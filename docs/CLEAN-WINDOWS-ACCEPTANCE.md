# Clean Windows acceptance checklist — EmailChronicle 0.1.2

This gate is NOT completed on the development host. Use a fresh Windows 10/11
x64 VM or spare PC with no Python/Qt installation required by the application.
Do not change Windows security controls to make the preview run. If blocked,
record the exact message and stop that step.

1. Copy the complete private-preview folder to local storage outside a web root.
   Compare the installer SHA-256 with SHA256SUMS.txt. Confirm Windows reports the
   setup as unsigned; do not claim the local test certificate provides trust.
2. In an approved PowerShell session (without changing execution policy), run:

   ```powershell
   ./test-installed-preview.ps1 -Installer ./EmailChronicle-Setup-0.1.2-x64.exe -EnvironmentLabel clean-windows-vm -Launches 10 -OutputDirectory ./verification
   ```

   If the script is blocked, have the system administrator assess it or perform
   the manual steps. No policy bypass is required or supplied.
3. Independently record Windows edition/build/architecture, VM freshness, whether
   Python/Qt are installed, security policy and the tester/date. The script's
   environment label is NOT independent proof of a clean machine.
4. Separately install normally and launch from Start. Create a case; import the
   bundled `samples/*.eml` in reverse order. Confirm six message occurrences,
   oldest-to-newest UTC ordering, duplicate hints and two undated review rows.
   Import an identical file again; confirm no additional occurrence.
5. Configure the following synthetic synonyms:

   ```text
   + Handover | handover | transfer
   ```

   In Expanded mode search `transfer`; confirm `handover` matches with a synonym
   explanation. Exact `transfer` should not match those sample subjects. Check
   an exact quoted phrase and the approximate spelling mode. Never use real data.
6. Export CSV and the PDF/Excel/graph bundle to another local folder. Open the
   files; inspect UTF-8 names, full content, provenance, search scope, undated
   warnings and original/quoted distinctions. View PNG/SVG/PDF chart pages.
   Gantt-style lanes show point events and do not infer durations.
7. Close normally, reopen, confirm the synthetic case persists, then close again.
   Repeat shutdown. Record any Windows crash event or nonzero process exit.
8. Uninstall via Windows Settings. Verify program/shortcuts were removed and the
   synthetic case under `%LOCALAPPDATA%\EmailChronicle` remains. Reinstall to
   confirm retained-case access. Remove only your synthetic test data when done.
9. Return the JSON acceptance report and manual observations to the project.
   Clean-machine approval remains pending until these results are reviewed.

Store installers and source companions in private server storage outside public
web access if access distribution is later approved. Never upload the installer
into a theme directory or the WordPress Media Library.
