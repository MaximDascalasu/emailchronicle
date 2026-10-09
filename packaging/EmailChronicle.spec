from pathlib import Path
import importlib.metadata
import sys

root = Path(SPECPATH).parent
datas = [(str(root / 'README.md'), '.'), (str(root / 'samples'), 'samples')]
for name in ('PySide6', 'PySide6_Essentials', 'shiboken6'):
    distribution = importlib.metadata.distribution(name)
    for entry in distribution.files or ():
        if any('license' in part.lower() or 'copying' in part.lower() for part in entry.parts):
            source = Path(distribution.locate_file(entry))
            if source.is_file():
                datas.append((str(source), 'third-party-notices/' + name + '/' + str(entry.parent)))
python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if python_license.exists():
    datas.append((str(python_license), 'third-party-notices/Python'))

a = Analysis([str(root / 'packaging' / 'launcher.py')], pathex=[str(root / 'src')],
             binaries=[], datas=datas, hiddenimports=[], hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                                         'PySide6.QtWebEngineQuick'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='EmailChronicle',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='EmailChronicle')
