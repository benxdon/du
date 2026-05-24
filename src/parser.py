from dataclasses import dataclass
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import mailbox
from datetime import datetime
from bs4 import BeautifulSoup
from email import policy
import json


@dataclass
class Email:
    from_address: str=""
    to_address: str=""
    subject: str=""
    body: str=""
    reply_to: str=""
    date: datetime|None = None


def read_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n",strip=True)

    return text


def save_emails(emails,path="data/parsed.json"):
    data = []

    for email in emails:
        d = {
            "from"      : email.from_address or "",
            "to"        : email.to_address or "",
            "subject"   : email.subject or "",
            "body"      : email.body or "",
            "reply_to"  : email.reply_to or "",
            "date"      : email.date.isoformat() if email.date else None
        }

        for key in d.keys():
            if isinstance(d[key], bytes):
                d[key] = d[key].decode("utf-8",errors="replace")

        data.append(d)

    with open(path,"w") as f:
        json.dump(data,f)


def load_emails(path="data/parsed.json"):
    with open(path) as f:
        data = json.load(f)

    emails = []

    for d in data: 
        emails.append(
            Email(
                from_address = d["from"],
                to_address   = d["to"],
                subject      = d["subject"],
                body         = d["body"],
                reply_to     = d["reply_to"],
                date         = datetime.fromisoformat(d["date"]) if d["date"] else None
            )
        )

    return emails


def read_body(msg):
    if not msg.is_multipart():
        content = msg.get_content()
        if isinstance(content,bytes):
            return ""
        if msg.get_content_type() == "text/html":
            return read_html(content)
        return content

    plain = None
    html = None

    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type.startswith("multipart/"):
            continue
        content = part.get_content()
        if isinstance(content,bytes):
            continue
        if content_type == "text/plain" and plain is None:
            plain = part.get_content()
        if content_type == "text/html" and html is None: 
            html = read_html(part.get_content())

    if plain is not None: 
        return plain
    if html is not None: 
        return html
    return ""


if __name__ == "__main__":
    import os

    if os.path.exists("data/parsed.json"):
        emails = load_emails()

    else:
        msgs = []
        with os.scandir("data/") as d: 
            for e in d:
                if e.name.endswith(".mbox"):
                    mbox = mailbox.mbox(path=e.path, factory=lambda f: BytesParser(policy=policy.default).parse(f))
                    msgs.extend(mbox)

        emails = []

        for msg in msgs:
            try:
                date = parsedate_to_datetime(msg["Date"])
            except ValueError: 
                date = None

            try:
                emails.append(
                    Email(
                        from_address = msg["From"],
                        to_address   = msg["To"],
                        subject      = msg["Subject"],
                        body         = read_body(msg),
                        reply_to     = msg["In-Reply-To"],
                        date         = date
                    )
                )
            except Exception as err: 
                print(f"skipping email: {err}")

        save_emails(emails)
        print(f"Parsed: {len(emails)}")


