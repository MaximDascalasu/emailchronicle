"""Build-time license collection. No network code is included in the app."""
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import shutil
import ssl
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ("QtBase", "https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz",
     "a951bd163c7b80fc6b8c88d7668fb56abf91c152373e13c10666763238131307"),
    ("PySide-Shiboken", "https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz",
     "099c1a597cf33c1b000e11cf68a0b82d216fb802bf81726efc720394f10c7751"),
)
QT_DLLS = {"qt6core.dll", "qt6gui.dll", "qt6widgets.dll"}
QT_PLUGINS = {"platforms/qwindows.dll", "platforms/qoffscreen.dll", "platforms/qminimal.dll",
              "styles/qmodernwindowsstyle.dll"}
NOTICE_DIRECTORY = "third-party-notices-v2"


def permitted_binary(name):
    """Explicit Qt allowlist prevents accidental GPL-only plugin distribution."""
    normalized = name.replace("\\", "/").lower()
    basename = normalized.rsplit("/", 1)[-1]
    if basename == "opengl32sw.dll" or (basename.startswith("icu") and basename.endswith(".dll")):
        return False  # Windows system ICU, never an unrelated DLL from PATH.
    if normalized.startswith("pyside6/plugins/"):
        return normalized.removeprefix("pyside6/plugins/") in QT_PLUGINS
    if basename.startswith("qt6") and basename.endswith(".dll"):
        return basename in QT_DLLS
    if normalized.startswith("pyside6/qt") and basename.endswith(".pyd"):
        return basename in {"qtcore.pyd", "qtgui.pyd", "qtwidgets.pyd"}
    return True


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(url, destination, expected=None):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or (expected and digest(destination) != expected):
        request = urllib.request.Request(url, headers={"User-Agent": "EmailChronicle-build/0.1"})
        with urllib.request.urlopen(request, timeout=90) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
    if expected and digest(destination) != expected:
        raise ValueError(f"Source archive checksum mismatch: {destination.name}")
    return destination


def notice_member(name):
    path = PurePosixPath(name)
    base = path.name.lower()
    return (any(part.lower() == "licenses" for part in path.parts)
            or base.startswith(("license", "licence", "copying", "notice", "copyright"))
            or base == "qt_attribution.json")


def extract_notices(archive, destination):
    destination = Path(destination).resolve()
    count = 0
    with tarfile.open(archive, "r:xz") as source:
        for member in source:
            if not member.isfile() or not notice_member(member.name):
                continue
            parts = PurePosixPath(member.name).parts
            if any(p in ("..", "") for p in parts) or PurePosixPath(member.name).is_absolute():
                raise ValueError("Unsafe source archive member")
            target = destination.joinpath(*parts).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Source notice escapes destination")
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.extractfile(member) as input_stream, target.open("wb") as output:
                shutil.copyfileobj(input_stream, output)
            count += 1
    if not count:
        raise ValueError("Source archive contains no license notices")
    return count


