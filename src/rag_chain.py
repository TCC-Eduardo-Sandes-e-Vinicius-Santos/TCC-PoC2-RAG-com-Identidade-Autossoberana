# import os
# import logging
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import Chroma
# from langchain_community.chat_models import ChatOllama
# from langchain_core.prompts import PromptTemplate
# from langchain_core.runnables import RunnablePassthrough
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.documents import Document
# from langchain.retrievers import EnsembleRetriever
# from langchain_community.retrievers import BM25Retriever

# os.environ["ANONYMIZED_TELEMETRY"] = "False"
# logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# logger = logging.getLogger(__name__)

# class SecureRAG:
#     def __init__(self, docs_path="data/documentos", persist_directory="data/chroma_db"):
#         self.docs_path = docs_path
#         self.persist_directory = persist_directory
   
#         self.embedding_model = HuggingFaceEmbeddings(
#             model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
#         )
#         self.llm = ChatOllama(model="llama3")
#         self.vector_store = None
        
#         self.prompt = PromptTemplate.from_template(
#             "Você é um assistente pessoal focado em privacidade. "
#             "Responda à pergunta baseando-se ESTRITAMENTE no contexto abaixo. "
#             "Se a resposta não estiver no contexto, diga 'Não tenho informações suficientes nos seus documentos para responder a isso.'\n\n"
#             "Contexto: {context}\n\n"
#             "Pergunta: {question}\n\n"
#             "Resposta:"
#         )

#     def ingest_documents(self, force_update=False):
#         logger.info("Iniciando rotina de ingestão...")

#         if force_update and self.vector_store:
#             logger.info("Apagando coleção antiga do ChromaDB...")
#             self.vector_store.delete_collection()
#             self.vector_store = None 
            
#         if not self.vector_store:
#             self.vector_store = Chroma(
#                 persist_directory=self.persist_directory, 
#                 embedding_function=self.embedding_model
#             )
            
#         try:
#             banco_tamanho = len(self.vector_store.get()['ids'])
#         except Exception:
#             banco_tamanho = 0
            
#         if banco_tamanho > 0 and not force_update:
#             logger.info(f"O banco já possui {banco_tamanho} trechos salvos. Pulando ingestão.")
#             return True
            
#         logger.info("Lendo e vetorizando documentos do zero. Isso pode demorar...")
        
#         if not os.path.exists(self.docs_path):
#             os.makedirs(self.docs_path)
            
#         txt_loader = DirectoryLoader(self.docs_path, glob="**/*.txt", loader_cls=TextLoader)
#         txt_docs = txt_loader.load()
        
#         pdf_loader = DirectoryLoader(self.docs_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
#         pdf_docs = pdf_loader.load()
        
#         documents = txt_docs + pdf_docs
        
#         if not documents:
#             logger.warning("Nenhum documento encontrado na pasta.")
#             return False
            
#         text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
#         chunks = text_splitter.split_documents(documents)
        
#         self.vector_store = Chroma.from_documents(
#             documents=chunks, 
#             embedding=self.embedding_model, 
#             persist_directory=self.persist_directory
#         )
#         self.vector_store.persist()
#         logger.info("Ingestão concluída com sucesso.")
#         return True

#     def _verify_consent(self, did_user, signature, consent_payload):
#         logger.info(f"Verificando permissões para o DID: {did_user}")
        
#         if not signature:
#             logger.error("Falha: Assinatura ausente ou inválida.")
#             return False
            
#         allow_rag = consent_payload.get("allow_rag", False)
        
#         if not allow_rag:
#             logger.warning(f"Bloqueio de Privacidade: A assinatura é válida, mas o usuário NÃO autorizou o uso do RAG.")
#             return False
            
#         logger.info("Sucesso: Assinatura válida e permissão concedida pelo usuário.")
#         return True

#     def query_with_consent(self, question, did_user, signature, consent_payload):
#         if not self._verify_consent(did_user, signature, consent_payload):
#             return "Acesso Negado: Falha na validação do consentimento criptográfico. O acesso aos seus dados foi bloqueado."

