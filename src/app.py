import streamlit as st
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_chain import SecureRAG

st.set_page_config(page_title="Assistente IA - Autossoberano", layout="wide")

@st.cache_resource(show_spinner="Iniciando IA e carregando documentos...")
def initialize_rag():
    rag = SecureRAG(docs_path="data/documentos", persist_directory="data/chroma_db")
    rag.ingest_documents() 
    return rag

rag_system = initialize_rag()

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Identidade Autossoberana")
    st.caption("Controle local das suas credenciais.")
    
    did_user = st.text_input("Seu DID (Gerado Localmente)", value="did:poc:12345", disabled=True)
    signature = st.text_input("Assinatura Criptográfica", value="hash_assinatura_valida")
    
    st.divider()
    
    allow_rag = st.toggle("Autorizar IA a ler meus documentos", value=True)
    
    st.divider()
    
    st.info(
        "**Transparência e Privacidade:**\n"
        "Todo o processamento é executado localmente (Edge Computing). "
        "Suas imagens não são salvas e o modelo de linguagem não acessa a internet."
    )
    
    st.divider()
    st.subheader("Gerenciar Documentos")
    
    with st.form("upload_form", clear_on_submit=True):
        uploaded_files = st.file_uploader(
            "Adicione novos documentos à base da IA", 
            type=["pdf", "txt"], 
            accept_multiple_files=True
        )
        
        submitted = st.form_submit_button("Salvar e Processar Arquivos")

    if submitted:
        if uploaded_files:
            with st.spinner("Salvando no disco e vetorizando (Isso pode demorar)..."):
                os.makedirs("data/documentos", exist_ok=True)
                for file in uploaded_files:
                    file_path = os.path.join("data/documentos", file.name)
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer()) 
                
                rag_system.ingest_documents(force_update=True)
                st.success("Arquivos salvos e IA atualizada com sucesso!")
        else:
            st.warning("Por favor, selecione pelo menos um arquivo antes de salvar.")

    st.write("---")

    st.caption("Se você moveu arquivos manualmente para a pasta:")
    if st.button("Sincronizar Pasta Local"):
        with st.spinner("Lendo a pasta e recriando a base vetorial..."):
            rag_system.ingest_documents(force_update=True)
            st.success("Base de dados sincronizada com a pasta local!")


    st.divider()
    st.subheader("Exportar Identidade")

    # Construção do JSON
    identidade_json = {
        "type": ["VerifiableCredential", "IdentityCredential"],
        "issuer": "did:poc:sistema_local_tcc",
        "issuanceDate": "2026-08-12T12:00:00Z", 
        "credentialSubject": {
            "id": did_user,
            "alegacoes": {
                "maior_de_idade": True 
            },
            "permissoes": {
                "allow_rag": allow_rag
            }
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "signatureValue": signature
        }
    }

    json_string = json.dumps(identidade_json, indent=4)

    st.download_button(
        label="Baixar Identidade Digital (.json)",
        file_name="minha_identidade_autossoberana.json",
        mime="application/json",
        data=json_string
    )

st.title("Assistente Pessoal Offline")
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