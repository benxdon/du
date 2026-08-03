import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import chromadb

from gmail_poll import polls

DEFAULT_OUTPUT = os.path.expanduser("~/cloud/Documents/Obsidian Vault/50 - Daily")


def parse_date(date_str):
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        pass
    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        return None


def fetch_recent_emails(days):
    chroma_client = chromadb.PersistentClient(path="data/chroma")
    collection = chroma_client.get_collection(name="emails")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    total = collection.count()

    emails = []
    batch_size = 5000
    for offset in range(0, total, batch_size):
        results = collection.get(
            include=["documents", "metadatas"],
            limit=batch_size,
            offset=offset,
        )
        if not results["documents"]:
            break
        for i, doc in enumerate(results["documents"]):
            meta = results["metadatas"][i]
            dt = parse_date(meta.get("date", ""))
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt < cutoff:
                continue
            emails.append({
                "from": meta["from"],
                "to": meta["to"],
                "subject": meta["subject"],
                "date": meta.get("date", ""),
                "body": doc,
            })

    return emails


def write_brief(emails, output_dir):
    today = datetime.now()
    month_dir = Path(output_dir) / today.strftime("%Y-%m")
    month_dir.mkdir(parents=True, exist_ok=True)

    file_path = month_dir / f"{today.strftime('%d')}.md"

    frontmatter = (
        f"---\n"
        f"date: {today.strftime('%Y-%m-%d')}\n"
        f"tags: [daily-brief, email]\n"
        f"emails: {len(emails)}\n"
        f"unread: true\n"
        f"---\n\n"
    )

    lines = []
    for e in emails:
        lines.append(f"### {e['subject']}")
        lines.append(f"- **From:** {e['from']}")
        lines.append(f"- **To:** {e['to']}")
        lines.append(f"- **Date:** {e['date']}")
        lines.append(f"\n{e['body']}\n")

    file_path.write_text(frontmatter + "\n".join(lines))
    return file_path


def main():
    parser = argparse.ArgumentParser(description="Generate daily email brief for Obsidian")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Output directory")
    parser.add_argument("--dump", action="store_true", help="Print emails as JSON to stdout for piping")
    args = parser.parse_args()

    print("Syncing emails...", flush=True)
    polls(token_path="creds/token_pickle", last_poll_file="data/last_poll.txt")
    polls(token_path="creds/token_pickle_2", last_poll_file="data/last_poll_2.txt")

    print(f"Fetching emails from last {args.days} day(s)...", flush=True)
    emails = fetch_recent_emails(args.days)

    if not emails:
        print("No emails found, skipping brief.")
        return

    print(f"Found {len(emails)} emails.", flush=True)

    if args.dump:
        print(json.dumps(emails, indent=2))
        return

    path = write_brief(emails, args.output)
    print(f"Done: {path}")


if __name__ == "__main__":
    main()
