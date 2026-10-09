# EmailChronicle third-party software

EmailChronicle uses the open-source distributions of Python, PySide6, Shiboken
and Qt. No purchased Qt commercial license is claimed. Third-party copyrights
and license terms remain with their respective owners; this document does not
grant rights in EmailChronicle's own code. Its licensing decision is pending
the project owner's instruction.

The installer places complete collected notices in
`_internal/third-party-notices`. The **Third-party licenses** menu item opens
this directory. The matching `EmailChronicle-ThirdPartySources-VERSION.zip`
companion must accompany every binary distribution, with the same recipient
access as the installer. It contains the exact upstream QtBase and
PySide/Shiboken 6.12.0 source archives, checksums, licenses and attribution files.
Do not distribute a binary alone. Source downloads happen during development
and builds; the installed app does not download sources or contact a service.

| Component | Applicable route / purpose | Upstream |
| --- | --- | --- |
| Python | PSF and included historical/third-party license terms; embedded interpreter and standard library | https://docs.python.org/3/license.html |
| PySide6 / Shiboken 6.12.0 | LGPLv3 route; bindings and support libraries | https://doc.qt.io/qtforpython-6/licenses.html |
| QtBase 6.12.0 | LGPLv3 route for Core, Gui, Widgets and the allowlisted Windows platform/style plugins; additional bundled third-party notices also apply | https://doc.qt.io/qt-6/licensing.html |
| SQLite | Public domain; local database runtime | https://www.sqlite.org/copyright.html |
| OpenSSL | Apache-2.0 for the Python runtime's 3.x OpenSSL dependency; actual build version recorded in inventory | https://openssl-library.org/source/ |
| PyInstaller | GPL with the bootloader distribution exception; full COPYING text included | https://pyinstaller.org/en/stable/license.html |
| Inno Setup | Inno Setup license for setup/uninstall runtime; author requests commercial users purchase a license, but states it is not strictly required | https://jrsoftware.org/isorder.php |
| Microsoft runtime libraries | Redistributable terms from the supplying Python/Qt toolchain; vendor notices/signatures are retained | https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution |

Qt/PySide/Shiboken are unmodified shared libraries, stored separately from the
application executable. Recipients may replace them with ABI-compatible
modified builds. Python support modules are deployed as separate bytecode files
instead of being sealed into the executable's Python archive. No application rule enforces their signatures or inventory
hashes at runtime. Debugging or reverse engineering needed to exercise rights
under their LGPL terms is not restricted by this project. The LGPLv3 and GPLv3
texts, upstream copyright notices and third-party attributions are included.
Some upstream notice folders describe more code than this app uses; this is
intentional and does not mean every optional component is installed.

The packaging allowlist excludes Virtual Keyboard, WebEngine, PDF, QML/Quick,
SVG, software OpenGL, network plugins and optional image codecs, which this EML-only application
does not use. Builds fail if unreviewed Qt DLLs or plugins reach the final bundle.

`bundle-inventory.json` identifies shipped files and hashes. It is a build
inventory, not proof of legal compliance. Commercial release still requires
confirmation of the copyright owner's chosen application license, publisher
identity, Microsoft runtime redistribution entitlement and any desired Inno
Setup commercial license purchase. No purchased license or certificate exists
merely because a build completed. Obtain legal review before relying on a claim
that a commercial distribution meets every applicable legal requirement.
