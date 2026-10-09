import importlib.util
from pathlib import Path
import io
import tarfile
import os
import subprocess

import pytest

spec = importlib.util.spec_from_file_location("chronicle_compliance", Path(__file__).resolve().parents[1] / "packaging" / "compliance.py")
compliance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compliance)


@pytest.mark.parametrize("name", ["PySide6/Qt6VirtualKeyboard.dll", "PySide6/Qt6Pdf.dll",
    "PySide6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll", "PySide6/plugins/imageformats/qpdf.dll",
    "PySide6\\plugins\\imageformats\\qjpeg.dll", "icuuc.dll", "icudt78.dll", "PySide6/opengl32sw.dll", "PySide6/QtNetwork.pyd"])
def test_unreviewed_plugins_excluded(name):
    assert not compliance.permitted_binary(name)


@pytest.mark.parametrize("name", ["PySide6/Qt6Core.dll", "PySide6/Qt6Widgets.dll", "PySide6/QtWidgets.pyd",
    "PySide6/plugins/platforms/qwindows.dll", "PySide6/plugins/platforms/qoffscreen.dll", "python312.dll"])
def test_required_runtime_allowed(name):
    assert compliance.permitted_binary(name)


def test_notices_extract_without_extracting_arbitrary_source(tmp_path):
    archive = tmp_path / "source.tar.xz"
    with tarfile.open(archive, "w:xz") as output:
        for name in ("upstream/LICENSES/LGPL-3.0-only.txt", "upstream/README.md", "upstream/src/main.cpp"):
            data = b"synthetic test data"
            member = tarfile.TarInfo(name)
            member.size = len(data)
            output.addfile(member, io.BytesIO(data))
    assert compliance.extract_notices(archive, tmp_path / "notices") == 1
    assert (tmp_path / "notices/upstream/LICENSES/LGPL-3.0-only.txt").exists()
    assert not (tmp_path / "notices/upstream/src/main.cpp").exists()


def test_notice_path_traversal_rejected(tmp_path):
    archive = tmp_path / "unsafe.tar.xz"
    with tarfile.open(archive, "w:xz") as output:
        member = tarfile.TarInfo("../LICENSE.txt")
        member.size = 1
        output.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Unsafe"):
        compliance.extract_notices(archive, tmp_path / "notices")


def test_inventory_rejects_gpl_plugin_on_disk(tmp_path):
    plugin = tmp_path / "_internal/PySide6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll"
    plugin.parent.mkdir(parents=True)
    plugin.write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="Unreviewed Qt"):
        compliance.inventory(tmp_path)


@pytest.mark.skipif(os.name != "nt", reason="Windows signing preflight")
def test_signed_release_without_identity_is_blocked():
    env = os.environ.copy()
    env.pop("EMAILCHRONICLE_SIGNING_THUMBPRINT", None)
    command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(compliance.ROOT / "scripts/build-windows.ps1"), "-RequireSigning"]
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert "Signed release blocked" in result.stderr
