# Arquitetura Técnica

## Introdução

<div align="justify">&emsp;&emsp;
Este documento descreve o funcionamento interno da PoC: os módulos que a compõem, como eles se comunicam, o fluxo de dados desde a geração da identidade até a resposta do RAG, e as decisões de design de segurança e privacidade adotadas.
</div>

---

## Visão Geral dos Componentes

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         Processo Streamlit (app.py)                     │
│                                                                         │
│  ┌───────────────────┐   ┌──────────────────┐   ┌────────────────────┐  │
│  │   crypto_did.py   │   │   rag_chain.py   │   │  session_state     │  │
│  │  (DID, assinatura,│   │  (ChromaDB, LLM, │   │  (identidade,      │  │
│  │   keystore)       │   │   retrievers)    │   │   age_claim,       │  │
│  └────────┬──────────┘   └─────────┬────────┘   │   consent_payload, │  │
│           │                        │            │   signature)       │  │
│           │                        │            └────────────────────┘  │
└───────────┼────────────────────────┼────────────────────────────────────┘
            │                        │
            │ subprocess.run()       │ chamadas locais (Ollama HTTP)
            ▼                        ▼
┌─────────────────────────────┐   ┌──────────────────────────┐
│ biometric_worker.py         │   │  Ollama (llama3, local)  │
│ (processo filho,            │   │  http://localhost:11434  │
│  encerra após uso)          │   └──────────────────────────┘
│                             │
│  ┌───────────────────────┐  │
│  │ biometric_verifier.py │  │
│  │ (DeepFace/TensorFlow) │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

**Por que essa separação?** O processo principal (Streamlit) nunca importa `DeepFace`/TensorFlow diretamente, mas sim delega a inferência biométrica a um subprocesso curto, que morre assim que entrega o resultado. Isso alivia o uso de memória do processo principal durante toda a sessão de chat (ver `docs/otimizacoes-e-aprendizados.md`, seção de Usabilidade).

---

## Módulos

### `crypto_did.py` - Identidade e Criptografia

Responsável por toda a criptografia assimétrica da PoC. Usa **Ed25519** (`cryptography.hazmat.primitives.asymmetric.ed25519`) por ser um esquema de assinatura moderno, rápido e com chaves curtas (32 bytes).

| Método                                                                  | Função                                                                                                                                                                                                                                                                                                                          |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `generate_identity()`                                                   | Gera par de chaves Ed25519 e deriva o DID como `did:poc:<sha256(chave_pública)[:16]>`. Método específico da PoC (`did:poc`), não registrado em nenhum DID Method Registry público.                                                                                                                                              |
| `sign_payload(payload: dict)`                                           | Serializa o dict com `json.dumps(..., sort_keys=True, separators=(',', ':'))` determinístico, independente da ordem de inserção das chaves e assina os bytes resultantes.                                                                                                                                                   |
| `verify_signature(public_key_b64, payload, signature_b64)` *(estático)* | Reconstrói a chave pública a partir do base64, repete a mesma serialização determinística, e verifica a assinatura com `Ed25519PublicKey.verify()`. Usado pelo `rag_chain.py` para validar o consentimento.                         |
| `save_keystore(password, path)`                                         | Persiste a chave privada em disco, nunca em texto puro: deriva uma chave simétrica da senha via PBKDF2-HMAC-SHA256 (480.000 iterações, salt aleatório de 16 bytes) e criptografa a chave privada com Fernet (AES-128-CBC + HMAC). DID e chave pública ficam em texto puro no arquivo (são dados públicos por natureza). |
| `load_keystore(password, path)` *(classmethod)*                         | Deriva a mesma chave simétrica a partir da senha + salt salvos, decripta e reconstrói uma instância `CryptoDID` completa. Levanta `ValueError` se a senha estiver errada.                                                                                                                                                       |
| `keystore_exists(path)` *(estático)*                                    | Apenas checa se já existe um keystore salvo, para a UI decidir entre oferecer "gerar nova identidade" ou "carregar identidade salva".                                                                                                                                                                                           |

