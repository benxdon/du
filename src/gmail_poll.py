import imaplib
import email
import logging
import config
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from tqdm import tqdm
from email.header import decode_header, make_header


def _decode(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return str(value)


log = logging.getLogger(__name__)
IMAP_SERVER = "imap.gmail.com"
BODY_CAP = 8000

def get_last_poll(last_poll_path):
    if not last_poll_path.exists():
        return None
    raw = last_poll_path.read_text().strip()
    try:
        return int(raw)
    except ValueError:
        log.warning("last_poll %s is not a string (%r)", last_poll_path, raw)

def save_last_poll(last_poll_path, epoch_int):
    last_poll_path.parent.mkdir(parents=True, exist_ok=True)
    last_poll_path.write_text(str(int(epoch_int)))

def _extract_body(msg):
    plain, html = "", ""
    for part in msg.walk():
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if part.get_content_type() == "text/plain":
            plain += text
        elif part.get_content_type() == "text/html":
            html += text
    if plain.strip():
        return plain
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True) if html else ""

def poll(user, pw, last_poll_path):
    collection = config.get_collection()
    since = get_last_poll(last_poll_path)
    # since = int(datetime.now(timezone.utc).timestamp()) - 86400
    run_start = int(datetime.now(timezone.utc).timestamp())

    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(user, pw)
    imap.select("INBOX")
    if since:
        since_date = datetime.fromtimestamp(since, timezone.utc).strftime("%d-%b-%Y")
        _, msgnums = imap.search(None, f'(SINCE "{since_date}")')
    else:
        _, msgnums = imap.search(None, "ALL")
    ids = msgnums[0].split()
    log.info("%s: %d messages", user, len(ids))

    BATCH = 500
    b_ids, b_docs, b_metas = [], [], []

    def flush():
        if b_ids:
            collection.upsert(
                ids=b_ids,
                metadatas=b_metas,
                documents=b_docs
            )
            b_ids.clear()
            b_docs.clear()
            b_metas.clear()

    for num in tqdm(ids, desc=user, unit="msg"):
        _, data = imap.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])

        date_str = msg.get("Date", "")
        try:
            date_int = int(parsedate_to_datetime(date_str).timestamp()) if date_str else 0
        except Exception:
            date_int = 0

        msg_id = msg.get("Message-ID")
        body = _extract_body(msg)[:BODY_CAP]

        collection.upsert(
            ids = [msg_id],
            documents=[body],
            metadatas=[{
                "from": _decode(msg.get("From", "")),
                "subject": _decode(msg.get("Subject", "")),
                "date": date_str,
                "date_int": date_int
            }]
        )
        if len(b_ids) >= BATCH:
            flush()

    flush()
    imap.close()
    imap.logout()
    save_last_poll(last_poll_path, run_start)
    return len(ids)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for user, pw, last_poll_path in config.ACCOUNTS:
        n = poll(user, pw, last_poll_path)
        print(f"{user}: {n} messages")
