import logging
import inngest
import inngest.fast_api
from inngest.experimental import ai

from fastapi import FastAPI
from dotenv import load_dotenv
import uuid
import os
import datetime

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGChunksAndSrc, RAGUpsertResult, RAGSearchResult, RAGQueryResult

logger = logging.getLogger(__name__)

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
async def rag_ingest_pdf(ctx: inngest.Context) -> RAGUpsertResult:
    def _load(ctx: inngest.Context) -> RAGChunksAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        logger.info("***** pdf_path=%s", pdf_path)
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        logger.info("***** chunks=%s", str(chunks))
        return RAGChunksAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunksAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
        logger.info("****** ids=%s || vecs=%s || payloads=%s", str(ids), str(vecs), str(payloads))
        QdrantStorage().upsert(ids, vecs['embeddings'], payloads)
        return RAGUpsertResult(ingested=len(chunks))
    
    chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), output_type=RAGChunksAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)
    return ingested.model_dump()


app = FastAPI()
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf])


def main():
    print("Hello from rag-ai-app!")

if __name__ == "__main__":
    main()
