from fastapi import FastAPI, Request
import chromadb
from bs4 import BeautifulSoup
import uuid


chroma_client = chromadb.PersistentClient(path="data/chroma")
collection = chroma_client.get_or_create_collection(name="emails")

app = FastAPI()

def read_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n",strip=True)

    return text

@app.post("/ingest")
async def get_data(request: Request):
    data = await request.json()
    if data:
        from_address = data["from"]
        to_address = data["to"]
        subject = data["subject"]
        body = read_html(data["body"])
        reply_to = data.get("reply_to","")
        date = data["date"]

        collection.add(
            ids = [str(uuid.uuid4())],
            documents = [f"Subject: {subject}\n\n{body}"],
            metadatas = [{
                "from"      : from_address,
                "to"        : to_address,
                "subject"   : subject,
                "reply_to"  : reply_to,
                "date"      : date 
                }]
        )
    return {"status":"ok"}


