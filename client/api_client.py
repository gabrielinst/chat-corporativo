import requests
import os
import json

# ---- Configuração do IP do Servidor ----
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_SERVER = "http://192.168.1.140:8000"

def load_server_url():
    """Carrega a URL do servidor salva no config.json."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("server_url", DEFAULT_SERVER)
        except:
            pass
    return DEFAULT_SERVER

def save_server_url(url):
    """Salva a URL do servidor no config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"server_url": url.rstrip("/")}, f)

def get_server_url():
    return load_server_url()

# ---- Funções de API ----

def send_message(message: str, session_id: str = "user_desktop"):
    """Envia mensagem ao servidor e retorna a resposta."""
    server = get_server_url()
    try:
        response = requests.post(
            f"{server}/chat",
            json={"message": message, "session_id": session_id},
            timeout=300
        )
        if response.status_code == 200:
            return response.json().get("response")
        else:
            return f"Erro no servidor: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Falha de conexão com o servidor ({server}). O backend está rodando? Detalhes: {e}"

def upload_document(file_path: str):
    """Envia o arquivo para o servidor indexar no VectorStore."""
    server = get_server_url()
    if not os.path.exists(file_path):
        return "Erro: Arquivo não encontrado localmente."

    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            response = requests.post(f"{server}/indexar", files=files, timeout=300)

        if response.status_code == 200:
            return response.json().get("message", "Arquivo indexado com sucesso.")
        else:
            return f"Erro na indexação: {response.text}"
    except Exception as e:
        return f"Erro de conexão durante upload: {e}"

def index_url(url: str):
    """Envia uma URL do Google Sheets para o servidor indexar."""
    server = get_server_url()
    try:
        response = requests.post(f"{server}/index_url", json={"url": url}, timeout=300)

        if response.status_code == 200:
            return response.json().get("message", "URL indexada com sucesso.")
        else:
            return f"Erro na indexação: {response.text}"
    except Exception as e:
        return f"Erro de conexão durante indexação da URL: {e}"
