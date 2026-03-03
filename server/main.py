import os
import shutil
import asyncio
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importações do RAG / Langchain
from core.llm_engine import aguardar_ollama
from core.rag_manager import RAGManager

app = FastAPI(title="Chat Corporativo AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_manager = RAGManager()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"

class ChatResponse(BaseModel):
    response: str

@app.on_event("startup")
async def startup_event():
    print("Inicializando Servidor de IA...")
    rag_manager.init_db()
    # Inicia a sincronização periódica em background (ex: a cada 1 hora)
    asyncio.create_task(periodic_sync())

async def periodic_sync():
    """Roda infinitamente enquanto o servidor estiver online, refazendo o download da planilha API Google periodicamente."""
    while True:
        try:
            print("[SYNC AUTO] Buscando novas atualizações da Planilha Master via Google API...")
            rag_manager.sync_google_sheet_api()
        except Exception as e:
            print(f"[SYNC AUTO] Erro na sincronização: {e}")
        
        # Espera 1 hora (3600 segundos) para buscar novamente. Ajuste conforme necessidade
        await asyncio.sleep(3600) 

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Mensagem vazia.")
            
        resposta = rag_manager.ask_question(req.message, req.session_id)
        return ChatResponse(response=resposta)
    except Exception as e:
        print(f"Erro no chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/indexar")
async def index_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")
        
    try:
        # Salva o temp file
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Processa e indexa no banco vetorial
        msg = rag_manager.index_document(file_path)
        
        # Limpa arquivo temporario
        os.remove(file_path)
        
        return {"status": "success", "message": msg}
        
    except Exception as e:
        print(f"Erro ao indexar arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class UrlRequest(BaseModel):
    url: str

@app.post("/index_url")
async def index_url_endpoint(req: UrlRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="Nenhuma URL informada.")
        
    try:
        msg = rag_manager.index_url(req.url)
        return {"status": "success", "message": msg}
    except Exception as e:
        print(f"Erro ao indexar URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