#         if not self.vector_store:
#             self.vector_store = Chroma(
#                 persist_directory=self.persist_directory, 
#                 embedding_function=self.embedding_model
#             )

#         all_data = self.vector_store.get()
#         if not all_data['documents']:
#             return "O banco de dados está vazio. Por favor, adicione documentos e atualize a base."

#         vector_retriever = self.vector_store.as_retriever(
#             search_type="mmr", 
#             search_kwargs={"k": 5, "fetch_k": 30}
#         )

#         documents = [Document(page_content=text) for text in all_data['documents']]
#         bm25_retriever = BM25Retriever.from_documents(documents)
#         bm25_retriever.k = 5

#         hybrid_retriever = EnsembleRetriever(
#             retrievers=[vector_retriever, bm25_retriever],
#             weights=[0.5, 0.5]
#         )

#         def format_docs(docs):
#             text_chunks = []
#             print("DEBUG DA BUSCA HÍBRIDA: O QUE A IA ESTÁ LENDO?")
#             print("="*50)
#             for i, doc in enumerate(docs):
#                 print(f"\n--- Trecho {i+1} ---")
#                 print(f"{doc.page_content[:200]}...") 
#                 text_chunks.append(doc.page_content)
#             print("\n" + "="*50 + "\n")
#             return "\n\n".join(text_chunks)

#         rag_chain = (
#             {"context": hybrid_retriever | format_docs, "question": RunnablePassthrough()}
#             | self.prompt
#             | self.llm
#             | StrOutputParser()
#         )

#         logger.info("Consentimento aprovado. Iniciando Busca Híbrida e gerando resposta...")
#         return rag_chain.invoke(question)

# # Bloco de execução para terminal
# if __name__ == "__main__":
#     print("--- Teste de Módulo: Secure RAG Híbrido ---")
#     rag = SecureRAG()
#     rag.ingest_documents()
#     resposta_valida = rag.query_with_consent(
#         question="Qual é o foco principal do projeto?", 
#         did_user="did:poc:12345", 
#         signature="assinatura_criptografica_valida", 
#         consent_payload={"allow_rag": True}
#     )
#     print(f"Resposta da IA: {resposta_valida}")

# ============================================================================================================

import os
import logging
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

