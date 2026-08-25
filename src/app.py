import streamlit as st
import os
import sys
import json
from rag_chain import SecureRAG
from crypto_did import CryptoDID
from biometric_verifier import BiometricVerifier, AgeAnalysisError
import cv2
import numpy as np

os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"

if sys.platform == "linux":
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="Assistente IA - Autossoberano", layout="wide")

@st.cache_resource(show_spinner="Iniciando IA e carregando documentos...")
def initialize_rag():
    rag = SecureRAG(docs_path="data/documentos", persist_directory="data/chroma_db")
    rag.ingest_documents() 
    return rag

rag_system = initialize_rag()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "crypto" not in st.session_state:
    st.session_state.crypto = CryptoDID()
if "identidade" not in st.session_state:
    st.session_state.identidade = None
if "age_claim" not in st.session_state:
    st.session_state.age_claim = None
if "signature" not in st.session_state:
    st.session_state.signature = None

with st.sidebar:
    st.header("Identidade Autossoberana")
    st.caption("Controle local das suas credenciais.")
    
    if not st.session_state.identidade:
        if st.button("Gerar Identidade (DID)", type="primary", use_container_width=True):
            with st.spinner("Gerando chaves..."):
                st.session_state.identidade = st.session_state.crypto.generate_identity()
            st.rerun()
    else:
        st.success("Identidade Gerada com Sucesso!")
        did_user = st.text_input("Seu DID", value=st.session_state.identidade["did"], disabled=True)
        pub_key = st.text_input("Chave Pública (Base64)", value=st.session_state.identidade["public_key"], disabled=True)
        
        st.divider()
        st.subheader("Verificação Etária")
        
        if not st.session_state.age_claim:
            st.info("A IA só será liberada após a comprovação de maioridade.")
            
            picture = st.camera_input("Tire uma foto para comprovar maioridade")
            
            if picture is not None:
                with st.spinner("Analisando rosto..."):
                    try:
                        bytes_data = picture.getvalue()
                        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                        
                        verifier = BiometricVerifier()
                        claim = verifier.verify_age_from_array(image_array=cv2_img, did_subject=did_user)
                        
                        if claim.is_adult:
                            st.session_state.age_claim = claim.to_dict()
                            st.rerun()
                        else:
                            st.error("Acesso Negado: Sistema restrito para maiores de 18 anos.")
                    except AgeAnalysisError as e:
                        st.error(f"Rosto não detectado ou erro na leitura: {e}")
        else:
            st.success(f"Maioridade Confirmada! (Idade est. {st.session_state.age_claim['estimated_age']} anos)")

        st.divider()
        allow_rag = st.toggle("Autorizar IA a ler meus documentos", value=True)
        
        consent_payload = {"allow_rag": allow_rag, "did": did_user}
        st.session_state.signature = st.session_state.crypto.sign_payload(consent_payload)
        
        st.text_input("Sua Assinatura Criptográfica (Consentimento)", value=st.session_state.signature, disabled=True)
        
        st.divider()
        st.info(
            "**Transparência e Privacidade:**\n"
            "Todo o processamento é executado localmente (Edge Computing). "
            "Suas imagens não são salvas e o modelo de linguagem não acessa a internet."
        )
        
        st.divider()
        st.subheader("Exportar Identidade")
        
        identidade_json = {
            "type": ["VerifiableCredential", "IdentityCredential"],
            "issuer": "did:poc:sistema_local_tcc",
            "issuanceDate": "2026-08-12T12:00:00Z", 
            "credentialSubject": {
                "id": did_user,
                "public_key": st.session_state.identidade["public_key"],
                "alegacoes": st.session_state.age_claim,
                "permissoes": consent_payload
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "signatureValue": st.session_state.signature
            }
        }
        json_string = json.dumps(identidade_json, indent=4)
        st.download_button(
            label="Baixar Identidade Digital (.json)",
            file_name="minha_identidade_autossoberana.json",
            mime="application/json",
            data=json_string,
            use_container_width=True
        )

st.title("Assistente Pessoal Offline")

if not st.session_state.identidade or not st.session_state.age_claim:
    st.warning("Gere a identidade e faça a verificação etária na barra lateral para liberar o acesso ao assistente.")
else:
    st.markdown("Interaja com seus arquivos locais. O acesso da IA é condicionado ao seu consentimento na barra lateral.")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Pergunte algo sobre seus documentos..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        consent_payload = {"allow_rag": allow_rag, "did": st.session_state.identidade["did"]}

        with st.chat_message("assistant"):
            with st.spinner("Validando consentimento e gerando resposta (Isso pode levar alguns minutos)..."):
                resposta = rag_system.query_with_consent(
                    question=prompt,
                    did_user=st.session_state.identidade["did"],
                    public_key=st.session_state.identidade["public_key"],
                    signature=st.session_state.signature, 
                    consent_payload=consent_payload 
                )
                st.markdown(resposta)
        
        st.session_state.messages.append({"role": "assistant", "content": resposta})