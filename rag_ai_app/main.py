import logging
import inngest
import inngest.fast_api
from inngest.experimental import ai

from fastapi import FastAPI
from dotenv import load_dotenv
import uuid
import os
import datetime

load_dotenv()  # Load environment variables from .env file
inngest_client = inngest.Inngest(
    app_id = "rag_app",
    logger = logging.getLogger("uvicorn"),
    is_production = False,
    serializer=inngest.PydanticSerializer()
)

@inngest_client.create_function(
    fn_id="RAG: Ingest PDF File",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
)
async def rag_ingest_pdf(ctx: inngest.Context):
    # hello world function
    return {"hello": "world from RAG Ingest PDF Function!"}


app = FastAPI()
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf])


def main():
    print("Hello from rag-ai-app!")

if __name__ == "__main__":
    main()