os.environ["ANONYMIZED_TELEMETRY"] = "False"

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SecureRAG:
    def __init__(self, docs_path="data/documentos", persist_directory="data/chroma_db"):
        self.docs_path = docs_path
        self.persist_directory = persist_directory
        
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.llm = ChatOllama(model="llama3")
        self.vector_store = None
        
        # Prompt restrito ao contexto (Atende à US05)
        self.prompt = PromptTemplate.from_template(
            "Você é um assistente pessoal focado em privacidade. "
            "Responda à pergunta baseando-se ESTRITAMENTE no contexto abaixo. "
            "Se a resposta não estiver no contexto, diga 'Não tenho informações suficientes nos seus documentos para responder a isso.'\n\n"
            "Contexto: {context}\n\n"
            "Pergunta: {question}\n\n"
            "Resposta:"
        )

    def ingest_documents(self, force_update=False):
        logger.info("Iniciando rotina de ingestão...")
        
        # Limpeza via API do Chroma
        if force_update and self.vector_store:
            logger.info("Apagando coleção antiga do ChromaDB...")
            self.vector_store.delete_collection()
            self.vector_store = None 
            
        # Conecta ao banco de dados existente no HD
        if not self.vector_store:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory, 
                embedding_function=self.embedding_model
            )
            
        # Verifica se já existem dados salvos.
        try:
            banco_tamanho = len(self.vector_store.get()['ids'])
        except Exception:
            banco_tamanho = 0
            
        if banco_tamanho > 0 and not force_update:
            logger.info(f"O banco já possui {banco_tamanho} trechos salvos. Pulando ingestão.")
            return True
            
        logger.info("Lendo e vetorizando documentos do zero. Isso pode demorar...")
        
        # Garante que o diretório de documentos exista
        if not os.path.exists(self.docs_path):
            os.makedirs(self.docs_path)
            
        # Carrega os TXTs e PDFs
        txt_loader = DirectoryLoader(self.docs_path, glob="**/*.txt", loader_cls=TextLoader)
        txt_docs = txt_loader.load()
        
        pdf_loader = DirectoryLoader(self.docs_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
        pdf_docs = pdf_loader.load()
        
        documents = txt_docs + pdf_docs
        
        if not documents:
            logger.warning("Nenhum documento encontrado na pasta.")
            return False
            
        # Quebrar em pedaços menores (Chunks)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=6000, chunk_overlap=400)
        chunks = text_splitter.split_documents(documents)
        
        # Criar e persistir o banco vetorial
        self.vector_store = Chroma.from_documents(
            documents=chunks, 
            embedding=self.embedding_model, 
            persist_directory=self.persist_directory
        )
        self.vector_store.persist()
        logger.info("Ingestão concluída com sucesso.")
        return True

    def _verify_consent(self, did_user, public_key, signature, consent_payload):
        from crypto_did import CryptoDID 
        
        logger.info(f"Verificando permissões para o DID: {did_user}")
        
        if not signature:
            logger.error("Falha: Assinatura ausente.")
            return False
            
        allow_rag = consent_payload.get("allow_rag", False)
        
        if not allow_rag:
            logger.warning("Bloqueio de Privacidade: O usuário NÃO autorizou o uso do RAG.")
            return False

        is_valid = CryptoDID.verify_signature(
            public_key_b64=public_key,
            payload=consent_payload,
            signature_b64=signature
        )
        
        if not is_valid:
            logger.error("Acesso Negado: A assinatura não é válida ou o termo foi adulterado.")
            return False
            
        logger.info("Sucesso: Assinatura criptográfica válida e permissão concedida.")
        return True

    def query_with_consent(self, question, did_user, public_key, signature, consent_payload):
        # TRAVA LÓGICA DE PRIVACIDADE
        if not self._verify_consent(did_user, public_key, signature, consent_payload):
            return "Acesso Negado: Falha na validação do consentimento criptográfico. O acesso aos seus dados foi bloqueado."

        # Prepara o Banco Vetorial e o Retriever
        if not self.vector_store:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory, 
                embedding_function=self.embedding_model
            )

        all_data = self.vector_store.get()
        if not all_data['documents']:
            return "O banco de dados está vazio. Por favor, adicione documentos e atualize a base."

        retriever = self.vector_store.as_retriever(
            search_type="mmr", 
            search_kwargs={"k": 30, "fetch_k": 150}
        )

        # Função auxiliar para extrair o texto e imprimir o log no terminal
        def format_docs(docs):
            text_chunks = []
            print("\n" + "="*50)
            print("🔍 DEBUG DO RETRIEVER: O QUE A IA ESTÁ LENDO?")
            print("="*50)
            
            for i, doc in enumerate(docs):
                print(f"\n--- Trecho {i+1} ---")
                print(f"{doc.page_content[:200]}...") 
                text_chunks.append(doc.page_content)
                
            print("\n" + "="*50 + "\n")
            return "\n\n".join(text_chunks)

        # Montagem da cadeia de execução (Chain) usando LCEL
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

        logger.info("Consentimento aprovado. Recuperando contexto e gerando resposta local...")
        return rag_chain.invoke(question)

# Bloco de execução para testar o módulo isoladamente no terminal
if __name__ == "__main__":
    print("--- Teste de Módulo: Secure RAG ---")
    rag = SecureRAG()
    rag.ingest_documents()
    
    resposta_valida = rag.query_with_consent(
        question="Qual é o foco principal do projeto?", 
        did_user="did:poc:12345", 
        signature="assinatura_criptografica_valida", 
        consent_payload={"allow_rag": True}
    )
    print(f"\nResposta da IA: {resposta_valida}")