import streamlit as st
import os
import sys
import json
import base64
import subprocess
import uuid
from datetime import datetime, timezone, timedelta

os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"

if sys.platform == "linux":
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_chain import SecureRAG
from crypto_did import CryptoDID

BIOMETRIC_WORKER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biometric_worker.py")
KEYSTORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "keystore", "identidade.json")

CONSENT_VALIDITY_MINUTES = 15

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
if "consent_payload" not in st.session_state:
    st.session_state.consent_payload = None

with st.sidebar:
    st.header("Identidade Autossoberana")
    st.caption("Controle local das suas credenciais.")
    
    if not st.session_state.identidade:
        keystore_found = CryptoDID.keystore_exists(KEYSTORE_PATH)

        modo = st.radio(
            "O que você quer fazer?",
            ["Carregar identidade salva", "Gerar nova identidade"] if keystore_found else ["Gerar nova identidade"],
            horizontal=False,
        )

        if modo == "Carregar identidade salva":
            st.caption("Identidade salva encontrada localmente. Digite a senha para desbloqueá-la.")
            senha_login = st.text_input("Senha do keystore", type="password", key="senha_login")
            if st.button("Carregar Identidade", type="primary", use_container_width=True):
                try:
                    with st.spinner("Descriptografando keystore local..."):
                        crypto_carregado = CryptoDID.load_keystore(senha_login, KEYSTORE_PATH)
                    st.session_state.crypto = crypto_carregado
                    st.session_state.identidade = {
                        "did": crypto_carregado.did,
                        "public_key": crypto_carregado.public_key_b64,
                    }
                    st.rerun()
                except (ValueError, FileNotFoundError, json.JSONDecodeError):
                    st.error("Não foi possível carregar a identidade: senha incorreta.")
        else:
            st.caption(
                "A chave privada só existe em memória durante esta sessão, a menos "
                "que você defina uma senha para salvá-la localmente, criptografada, "
                "e reutilizar o mesmo DID nas próximas sessões."
            )
            senha_nova = st.text_input(
                "Senha para proteger o keystore (opcional)",
                type="password",
                key="senha_nova",
                help="Deixe em branco para uma identidade válida só nesta sessão (comportamento anterior).",
            )
            if st.button("Gerar Identidade (DID)", type="primary", use_container_width=True):
                with st.spinner("Gerando chaves Ed25519..."):
                    st.session_state.identidade = st.session_state.crypto.generate_identity()
                    if senha_nova:
                        st.session_state.crypto.save_keystore(senha_nova, KEYSTORE_PATH)
                        st.toast("Identidade salva localmente e criptografada com sua senha.", icon="🔐")
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
                with st.spinner("Analisando imagem..."):
                    try:
                        bytes_data = picture.getvalue()
                        b64_image = base64.b64encode(bytes_data).decode("utf-8")

                        result = subprocess.run(
                            [sys.executable, BIOMETRIC_WORKER_PATH, did_user],
                            input=b64_image,
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )

                        if result.returncode != 0 and not result.stdout.strip():
                            st.error(f"Erro no processo de verificação biométrica: {result.stderr.strip() or 'falha desconhecida'}")
                        else:
                            output = json.loads(result.stdout.strip().splitlines()[-1])

                            if output.get("ok"):
                                claim_dict = output["claim"]
                                if claim_dict["value"]:
                                    st.session_state.age_claim = claim_dict
                                    st.rerun()
                                else:
                                    st.error("Acesso Negado: Sistema restrito para maiores de 18 anos.")
                            else:
                                st.error(f"Rosto não detectado ou erro na leitura: {output.get('error')}")

                    except subprocess.TimeoutExpired:
                        st.error("Tempo limite excedido na verificação biométrica. Tente novamente.")
                    except (json.JSONDecodeError, IndexError):
                        st.error("Resposta inesperada do processo de verificação biométrica.")
        else:
            st.success(f"Maioridade Confirmada! (Idade est. {st.session_state.age_claim['estimated_age']} anos)")

        st.divider()
        allow_rag = st.toggle("Autorizar IA a ler meus documentos", value=True)

        renovar = st.button(
            "Renovar consentimento",
            use_container_width=True,
            help=f"O consentimento assinado expira {CONSENT_VALIDITY_MINUTES} min após ser gerado.",
        )

        precisa_assinar = (
            st.session_state.consent_payload is None
            or st.session_state.consent_payload.get("allow_rag") != allow_rag
            or renovar
        )

        if precisa_assinar:
            agora = datetime.now(timezone.utc)
            consent_payload = {
                "allow_rag": allow_rag,
                "did": did_user,
                "issued_at": agora.isoformat(),
                "expires_at": (agora + timedelta(minutes=CONSENT_VALIDITY_MINUTES)).isoformat(),
            }
            st.session_state.consent_payload = consent_payload
            st.session_state.signature = st.session_state.crypto.sign_payload(consent_payload)

        consent_payload = st.session_state.consent_payload

        st.text_input("Sua Assinatura Criptográfica (Consentimento)", value=st.session_state.signature, disabled=True)
        st.caption(f"Consentimento válido até `{consent_payload['expires_at']}` (UTC).")
        
        st.divider()
        st.info(
            "**Transparência e Privacidade:**\n"
            "Todo o processamento é executado localmente (Edge Computing). "
            "Suas imagens não são salvas e o modelo de linguagem não acessa a internet."
        )
        
        st.divider()
        st.subheader("Exportar Identidade")

        credential_id = f"urn:uuid:{uuid.uuid4()}"
        issuance_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        identidade_json = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1",
            ],
            "id": credential_id,
            "type": ["VerifiableCredential", "IdentityCredential"],
            "issuer": did_user,
            "issuanceDate": issuance_date,
            "expirationDate": consent_payload["expires_at"],
            "credentialSubject": {
                "id": did_user,
                "public_key": st.session_state.identidade["public_key"],
                "alegacoes": st.session_state.age_claim,
                "permissoes": consent_payload
            },
            "proof": {
                "type": "Ed25519Signature2020",
                "created": issuance_date,
                "proofPurpose": "assertionMethod",
                "verificationMethod": f"{did_user}#key-1",
                "proofValue": st.session_state.signature
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

        consent_payload = st.session_state.consent_payload

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
