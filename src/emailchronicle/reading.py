"""Readable derivatives; original evidence is never changed."""
import re
from email.utils import getaddresses
from datetime import datetime
from .parser import recorded_datetime, clean_address


def readable_date(value):
    if not value:
        return "Date unknown · review source"
    return datetime.fromisoformat(value).strftime("%d %b %Y · %H:%M:%S UTC")


def message_date(row):
    if row['date_utc']:
        return readable_date(row['date_utc'])
    dt = recorded_datetime(dict(row).get('raw_date'))
    if dt:
        return dt.strftime("%d %b %Y · %H:%M") + " · timezone not recorded"
    return "Date unknown · review source"


def date_key(row):
    dt = recorded_datetime(dict(row).get('raw_date')) if not row['date_utc'] else datetime.fromisoformat(row['date_utc'])
    return dt.replace(tzinfo=None).isoformat() if dt else ''


def chronological(rows):
    return sorted(rows, key=lambda r: (not bool(date_key(r)), date_key(r), r['id']))


def clean_message(body, sender=None):
    lines = body.replace('\r', '').splitlines()
    result = []
    name = clean_address(sender).split('<')[0].strip()
    name_words = re.findall(r"[A-Za-z]+", name)
    full_name = ' '.join(name_words).casefold()
    # A sender's full name followed by a role/contact block marks an unsigned footer.
    footer = len(lines)
    if len(name_words) >= 2:
        for index, line in enumerate(lines):
            normalized = re.sub(r"\s+", " ", line).strip().casefold()
            if normalized.startswith(full_name) and len(normalized) < len(full_name) + 30:
                tail = '\n'.join(lines[index+1:index+12])
                if re.search(r"(?:https?://|www\.|@|(?:\d[ .()-]*){7}|partner|director|manager|strategist|designer)", tail, re.I):
                    footer = index
                    break
    for index, line in enumerate(lines[:footer]):
        if re.fullmatch(r"(?:thanks|thank you)[,! ]*", line.strip(), re.I):
            tail = [part.strip() for part in lines[index+1:footer] if part.strip()]
            if len(tail) == 1 and (tail[0].casefold() in (full_name, name_words[0].casefold() if name_words else '') or re.fullmatch(r"[A-Za-z]{2,20}", tail[0])):
                footer = index
                break
    lines = lines[:footer]
    for line in lines:
        text = re.sub(r"^(?:\s*>\s*)+", "", line).strip()
        if re.match(r"^(?:On .+wrote:|[-_]{5,}|--\s*$|Sent from my (?:iPhone|iPad|Android)|Get Outlook for)", text, re.I):
            break
        if re.fullmatch(r"(?:kind regards|best regards|regards|best wishes|best|warm regards|sincerely|yours sincerely|many thanks)[,! ]*", text, re.I):
            break
        if re.match(r"^(?:This (?:e-?mail|message).*(?:confidential|intended)|Confidentiality notice|NOTICE & DISCLAIMER:|DISCLAIMER:)", text, re.I):
            break
        if re.fullmatch(r"\[?(?:cid:|image\d*\.|https?://[^ ]*(?:googleusercontent|mail-sig)[^ ]*).*\]?", text, re.I):
            continue
        if re.fullmatch(r"(?:CAUTION:.*|EXTERNAL SENDER|\[signature[^]]*\])", text, re.I):
            continue
        text = re.sub(r"<mailto:([^>]+)>", "", text, flags=re.I)
        if '<http' in text:
            text = re.sub(r"([^\s<>]+)<https?://[^>]+>", r"\1", text)
        result.append(re.sub(r"[ \t]+", " ", text))
    content = "\n".join(result)
    content = re.sub(r"(?m)^\s*[*•]\s*\n(?:[ \t]*\n)*([^\n]+)", r"• \1", content)
    return re.sub(r"\n{3,}", "\n\n", content).strip()


def people_summary(value):
    people = getaddresses([clean_address(value)])
    labels = list(dict.fromkeys(name.strip('" ') or address for name, address in people if name or address))
    return ', '.join(labels[:3]) + (f" +{len(labels)-3} more" if len(labels)>3 else '')