def prepare():
    for name in ("PySide6", "PySide6_Essentials", "shiboken6"):
        if importlib.metadata.version(name) != "6.12.0":
            raise ValueError("Review source archives and licenses before changing the Qt version")
    folder = ROOT / "build" / "compliance"
    notices = folder / "third-party-notices"
    notices.mkdir(parents=True, exist_ok=True)
    index = []
    for name, url, expected in SOURCES:
        archive = fetch(url, folder / "sources" / url.rsplit("/", 1)[-1], expected)
        count = extract_notices(archive, notices / name)
        index.append({"component": name, "version": "6.12.0", "url": url,
                      "sha256": expected, "notice_files": count, "modified": False})
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise ValueError("Python runtime license missing")
    (notices / "Python").mkdir(exist_ok=True)
    shutil.copy2(python_license, notices / "Python" / "LICENSE.txt")
    distribution = importlib.metadata.distribution("pyinstaller")
    license_path = next((distribution.locate_file(f) for f in distribution.files or []
                         if str(f).endswith("licenses/COPYING.txt")), None)
    if license_path is None:
        raise ValueError("PyInstaller license and bootloader exception missing")
    (notices / "PyInstaller").mkdir(exist_ok=True)
    shutil.copy2(license_path, notices / "PyInstaller" / "COPYING.txt")
    openssl_version = ssl.OPENSSL_VERSION.split()[1]
    fetch(f"https://raw.githubusercontent.com/openssl/openssl/openssl-{openssl_version}/LICENSE.txt",
          notices / "OpenSSL" / "LICENSE.txt")
    fetch("https://raw.githubusercontent.com/jrsoftware/issrc/is-6_7_3/license.txt",
          notices / "InnoSetup" / "LICENSE.txt")
    fetch("https://www.sqlite.org/copyright.html", notices / "SQLite" / "copyright.html")
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", notices / "README.md")
    (notices / "source-index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    required = [p.name.lower() for p in notices.rglob("*") if p.is_file()]
    if not any("lgpl" in name for name in required) or not any("gpl-3" in name or "gpl3" in name for name in required):
        raise ValueError("Full LGPLv3 and GPLv3 license texts missing")
    # Inno Setup 6 cannot install arbitrarily long upstream source-tree paths.
    # Preserve all bytes but use short, collision-resistant installed names.
    compact = folder / NOTICE_DIRECTORY
    compact.mkdir(exist_ok=True)
    origins = []
    for original in sorted(notices.rglob('*')):
        if not original.is_file():
            continue
        relative = original.relative_to(notices)
        if len(relative.parts) == 1:
            target = compact / original.name
        else:
            target = compact / relative.parts[0] / (hashlib.sha256(relative.as_posix().encode()).hexdigest()[:12] + '-' + original.name[:40])
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(original, target)
        origins.append({'installed_path': target.relative_to(compact).as_posix(), 'upstream_notice_path': relative.as_posix(), 'sha256': digest(original)})
    (compact / 'notice-origins.json').write_text(json.dumps(origins, indent=2), encoding='utf-8')
    return folder


def inventory(bundle):
    bundle = Path(bundle).resolve()
    forbidden = [str(p.relative_to(bundle)) for p in bundle.rglob("*")
                 if p.is_file() and not permitted_binary(p.relative_to(bundle).as_posix().removeprefix("_internal/"))]
    if forbidden:
        raise ValueError("Unreviewed Qt components in bundle: " + ", ".join(forbidden))
    files = [{"path": p.relative_to(bundle).as_posix(), "sha256": digest(p), "size": p.stat().st_size}
             for p in sorted(bundle.rglob("*")) if p.is_file() and p.name != "bundle-inventory.json"]
    result = {"application": "EmailChronicle", "version": importlib.metadata.version("emailchronicle"),
              "python": sys.version.split()[0], "openssl": ssl.OPENSSL_VERSION,
              "qt": "6.12.0", "files": files,
              "note": "File inventory, not a legal certification or SPDX SBOM. See THIRD_PARTY_NOTICES.md."}
    (bundle / "bundle-inventory.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def source_companion(output=None):
    import sqlite3
    folder = ROOT / "build" / "compliance"
    output = Path(output) if output else ROOT / "installer-output"
    output.mkdir(parents=True, exist_ok=True)
    version = importlib.metadata.version("emailchronicle")
    with zipfile.ZipFile(output / f"EmailChronicle-ThirdPartySources-{version}.zip", "w", zipfile.ZIP_STORED) as archive:
        for source in sorted((folder / "sources").glob("*.tar.xz")):
            archive.write(source, "sources/" + source.name)
        for notice in sorted((folder / NOTICE_DIRECTORY).rglob("*")):
            if notice.is_file():
                archive.write(notice, "notices/" + notice.relative_to(folder / NOTICE_DIRECTORY).as_posix())
        archive.write(ROOT / "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md")
        archive.writestr("runtime-versions.json", json.dumps({"python": sys.version.split()[0],
                         "openssl": ssl.OPENSSL_VERSION, "sqlite": sqlite3.sqlite_version}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--inventory":
        inventory(sys.argv[2])
    elif len(sys.argv) in (2, 3) and sys.argv[1] == "--source-companion":
        source_companion(sys.argv[2] if len(sys.argv) == 3 else None)
    else:
        print(prepare())
