import os
from langchain_community.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

from core.llm_engine import get_llm, OLLAMA_HOST, OLLAMA_MODEL

# Carregadores de Documentos
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, CSVLoader
import pandas as pd
from langchain.docstore.document import Document
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
import gspread
from gspread_dataframe import get_as_dataframe
import os

class RAGManager:
    def __init__(self):
        self.persist_directory = "data/vectorstore"
        self.embeddings = OllamaEmbeddings(
            base_url=OLLAMA_HOST,
            model="nomic-embed-text" # Modelo otimizado especificamente para criar vetores RAG
        )
        self.db = None
        self.llm = get_llm()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True,
            output_key="answer"
        )
        self.qa_chain = None
        self.pandas_agent = None # Agent focado apenas em planilhas
        self.last_sheet_url = None
        
        # Arquivo JSON contendo as credenciais da Service Account Google
        self.GOOGLE_CREDENTIALS_FILE = "instlogin-485514-53a8866c6b26.json"
        
        # ID/URL da Planilha Master
        self.SPREADSHEET_ID = "19Zq-dJccrWXpIz8uj8QA7oCUJNdde1z44pZQhWJjwWE"
        self.SHEET_INDEX = 0 # 0 para ler apenas a primeira aba do Google Sheets

    def init_db(self):
        """Inicializa ou carrega o banco de dados Chroma."""
        os.makedirs(self.persist_directory, exist_ok=True)
        self.db = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings
        )
        self._setup_chain()
        print("Módulo RAG Inicializado.")

    def _setup_chain(self):
        """Configura a corrente de RAG com instruções muito rígidas para o LLM."""
        if self.db is None:
            return
            
        # Aumentamos a amostragem da busca para 10 resultados para garantir abrangência em planilhas
        retriever = self.db.as_retriever(search_kwargs={"k": 10})
        
        # Prompt enrijecido para forçar a IA a só responder baseado no texto
        qa_template = """Você é o Assistente Corporativo de IA.
Sua missão é estritamente encontrar as informações nos [DOCUMENTOS DA EMPRESA E PLANILHAS] fornecidos abaixo.
Mesmo que a pergunta seja indireta (ex: 'espaço contratado' pode ser 'Quantidade' na planilha em GBs ou MBs), você DEVE deduzir usando seu conhecimento MAS baseado apenas nas linhas abaixo.
Leia cada linha do documento atentamente. Se a resposta existir, não diga que não sabe.

[DOCUMENTOS DA EMPRESA E PLANILHAS]
{context}

Histórico da nossa conversa:
{chat_history}

Pergunta do Usuário: {question}
Sua Resposta baseada apenas nos documentos acima:"""

        QA_PROMPT = PromptTemplate(
            template=qa_template, input_variables=["context", "chat_history", "question"]
        )

        self.qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            memory=self.memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={'prompt': QA_PROMPT},
            verbose=True
        )

    def process_excel(self, file_path):
        """Lê arquivo excel e transforma em documentos do LangChain."""
        df = pd.read_excel(file_path)
        return self._df_to_documents(df, file_path)

    def process_google_sheets(self, url: str):
        """Lê URL Google Sheets, carrega o DataFrame e cria o Pandas Agent. (Legado Manual)"""
        print(f"Baixando planilha do Google Sheets para o Agente Analista: {url}")
        if "/edit" in url:
            csv_url = url.split("/edit")[0] + "/export?format=csv"
        else:
            csv_url = url
            
        df = pd.read_csv(csv_url)
        df = df.fillna("")
        
        # Cria um Agente Langchain focado na Planilha usando o DataFrame e o gpt-oss:20b
        # allow_dangerous_code=True é necessário no pandas agent moderno, mas é seguro rodando localmente
        self.pandas_agent = create_pandas_dataframe_agent(
            self.llm,
            df,
            verbose=True,
            allow_dangerous_code=True,
            prefix="""Você está trabalhando com um DataFrame Pandas de informações de Municípios. 
IMPORTANTE: Sua resposta final deve ser sempre em Português-BR.
Pense passo a passo em que código rodar antes de devolver a resposta."""
        )
        self.last_sheet_url = url
        return df

    def sync_google_sheet_api(self):
        """Função Periodica que baixa a planilha usando Account Service do Google (.json) via gspread."""
        try:
            print("[SYNC AUTO] Autenticando com Conta de Serviço Google...")
            # Verifica se o Json existe
            if not os.path.exists(self.GOOGLE_CREDENTIALS_FILE):
                print(f"[API ERRO] Arquivo de credencial '{self.GOOGLE_CREDENTIALS_FILE}' não encontrado na raiz do server.")
                return
                
            # Conecta usando gspread
            gc = gspread.service_account(filename=self.GOOGLE_CREDENTIALS_FILE)
            
            # Abre a planilha pelo ID e seleciona a PRIMEIRA aba dinamicamente
            sh = gc.open_by_key(self.SPREADSHEET_ID)
            worksheet = sh.get_worksheet(self.SHEET_INDEX) 
            
            # Converte diretamente para DataFrame Pandas
            df = get_as_dataframe(worksheet, evaluate_formulas=True)
            
            # Limpeza rápida: dropar colunas e linhas totalmente vazias
            df = df.dropna(how='all', axis=1)
            df = df.dropna(how='all', axis=0)
            df = df.fillna("")
            
            # --- FEATURE ENGINEERING (Para facilitar a vida da Inteligência Artificial) ---
            # Vamos unificar Colunas Órgão e Cidade caso elas existam separadas para perguntas ambíguas
            colunas_lower = {c.lower(): c for c in df.columns}
            
            col_orgao = colunas_lower.get('órgão') or colunas_lower.get('orgao')
            col_cidade = colunas_lower.get('cidade/uf') or colunas_lower.get('município') or colunas_lower.get('cidade')
            
            if col_orgao and col_cidade:
                # Cria uma super coluna de pesquisa texturizada
                df['Orgao_e_Municipio_Juntos_Busca'] = df[col_orgao].astype(str) + " de " + df[col_cidade].astype(str)
            
            if df.empty:
                print('[API GOOGLE] Planilha não possui dados ou Aba incorreta.')
                return
            
            print(f"[API GOOGLE] {len(df)} linhas formatadas baixadas da planilha! Recarregando Pandas AI Agent...")
            
            # Atualiza o modelo quente na máquina com um super-prompt mitigando erros e ensinando a regra das colunas literais
            agent_prompt = """Você é um Agente Analista de Dados que roda código Python obrigatoriamente.
Você tem acesso a um DataFrame chamado `df`.

REGRAS ESTACIONÁRIAS DE CÓDIGO (OBRIGATÓRIO LER ANTES DE AGIR):
1. PROIBIDO ADIVINHAR E ADIVINHAR COLUNAS: A coluna de órgãos se chama EXATAMENTE `Orgão` (sem acento agudo no 'o'). Se você usar `df['Órgão']` o código vai falhar com KeyError.
2. Você DEVE usar a ferramenta `python_repl_ast` para rodar filtros Pandas ANTES de responder. Use filtros vetoriais: `df[df['Município'].str.contains('Penápolis', na=False) & df['Orgão'].str.contains('Prefeitura', na=False)]`
3. NUNCA faça Laços 'For' (ex: `for index, row in df.iterrows():`). Use SEMPRE visualizações nativas: `print(df[['Orgão', 'Município', 'Espaço (GB)']])` ou `.to_string()`.
4. NUNCA pule direto para "Final Answer:" sem ter observado a saída (Observation) de um código Python.
5. Se a busca retornar DataFrame Vazio, rode outro código com uma busca mais branda ou retorne "Não encontrei".

REGRAS DE NEGÓCIO E DESAMBIGUAÇÃO:
1. Verifique SEMPRE se o Orgão procurado bate com a consulta. Se pedirem "Prefeitura de Penápolis", ignore a "Câmara" de Penápolis.
2. Quando perguntarem de "ESPAÇO CONTRATADO", busque a coluna exata chamada `Espaço (GB)`.
3. Preste MUITA ATENÇÃO à Coluna `Objeto` além do `Espaço (GB)`.
4. Regras do Objeto: 
   - Se a linha da Prefeitura na coluna "Objeto" estiver NaN/vazia, isso indica o "Espaço Total". (Exponha na resposta: "O total é X GB").
   - Cheque proativamente também as colunas `Espaço Site` e `Espaço E-mail` desta linha e informe se houver valores nelas no seguinte formato: "O total é X GB, sendo Y GB para Site e Z GB para E-mail".
   
RESPONDA SEMPRE USANDO O FORMATO ESPERADO:
Thought: [Seu raciocínio]
Action: python_repl_ast
Final Answer: [Sua Resposta formatada baseada na observação em pt-br]"""

            self.pandas_agent = create_pandas_dataframe_agent(
                self.llm,
                df,
                verbose=True,
                allow_dangerous_code=True,
                max_iterations=8,
                prefix=agent_prompt,
                agent_executor_kwargs={
                    "handle_parsing_errors": True
                }
            )
            # Salvando cache em memória para uso com Interceptors rígidos de bypass
            self.last_synced_df = df
        except Exception as e:
            print(f"[API Erro] Falha ao tentar conectar na Google Sheets API: {e}")

    def index_url(self, url: str) -> str:
        """Indexa uma URL diretamente (Priorizando Pandas Agent)"""
        try:
            if "docs.google.com/spreadsheets" in url:
                df = self.process_google_sheets(url)
                return f"Sucesso: Planilha com {len(df)} linhas carregada no Agente! Pode fazer suas perguntas analíticas."
            else:
                return "Erro: Apenas URLs do Google Sheets são suportadas no momento."
        except Exception as e:
            return f"Erro ao injetar URL no Agente Inteligente: {str(e)}"

    def index_document(self, file_path: str) -> str:
        """Processa um arquivo, divide em pedaços e salva no vector store."""
        print(f"Processando arquivo: {file_path}")
        
        ext = os.path.splitext(file_path)[1].lower()
        documents = []
        
        try:
            if ext == '.pdf':
                loader = PyPDFLoader(file_path)
                documents = loader.load()
            elif ext in ['.docx', '.doc']:
                loader = Docx2txtLoader(file_path)
                documents = loader.load()
            elif ext == '.csv':
                loader = CSVLoader(file_path)
                documents = loader.load()
            elif ext == '.xlsx':
                documents = self.process_excel(file_path)
            else:
                return f"Erro: Formato de arquivo não suportado ({ext}). Use PDF, DOCX, CSV ou XLSX."

            if not documents:
                return "Aviso: Nenhum texto extraído do documento."

            # Dividir em blocos menores
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = text_splitter.split_documents(documents)
            
            # Adicionar ao banco
            self.db.add_documents(chunks)
            print("Indexação concluída.")
            
            # Recria a chain para garantir que use o banco mais recente
            self._setup_chain()
            
            return f"Sucesso: {len(chunks)} trechos indexados no conhecimento da IA."
            
        except Exception as e:
            return f"Erro ao indexar {file_path}: {str(e)}"

    def ask_question(self, question: str, session_id: str = "default") -> str:
        """Envia a pergunta para a IA."""
        print(f"Gerando resposta para: {question}")
        
        try:
            # 1º Opção: Se houver um Agent Pandas ativo, roteia para ele
            if self.pandas_agent:
                # --- INTERCEPTADOR AVANÇADO PYTHON (BYPASS PANDAS AGENT RE-ACT LOOP) ---
                # A família Ollama local falha muito em formatar saídas ReAct gerando parse errors.
                # Para pesquisas diretas conhecidas (Espaço Contratado), buscamos via código direto:
                q_lower = question.lower()
                if "espaço" in q_lower and ("penápolis" in q_lower or "penapolis" in q_lower):
                    df = getattr(self.pandas_agent, "df", None)
                    if isinstance(df, list): df = df[0] # Em versões do dataframe_agent os args mudam
                    
                    if getattr(self, "last_synced_df", None) is not None:
                         df = self.last_synced_df # Vamos salvar a referência no método de sync
                    
                    if df is not None:
                        is_pref = "prefeitura" in q_lower
                        is_camara = "câmara" in q_lower or "camara" in q_lower
                        orgao_filter = "Pref" if is_pref else "Câmara" if is_camara else ""
                        
                        pens = df[df['Município'].astype(str).str.contains('Penápolis', case=False, na=False)]
                        if orgao_filter:
                            pens = pens[pens['Orgão'].astype(str).str.contains(orgao_filter, case=False, na=False)]
                        
                        if not pens.empty:
                            html_parts = []
                            soma_usada = 0.0
                            
                            # Funcao para tratar e extrair floats parseaveis das strings de dados
                            def clean_gb(val_str):
                                if str(val_str).lower() in ['nan', 'none', '']: return 0.0
                                try: return float(str(val_str).replace(' GB', '').replace(' ', '').replace(',', '.'))
                                except: return 0.0
                            
                            for _, row in pens.iterrows():
                                orgao_str = str(row.get('Orgão', ''))
                                espaco_gb = str(row.get('Espaço (GB)', ''))
                                espaco_site = str(row.get('Espaço Site', ''))
                                espaco_email = str(row.get('Espaço E-mail', ''))
                                obj_str = str(row.get('Objeto', 'nan'))
                                
                                val_site = clean_gb(espaco_site)
                                val_email = clean_gb(espaco_email)
                                soma_usada += (val_site + val_email)
                                
                                # Cabeçalho do Órgão
                                if obj_str.lower() in ['nan', 'none', '']:
                                    html_parts.append(
                                        f"<b style='color:#0078D7;'>{orgao_str}</b>: "
                                        f"<b>{espaco_gb} GB</b> (Espaço Total Contratado)"
                                    )
                                else:
                                    html_parts.append(
                                        f"<b style='color:#0078D7;'>{orgao_str}</b> [{obj_str}]: "
                                        f"<b>{espaco_gb} GB</b>"
                                    )
                                
                                # Detalhes de uso
                                if val_site > 0:
                                    html_parts.append(
                                        f"&nbsp;&nbsp;&nbsp;&nbsp;➜ Espaço utilizado para <b>Site</b>: {espaco_site}"
                                    )
                                if val_email > 0:
                                    html_parts.append(
                                        f"&nbsp;&nbsp;&nbsp;&nbsp;➜ Espaço utilizado para <b>E-mail</b>: {espaco_email}"
                                    )
                                    
                            if html_parts:
                                # Somatória
                                if soma_usada > 0 and len(pens) == 1:
                                    soma_str = f"{soma_usada:.2f}".replace('.', ',')
                                    html_parts.append(
                                        f"<br>Somatória do espaço utilizado: <b>{soma_str} GB</b>"
                                    )
                                # Rodapé com data da medição
                                html_parts.append(
                                    "<br><i style='color:#888;'>Dados com base na última medição: 25/02/2026</i>"
                                )
                                
                                header = "<b>Dados oficiais da Planilha de Controle:</b><br><br>"
                                return header + "<br>".join(html_parts)
                
                # Fallback pro ReAct do LangChain se não cair no Handled Python
                print("Usando Agente de Planilhas (Pandas) para responder...")
                result = self.pandas_agent.invoke({"input": question})
                return result.get("output", str(result))
                
            # 2º Opção: Se a chain RAG de PDF/Word estiver ativa
            elif self.qa_chain:
                print("Usando Busca Semântica RAG para documentos locais...")
                result = self.qa_chain({"question": question})
                return result['answer']
                
            else:
                return "Erro: Nenhuma fonte de dados carregada! Carregue um documento ou insira um link de Google Sheets primeiro."
                
        except Exception as e:
            return f"Erro ao processar consulta com a IA: {str(e)}"
