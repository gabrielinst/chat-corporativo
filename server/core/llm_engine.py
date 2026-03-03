import time
import requests
from langchain_community.llms import Ollama

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "gemma3" # Alterado pelo feedback do usuário para contornar erro de Parser do Pandas Agent

def aguardar_ollama():
    """
    Verifica se o servidor do Ollama está online e respondendo.
    """
    print(f"Verificando conexão com Ollama em {OLLAMA_HOST}...")
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/version", timeout=5)
            if response.status_code == 200:
                print("Ollama está online!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"Tentativa {i+1} de {max_retries} falhou. Retentando em 2 segundos...")
        time.sleep(2)
        
    print("Aviso: Não foi possível conectar ao Ollama. Certifique-se de que ele esteja rodando localmente.")
    return False

def get_llm():
    """Retorna a instância configurada do modelo local."""
    return Ollama(
        base_url=OLLAMA_HOST,
        model=OLLAMA_MODEL,
        temperature=0.0 # Reduzida a temperatura pra 0 para o agente ser mais analítico e exato, evitando erros de parse (Json/Tools)
    )
