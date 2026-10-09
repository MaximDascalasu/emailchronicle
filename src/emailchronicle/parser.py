"""Conservative EML parser. Quoted headers are assertions, never original metadata."""
from dataclasses import dataclass, field
from datetime import timezone
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import hashlib
import json
import re


@dataclass
class Message:
    sender: str | None
    recipients: str | None
    subject: str | None
    raw_date: str | None
    date_utc: str | None
    body: str
    kind: str
    locator: str
    message_id: str | None = None
    flags: list[str] = field(default_factory=list)

    @property
    def fingerprint(self):
        # Conservative exact content match, even if Message-ID is reused.
        values = [self.sender, self.recipients, self.subject, self.date_utc,
                  self.raw_date if not self.date_utc else None,
                  re.sub(r"\s+", " ", self.body).strip()]
        return hashlib.sha256(json.dumps(values, ensure_ascii=False).encode()).hexdigest()


def parse_date(raw):
    if not raw:
        return None, ["missing_date"]
    # RFC -0000 explicitly means the originating timezone is unknown.
    if re.search(r"-0000\b", raw):
        return None, ["ambiguous_timezone"]
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            return None, ["ambiguous_timezone"]
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds"), []
    except (ValueError, TypeError, OverflowError):
        return None, ["unparsed_date"]


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("br", "p", "div", "li", "tr") and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean_body(mail):
    part = mail.get_body(preferencelist=("plain", "html"))
    if part is None:
        return "", ["missing_body"]
    flags = []
    try:
        content = part.get_content()
    except (LookupError, UnicodeError):
        content = (part.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        flags.append("body_decode_fallback")
    if part.get_content_type() == "text/html":
        parser = TextHTML()
        parser.feed(content)
        content = unescape("".join(parser.parts))
        flags.append("html_converted_to_text")
    return content.replace("\r\n", "\n").replace("\r", "\n").strip(), flags


HEADER = re.compile(r"^(From|Sent|Date|To|Cc|Subject):\s*(.*)$", re.I)


def parse_eml(data: bytes) -> list[Message]:
    mail = BytesParser(policy=policy.default).parsebytes(data)
    body, body_flags = clean_body(mail)
    # Strip quote prefixes only for recognition; stored body remains unchanged.
    lines = body.splitlines()
    candidates = []
    i = 0
    while i < len(lines):
        line = re.sub(r"^(?:\s*>\s*)+", "", lines[i])
        if not re.match(r"^From:", line, re.I):
            i += 1
            continue
        start = i
        headers = {}
        while i < len(lines):
            match = HEADER.match(re.sub(r"^(?:\s*>\s*)+", "", lines[i]))
            if not match:
                break
            headers[match[1].lower()] = match[2].strip()
            i += 1
        if "from" in headers and ("date" in headers or "sent" in headers) and "subject" in headers:
            candidates.append((start, i, headers))
        i = max(i, start + 1)
    raw = str(mail["Date"]) if mail["Date"] else None
    # Preserve the literal date header rather than email.policy's normalized date.
    raw = next((v for k, v in mail.raw_items() if k.lower() == "date"), raw)
    utc, flags = parse_date(raw)
    if not mail["From"]:
        flags.append("missing_sender")
    if mail.defects:
        flags.append("email_structure_defect")
    for key in ("From", "To", "Date", "Subject", "Message-ID"):
        if len(mail.get_all(key, [])) > 1:
            flags.append("multiple_" + key.lower() + "_headers")
        if any(getattr(value, "defects", ()) for value in mail.get_all(key, [])):
            flags.append("malformed_" + key.lower() + "_header")
    first = candidates[0][0] if candidates else len(lines)
    result = [Message(str(mail["From"]) if mail["From"] else None,
                      str(mail["To"]) if mail["To"] else None,
                      str(mail["Subject"]) if mail["Subject"] else None,
                      raw, utc, "\n".join(lines[:first]).strip(), "original", "EML headers / MIME body",
                      str(mail["Message-ID"]) if mail["Message-ID"] else None,
                      flags + body_flags)]
    for index, (start, end, headers) in enumerate(candidates):
        stop = candidates[index + 1][0] if index + 1 < len(candidates) else len(lines)
        raw = headers.get("date") or headers.get("sent")
        utc, flags = parse_date(raw)
        if not headers["from"]:
            flags.append("missing_sender")
        result.append(Message(headers["from"] or None, headers.get("to"), headers.get("subject"),
                              raw, utc, "\n".join(lines[end:stop]).strip(), "quoted",
                              f"Decoded body lines {start + 1}-{stop}",
                              flags=["quoted_headers_unverified"] + flags))
    return result
