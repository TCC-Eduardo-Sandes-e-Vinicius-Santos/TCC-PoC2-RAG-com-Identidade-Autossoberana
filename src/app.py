import streamlit as st
import os
import sys

# Garante que o Python encontre o arquivo rag_chain.py no mesmo diretório
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_chain import SecureRAG

# Configuração da página
st.set_page_config(page_title="Assistente IA - Autossoberano", page_icon="🛡️", layout="wide")

# ==========================================
# Otimização: Cache da Ingestão
# ==========================================
# A "mágica" acontece aqui. O Streamlit roda essa função UMA VEZ.
# Ele cria o banco e guarda na memória. O app não vai mais travar a cada F5.
@st.cache_resource(show_spinner="Iniciando IA e carregando documentos...")
def initialize_rag():
    rag = SecureRAG(docs_path="data/documentos", persist_directory="data/chroma_db")
    # Tenta fazer a ingestão apenas se houver documentos na primeira inicialização
    rag.ingest_documents() 
    return rag

# Inicializa o sistema RAG usando a função com cache
rag_system = initialize_rag()

# Inicializa o histórico do chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# BARRA LATERAL: Identidade e Permissões
# ==========================================
with st.sidebar:
    st.header("🛡️ Identidade Autossoberana")
    st.caption("Controle local das suas credenciais.")
    
    did_user = st.text_input("Seu DID (Gerado Localmente)", value="did:poc:12345", disabled=True)
    signature = st.text_input("Assinatura Criptográfica", value="hash_assinatura_valida")
    
    st.divider()
    
    st.subheader("Controle de Permissões (US03)")
    allow_rag = st.toggle("Autorizar IA a ler meus documentos", value=True)
    
    st.divider()
    
    st.info(
        "🔒 **Transparência e Privacidade:**\n"
        "Todo o processamento é executado localmente (Edge Computing). "
        "Suas imagens não são salvas e o modelo de linguagem não acessa a internet."
    )
    
    # Botão para forçar a re-ingestão manual se o usuário adicionar novos arquivos
    if st.button("Atualizar Base de Documentos (Recarregar PDFs)"):
        with st.spinner("Processando novos arquivos... Isso pode demorar de acordo com o tamanho dos PDFs."):
            rag_system.ingest_documents(force_update=True)
            st.success("Documentos atualizados no banco vetorial!")

# ==========================================
# ÁREA PRINCIPAL: O Chat (US05)
# ==========================================
st.title("Assistente Pessoal Offline 🧠")
st.markdown("Interaja com seus arquivos locais. O acesso da IA é condicionado ao seu consentimento na barra lateral.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Pergunte algo sobre seus documentos..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    consent_payload = {"allow_rag": allow_rag}

    with st.chat_message("assistant"):
        with st.spinner("Validando consentimento e gerando resposta (Isso pode levar alguns segundos)..."):
            resposta = rag_system.query_with_consent(
                question=prompt,
                did_user=did_user,
                signature=signature, 
                consent_payload=consent_payload 
            )
            st.markdown(resposta)
    
    st.session_state.messages.append({"role": "assistant", "content": resposta})