"""Conservative EML parser. Quoted headers are assertions, never original metadata."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


def recorded_datetime(raw):
    """Read a recorded wall-clock time without assigning an absent timezone."""
    if not raw:
        return None
    value = re.sub(r"\s+", " ", raw).strip()
    try:
        return parsedate_to_datetime(value)
    except (ValueError, TypeError, OverflowError):
        pass
    value = re.sub(r"\bat\b", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip()
    for fmt in ("%A, %B %d, %Y %I:%M %p", "%a, %b %d, %Y %I:%M %p",
                "%A, %B %d, %Y %H:%M", "%a, %b %d, %Y %H:%M",
                "%B %d, %Y %I:%M %p", "%b %d, %Y %I:%M %p"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def clean_address(value):
    return re.sub(r"<mailto:[^>]+>", "", value or "", flags=re.I).strip()


def parse_date(raw):
    if not raw:
        return None, ["missing_date"]
    # RFC -0000 explicitly means the originating timezone is unknown.
    if re.search(r"-0000\b", raw):
        return None, ["ambiguous_timezone"]
    dt = recorded_datetime(raw)
    if dt is None:
        return None, ["unparsed_date"]
    if dt.tzinfo is None:
        return None, ["ambiguous_timezone"]
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds"), []



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
        reply = re.match(r"^On\s+(.+?\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?(?:\s+[+-]\d{4})?)\s+(.+?)\s+wrote:\s*$", line, re.I)
        if reply and recorded_datetime(reply[1]):
            candidates.append((i, i + 1, {"from": clean_address(reply[2]), "date": reply[1],
                "subject": str(mail['Subject'] or ''), "to": ""}))
            i += 1
            continue
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
        result.append(Message(clean_address(headers["from"]) or None, clean_address(headers.get("to")), headers.get("subject"),
                              raw, utc, "\n".join(lines[end:stop]).strip(), "quoted",
                              f"Decoded body lines {start + 1}-{stop}",
                              flags=["quoted_headers_unverified"] + flags))
    return result


def parse_msg(data: bytes) -> list[Message]:
    """Read Outlook mail without extracting attachments or changing original bytes."""
    from email.message import EmailMessage
    from email.parser import HeaderParser
    from email.utils import format_datetime, formataddr
    from aspose.email_foss.cfb import CFBReader
    from aspose.email_foss.msg import MsgReader, MsgDocument, MapiMessage

    try:
        with CFBReader(data) as compound, MsgReader(compound) as reader:
            with MapiMessage.from_msg_document(MsgDocument.from_reader(reader)) as outlook:
                if not (outlook.message_class or "").startswith("IPM.Note"):
                    raise ValueError("Only Outlook email messages are supported")
                def value(prop):
                    return outlook.get_property_value(prop)
                header = HeaderParser(policy=policy.default).parsestr(value(0x007D) or "")
                mail = EmailMessage(policy=policy.default)
                sender = value(0x5D01) or value(0x0C1F)
                sender = formataddr((value(0x0C1A) or "", sender)) if sender else value(0x0C1A)
                def recipients(kind, fallback):
                    addresses = [formataddr((r.display_name or "", r.email_address))
                                 for r in outlook.recipients
                                 if r.recipient_type == kind and r.email_address]
                    return ", ".join(addresses) or fallback
                for key, fallback in (("From", sender), ("To", recipients(1, value(0x0E04))),
                                      ("Cc", recipients(2, value(0x0E03))), ("Subject", outlook.subject),
                                      ("Message-ID", value(0x1035))):
                    text = str(header[key]) if header[key] else fallback
                    if text:
                        mail[key] = re.sub(r"[\r\n]+", " ", text)
                raw_date = next((v for k, v in header.raw_items() if k.lower() == "date"), None)
                # Client submit time is the send time; delivery time must not stand in for it.
                sent = value(0x0039)
                if not raw_date and isinstance(sent, datetime):
                    raw_date = format_datetime(sent)
                if raw_date:
                    mail["Date"] = re.sub(r"[\r\n]+", " ", raw_date)
                if outlook.body:
                    mail.set_content(outlook.body)
                elif outlook.body_html:
                    mail.set_content(outlook.body_html, subtype="html")
                else:
                    mail.set_content("")
                messages = parse_eml(mail.as_bytes())
                if raw_date:
                    messages[0].raw_date = raw_date
                    messages[0].date_utc, date_flags = parse_date(raw_date)
                    messages[0].flags = [f for f in messages[0].flags if f not in
                        ("missing_date", "unparsed_date", "ambiguous_timezone")] + date_flags
                messages[0].locator = "MSG properties / decoded message body"
                if reader.validation_issues:
                    messages[0].flags.append("msg_structure_warning")
                if not outlook.body and not outlook.body_html:
                    messages[0].flags.append("missing_body")
                return messages

    except Exception as exc:
        raise ValueError(f"Cannot read Outlook MSG email: {exc}") from exc


def parse_email(data: bytes, suffix: str) -> list[Message]:
    if suffix.lower() == ".msg":
        return parse_msg(data)
    if suffix.lower() == ".eml":
        return parse_eml(data)
    raise ValueError("Supported email formats are EML and MSG")
