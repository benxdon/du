import logging
from config import get_collection, ACCOUNTS
from datetime import datetime, timezone
from imap_tools import MailBox, AND
from tqdm import tqdm

IMAP_SERVER = "imap.gmail.com"
log = logging.getLogger(__name__)
BODY_CAP = 8000
BATCH_SIZE = 500


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

def poll(user, pw, last_poll_path):
    if not user or not pw:
        raise ValueError("missing IMAP credentials")

    collection = get_collection()
    run_start = int(datetime.now(timezone.utc).timestamp())

    since = get_last_poll(last_poll_path)
    # since = int(datetime.now().timestamp()) - 60 * 60 * 24
    since_date = datetime.fromtimestamp(since, timezone.utc).date() if since else None
    criteria = AND(date_gte=since_date) if since_date else AND(all=True)

    b_ids, b_docs, b_metas = [], [], []

    def flush():
        if b_ids:
            collection.upsert(ids=b_ids, documents=b_docs, metadatas=b_metas)
            b_ids.clear()
            b_docs.clear()
            b_metas.clear()

    with MailBox(IMAP_SERVER).login(user, pw, "INBOX") as mb:
        msgs = list(mb.fetch(criteria=criteria))
        log.info("%s: %d messages", user, len(msgs))

        for msg in tqdm(msgs, desc=user, unit="msg"):
            date_int = int(msg.date.timestamp()) if msg.date else 0
            body = (msg.text or msg.html or "")[:BODY_CAP]

            msg_id_header = msg.headers.get("message-id")
            if msg_id_header:
                msg_id = msg_id_header[0]
            else:
                msg_id = f"{user}:{msg.uid}"

            b_ids.append(msg_id)
            b_docs.append(body)
            b_metas.append({
                "from": msg.from_,
                "subject": msg.subject,
                "date": msg.date_str,
                "date_int": date_int
            })

            if len(b_ids) >= BATCH_SIZE:
                flush()

    save_last_poll(last_poll_path, run_start)
    return len(msgs)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for user, pw, last_poll_path in ACCOUNTS:
        n = poll(user, pw, last_poll_path)
        print(f"{user}: {n} messages")
