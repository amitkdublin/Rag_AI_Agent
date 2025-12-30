# steps to setup project
uv init rag_ai_app
cd ./rag_ai_app
uv add fastapi inngest llama-index-core llama-index-readers-file openai python-dotenv qdrant-client streamlit uvicorn ollama

#Steps to Execute

# 1. Install docker desktop app and then run below from a new shell
# create a new sub directory under project named qdrant_storage
docker run -d --name qdrantRagDb -p 6333:6333 -v ./qdrant_storage:/qdrant/storage qdrant/qdrant

# 2. Install Ollama desktop app. Download two models (magistral, nomic-embed-text). The LLM runs local on your desktop or laptop
ollama pull magistral
ollama pull nomic-embed-text

# 3. To run FastAPI
uv run uvicorn main:app

# 4. Now lest start local Inngest dev server
# run development server, and connect to an application running on port 8000
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest --no-discovery