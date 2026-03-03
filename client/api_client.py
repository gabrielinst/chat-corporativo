import requests
import os

SERVER_URL = "http://127.0.0.1:8000"

def send_message(message: str, session_id: str = "user_desktop"):
    """Envia mensagem ao servidor e retorna a resposta."""
    try:
        response = requests.post(
            f"{SERVER_URL}/chat", 
            json={"message": message, "session_id": session_id},
            timeout=300 # O modelo 20b é pesado, pode demorar até 5 minutos dependendo da máquina/contexto
        )
        if response.status_code == 200:
            return response.json().get("response")
        else:
            return f"Erro no servidor: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Falha de conexão com o servidor. O backend está rodando? Detalhes: {e}"

def upload_document(file_path: str):
    """Envia o arquivo para o servidor indexar no VectorStore."""
    if not os.path.exists(file_path):
        return "Erro: Arquivo não encontrado localmente."
        
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            response = requests.post(f"{SERVER_URL}/indexar", files=files, timeout=300)
            
        if response.status_code == 200:
            return response.json().get("message", "Arquivo indexado com sucesso.")
        else:
            return f"Erro na indexação: {response.text}"
    except Exception as e:
        return f"Erro de conexão durante upload: {e}"

def index_url(url: str):
    """Envia uma URL do Google Sheets para o servidor indexar."""
    try:
        response = requests.post(f"{SERVER_URL}/index_url", json={"url": url}, timeout=300)
            
        if response.status_code == 200:
            return response.json().get("message", "URL indexada com sucesso.")
        else:
            return f"Erro na indexação: {response.text}"
    except Exception as e:
        return f"Erro de conexão durante indexação da URL: {e}"
