from pathlib import Path
import importlib.metadata
import sys

root = Path(SPECPATH).parent
sys.path.insert(0, str(root / 'packaging'))
from compliance import permitted_binary, NOTICE_DIRECTORY
notices = root / 'build' / 'compliance' / NOTICE_DIRECTORY
if not (notices / 'source-index.json').exists():
    raise RuntimeError('Run packaging/compliance.py before bundling')
datas = [(str(root / 'README.md'), '.'), (str(root / 'LICENSE'), '.'), (str(root / 'samples'), 'samples'),
         (str(root / 'THIRD_PARTY_NOTICES.md'), '.'), (str(notices), 'third-party-notices')]

a = Analysis([str(root / 'packaging' / 'launcher.py')], pathex=[str(root / 'src')],
             binaries=[], datas=datas, hiddenimports=[], hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=['PySide6.QtNetwork', 'PySide6.QtPdf', 'PySide6.QtVirtualKeyboard',
                                         'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                                         'PySide6.QtWebEngineQuick'], noarchive=True)
# Qt 6.12 imports the Windows system ICU API (unsuffixed symbols). A developer
# PATH may contain an unrelated icuuc.dll with versioned ICU symbols. Never
# bundle that DLL: use the ICU implementation supplied by supported Windows.
a.binaries = [entry for entry in a.binaries if permitted_binary(entry[0])]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='EmailChronicle',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='EmailChronicle')