**Por que a serialização determinística importa:** se o `json.dumps` não usasse `sort_keys=True`, o mesmo payload lógico (`{"a": 1, "b": 2}` vs `{"b": 2, "a": 1}`) produziria bytes diferentes e, portanto, quebraria a verificação de assinatura mesmo quando os dados forem semanticamente idênticos.

### `biometric_verifier.py` - Inferência Etária Local

Encapsula o uso do `DeepFace` para estimar a idade a partir de uma imagem, sem nunca persistir a imagem em disco.

- `AgeClaim` (dataclass): representa a alegação etária, a qual carrega apenas `is_adult` (bool), `estimated_age` (int), `minimum_age_threshold`, `issued_at` e `method`. **Nunca carrega a imagem ou dados biométricos brutos.** Isso implementa o princípio de **minimização de dados**: a alegação assinada e exportada revela só o necessário ("é maior de idade").
- `BiometricVerifier.verify_age_from_array(image_array, did_subject)`: recebe a imagem já decodificada em memória (nunca em disco), roda `DeepFace.analyze(actions=["age"], detector_backend="opencv")`, e imediatamente descarta a referência à imagem (`finally: image_array = None`) antes de retornar o `AgeClaim`.
- O detector configurado é `"opencv"` buscando velocidade e menor uso de memória.

### `biometric_worker.py` - Processo Isolado

Script standalone, **não importado** pelo `app.py` o qual é invocado via `subprocess.run([sys.executable, "biometric_worker.py", did_user], ...)`.

**Contrato de entrada/saída:**
- **Entrada:** bytes da imagem (JPEG/PNG) capturada pelo `st.camera_input`, codificados em base64, enviados via **stdin** (nunca gravados em arquivo).
- **Saída:** uma única linha JSON em **stdout**: `{"ok": true, "claim": {...}}` ou `{"ok": false, "error": "..."}`.

O processo importa `biometric_verifier`, roda a inferência, imprime o resultado e termina devolvendo ao sistema operacional toda a memória alocada por TensorFlow/Keras/DeepFace. O processo pai (`app.py`) só lê o stdout; nunca importa `DeepFace` diretamente.

### `rag_chain.py` - RAG e Trava de Consentimento

Classe `SecureRAG`, responsável por: ingestão de documentos, indexação vetorial, recuperação híbrida de contexto e geração da resposta após validar o consentimento.

**Ingestão (`ingest_documents`)**
1. Carrega `.txt` (`TextLoader`) e `.pdf` (`PyPDFLoader`) de `data/documentos/`.
2. Divide em chunks com `RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)`.
3. Gera embeddings com `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (multilíngue, roda em CPU ou GPU via `model_kwargs={"device": "cuda"}`).
4. Persiste no ChromaDB local (`data/chroma_db/`). Se o banco já tiver documentos, a ingestão é pulada (idempotência).

**Trava de consentimento (`_verify_consent`)** - executada **antes** de qualquer acesso ao banco vetorial:
1. Assinatura precisa estar presente.
2. `consent_payload["allow_rag"]` precisa ser `True`.
3. Se houver `expires_at`, o consentimento não pode estar expirado (checagem de fuso horário normalizada para UTC). Payloads sem `expires_at` são aceitos por retrocompatibilidade (ex.: chamadas diretas em scripts de teste), mas isso é logado como aviso.
4. `CryptoDID.verify_signature()` precisa retornar `True` - validação criptográfica real, não apenas "campo preenchido".

Só depois de passar pelas quatro checagens é que `query_with_consent` monta os retrievers e consulta o LLM.

**Recuperação híbrida (retrieval):**
```python
vector_retriever = self.vector_store.as_retriever(
    search_type="mmr", search_kwargs={"k": 5, "fetch_k": 20}
)
bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 5

