import logging
import inngest
import inngest.fast_api
from inngest.experimental import ai

from fastapi import FastAPI
from dotenv import load_dotenv
import uuid
import os
import datetime

import ollama

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGChunksAndSrc, RAGUpsertResult, RAGSearchResult, RAGQueryResult

logger = logging.getLogger(__name__)
load_dotenv()
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
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunksAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunksAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStorage().upsert(ids, vecs['embeddings'], payloads)
        return RAGUpsertResult(ingested=len(chunks))
    
    chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), output_type=RAGChunksAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)
    return ingested.model_dump()


@inngest_client.create_function(
    fn_id="RAG: Query PDF (AI Adapter)",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai"),
    throttle={
        "limit": 5,
        "period": datetime.timedelta(seconds=1),
        "burst": 5,
    },
    rate_limit={
        "limit": 120,
        "period": datetime.timedelta(seconds=60),
    },
)
async def rag_query_pdf_ai(ctx: inngest.Context) -> RAGQueryResult:
    def _search(question: str, top_k: int = 5):
        query_vec = embed_texts([question])['embeddings'][0]
        store = QdrantStorage()
        found = store.search(query_vec, top_k)
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))

    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k), output_type=RAGSearchResult)

    context_block = "\n\n".join(f"- {c}" for c in found.contexts)
    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above."
    )
    response = ollama.chat(
        model="magistral",
        messages=[
                {"role": "system", "content": "You answer questions using only the provided context."},
                {"role": "user", "content": user_content},
            ]
    )
    answer = response.message.content
    return {"answer": answer, "sources": found.sources[:top_k], "num_contexts": len(found.contexts)}


app = FastAPI()
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])

def main():
    print("Hello from rag-ai-app!")

if __name__ == "__main__":
    main()
