# EmailChronicle 0.1.7 — Outlook MSG import preview

- Import EML and MSG email together, without Outlook installed.
- Preserve original evidence bytes, file extensions, SHA-256 hashes and audit entries.
- Extract MSG sender, recipients, subject, recorded send time, plain text and HTML.
- Reuse quoted-reply extraction, date uncertainty flags, duplicate checks and chronology.
- Show decoded MSG text and exact original bytes in the read-only source viewer.
- Bundle the MIT-licensed Aspose.Email FOSS parser and its license notice.
- Update quick start, website copy and access plugin 0.2.5 for the new installer.

RTF-only MSG bodies are flagged as missing body for review. Attachments remain in
the preserved source and are not imported separately. Contacts and appointments
are rejected. Large imports still run on the UI thread.

This is a local unsigned evaluation preview. No release publication or hosting
deployment is implied. Trusted signing and independent clean-machine acceptance
remain pending. Validation results are recorded in RELEASE-VALIDATION-0.1.7.md.
