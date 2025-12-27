# steps to setup project
uv init rag_ai_app
cd ./rag_ai_app
uv add fastapi inngest llama-index-core llama-index-readers-file openai python-dotenv qdrant-client streamlit uvicorn

# To run FastAPI
uv run uvicorn main:app

# Now lest start local Inngest dev server
# run development server, and connect to an application running on port 8000
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest --no-discovery
