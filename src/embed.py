import chromadb
import uuid
from parser import load_emails
from datetime import datetime
import os

chroma_client = chromadb.PersistentClient(path="data/chroma")

collection = chroma_client.get_or_create_collection(name="emails")

if collection.count() > 0:
    print(f"collection already has {collection.count()} emails")
elif not os.path.exists("data/parsed.json"):
    print("the file 'data/parsed.json' hasn't been created, please run the file 'src/parser.py' first")
else:
    emails = load_emails()
    batch_size = 500

    for i in range(0, len(emails), batch_size):
        batch = emails[i:i+batch_size]

        collection.add(
            ids = [str(uuid.uuid4()) for _ in batch],
            documents = [f"Subject: {e.subject}\n\n {e.body}" for e in batch],
            metadatas = [{
                "from"      : e.from_address,
                "to"        : e.to_address,
                "subject"   : e.subject,
                "reply_to"  : e.reply_to,
                "date"      : datetime.isoformat(e.date) if e.date else ""
            }
            for e in batch
            ])

        print(f"Added batch {i//batch_size + 1}")


    print(f"Added {collection.count()} emails into Chroma")
