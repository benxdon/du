import os
from datetime import datetime
from gmail_auth import get_creds
from googleapiclient.discovery import build
import base64
from parser import read_html
import chromadb
import uuid

chroma_client = chromadb.PersistentClient(path='data/chroma')
collection = chroma_client.get_or_create_collection(name='emails')

last_poll_file = "data/last_poll.txt"

def get_last_poll(path=last_poll_file):
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return None

def save_last_poll(path=last_poll_file):
    with open(path, 'w') as f:
        f.write(datetime.now().isoformat())


def get_body(payload):
    if 'parts' in payload: 
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data','')
                plain = base64.urlsafe_b64decode(data).decode('utf-8')
                return plain
            if part['mimeType'] == 'text/html':
                data = part['body'].get('data','')
                html = base64.urlsafe_b64decode(data).decode('utf-8')
                return read_html(html)
    else:
        data = payload['body'].get('data','')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8')

    return ''

def polls():
    creds = get_creds()
    service = build('gmail', 'v1', credentials=creds)

    last = get_last_poll()
    query = f"after:{last}" if last else ""

    results = service.users().messages().list(userId='me',q=query).execute()

    msgs = results.get('messages',[])
    print(f"Found {len(msgs)} new emails")
    for  msg in msgs:
        full_msg = service.users().messages().get(userId='me',id=msg['id'],format='full').execute()
        headers = full_msg['payload']['headers']
        from_address = next((h['value'] for h in headers if h['name'] == 'From'), '')
        to_address = next((h['value'] for h in headers if h['name'] == 'To'), '')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        reply_to = next((h['value'] for h in headers if h['name'] == 'Reply-To'), '')
        body = get_body(full_msg['payload'])

        collection.add(
            ids = [str(uuid.uuid4())],
            documents = [f"Subject: {subject}\n\n {body}"],
            metadatas = [{
                "from"      : from_address,
                "to"        : to_address,
                "subject"   : subject,
                "reply_to"  : reply_to,
                "date"      : date 
                }]
        )

"""
headers for each email to extract information

Delivered-To
Received
X-Received
ARC-Seal
ARC-Message-Signature
ARC-Authentication-Results
Return-Path
Received
Received-SPF
Authentication-Results
DKIM-Signature
DKIM-Signature
Received
Received
Content-Type
Date
From
Mime-Version
Message-ID
Subject
Reply-To
List-Unsubscribe
List-Unsubscribe-Post
X-SG-EID
X-SG-ID
To
X-Entity-ID
"""

if __name__ == "__main__":
    polls()
