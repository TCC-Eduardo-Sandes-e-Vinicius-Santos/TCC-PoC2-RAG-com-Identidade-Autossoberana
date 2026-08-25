import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag_chain import SecureRAG

if __name__ == "__main__":
    print("--- Teste de Módulo: Secure RAG ---")
    rag = SecureRAG()
    rag.ingest_documents()
    
    resposta_valida = rag.query_with_consent(
        question="Qual é o foco principal do projeto?", 
        did_user="did:poc:12345",
        public_key="chave_publica_ficticia_em_base64",
        signature="assinatura_criptografica_valida", 
        consent_payload={"allow_rag": True}
    )
    print(f"\nResposta da IA: {resposta_valida}")