hybrid_retriever = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever], weights=[0.6, 0.4]
)
```
- **MMR (Maximal Marginal Relevance)** sobre o índice vetorial: prioriza chunks relevantes e diversos entre si (evita redundância).
- **BM25**: busca lexical clássica (TF-IDF ponderado), mais forte para nomes próprios, números e termos exatos que o embedding semântico pode não captar bem.
- `EnsembleRetriever` combina as duas listas de resultados por *rank fusion* ponderado (60% vetorial / 40% léxico).

**Geração:** `ChatOllama(model="llama3", num_ctx=8192, temperature=0.1, num_predict=512)` - ver `docs/otimizacoes-e-aprendizados.md` para o porquê de cada parâmetro. O prompt instrui o modelo a responder **estritamente** com base no contexto recuperado, reduzindo alucinação.

### `app.py` - Orquestração e Interface (Streamlit)

Não contém lógica de negócio própria - orquestra os três módulos acima através da interface:

1. **Sidebar - Identidade:** oferece "Carregar identidade salva" (se existir keystore) ou "Gerar nova identidade" (com senha opcional para persistência).
2. **Sidebar - Verificação etária:** captura via `st.camera_input`, delega ao `biometric_worker.py` via `subprocess`, e armazena o `AgeClaim` resultante em `st.session_state.age_claim`.
3. **Sidebar - Consentimento:** toggle `allow_rag` + botão de renovação manual; assina um novo `consent_payload` (com `issued_at`/`expires_at`) apenas quando o valor do toggle muda ou o usuário clica em "renovar" - não a cada rerun do Streamlit - e guarda o payload assinado em `st.session_state.consent_payload` para reuso exato em todo o restante da sessão.
4. **Sidebar - Exportação:** monta a credencial `.json` alinhada ao modelo de VC do W3C e oferece download.
5. **Corpo principal - Chat:** só é liberado se houver identidade **e** `age_claim`; cada pergunta reutiliza o `consent_payload` já assinado e chama `rag_system.query_with_consent(...)`.

**Importante:** `consent_payload` é assinado **uma única vez por mudança de estado** e reaproveitado (via `st.session_state`) em vez de reconstruído a cada rerun - porque a inclusão de timestamps (`issued_at`/`expires_at`) faz com que dois dicts "logicamente iguais" construídos em momentos diferentes tenham conteúdo diferente, e portanto produzam assinaturas que não batem entre si na verificação.

---

## Modelo de Ameaças (resumo)

| Ameaça                                                                                  | Mitigação atual                                                                             | Limitação conhecida                                                                                                    |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Vazamento de imagem biométrica                                                          | Imagem só existe em memória do processo filho, nunca gravada em disco                       | Nenhuma proteção contra captura de memória do processo em nível de SO (fora do escopo de uma PoC local)                |
| Replay de consentimento assinado (reenviar uma assinatura antiga capturada em log/rede) | `expires_at` limita a janela de validade a 15 min                                           | Payloads sem `expires_at` (retrocompatibilidade) não expiram                                                           |
| Roubo do keystore em disco                                                              | Chave privada sempre criptografada com senha (PBKDF2 480k iterações + Fernet)               | Sem senha forte, o keystore ainda é vulnerável a ataque de força bruta offline                                         |
| Adulteração do termo de consentimento                                                   | Verificação criptográfica real (`verify_signature`), não apenas checagem de presença        | -                                                                                                                      |
| Alucinação/resposta fora do contexto                                                    | `num_ctx=8192` evita truncamento silencioso; `temperature=0.1`; prompt restrito ao contexto | Modelo local ainda pode alucinar; não há citação de fonte por chunk                                                    |
| Autoridade emissora da credencial                                                       | Credencial é autoemitida (`issuer = did_user`) - coerente com autossoberania                | Nenhum terceiro confiável atesta a veracidade da alegação etária (ver `docs/avaliacao-ssi.md`, propriedade *Provable*) |

---

## Dependências Externas

| Componente                | Papel                                                          | Observação                                                                                                     |
| ------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Ollama**                | Serve o LLM (`llama3`) localmente via HTTP (`localhost:11434`) | Requer instalação separada; único componente do sistema com IPC via rede (mas 100% local, sem sair da máquina) |
| **ChromaDB**              | Banco vetorial, persistido em disco (`data/chroma_db/`)        | Embeddings calculados localmente, sem chamadas externas                                                        |
| **DeepFace / TensorFlow** | Inferência de idade a partir da imagem                         | Só carregado no subprocesso `biometric_worker.py`                                                              |
| **sentence-transformers** | Geração dos embeddings dos documentos e das queries            | Modelo multilíngue, roda em CPU por padrão (GPU opcional)                                                      |
