# Recommended next development increments

1. Complete the distribution decisions in DISTRIBUTION.md: publisher identity,
   signing credential, application license and runtime redistribution review.
2. Add a manual-review queue. Let investigators confirm or correct parsed sender
   and date assertions while retaining the original values, the correction
   rationale, the actor and an append-only correction history. Keep quoted
   assertions visibly separate from original metadata. Do not silently fill
   missing information. This is the most valuable next product improvement.
3. Add portable investigation backup/restore and batch integrity verification.
   Replace absolute managed-copy paths with relative workspace paths. Test
   restore on a different machine and recovery from interrupted imports.
4. Add background import progress and cancellation for larger evidence batches.
   Native Excel export is available; continue improving large-report handling.
5. Extend MSG coverage to RTF-only bodies and additional Outlook variants.
   EML and MSG plain-text/HTML import are implemented in 0.1.7.
   Add safe ZIP ingestion with traversal, file-count and expansion limits.
6. Add DOCX and PDF text extraction with page/paragraph provenance and explicit
   uncertainty; treat OCR as a later offline feature. Evaluate dependencies and
   their licenses before adding them.

Future audit tamper evidence and encryption should be separately specified and
validated. A file hash and an ordinary SQLite log do not make the app a certified
forensic product, and a signed installer does not validate the extracted facts.
