# Otimizações e Aprendizados

## Introdução

<div align="justify">&emsp;&emsp;
Este documento registra, para fins de honestidade acadêmica e de referência técnica, os problemas reais enfrentados ao longo do desenvolvimento da PoC relativos a precisão, performance e usabilidade, o diagnóstico de cada um, e as mudanças efetivamente aplicadas para resolvê-los. A ordem de prioridade seguida foi: <strong>1) Precisão</strong>, <strong>2) Performance</strong>, <strong>3) Usabilidade</strong>, já que uma resposta rápida porém errada é pior do que nenhuma resposta, e um sistema que só é útil se o usuário tolerar o consumo de memória ainda depende, antes de tudo, de estar certo.
</div>

## Sintoma inicial

Antes das mudanças, para perguntas simples a PoC apresentava:
- **Precisão:** respostas erradas ou alucinadas, mesmo com o conteúdo relevante presente na base.
- **Performance:** ~10 minutos para responder.
- **Usabilidade:** consumo de memória excessivo ao rodar localmente.

---

## 1. Precisão

### Diagnóstico

A configuração original combinava:

```python
retriever = self.vector_store.as_retriever(
    search_type="mmr", search_kwargs={"k": 30, "fetch_k": 150}
)
```
com `chunk_size=6000` (chunks de ~6000 caracteres) e:
```python
self.llm = ChatOllama(model="llama3")
```

**O problema central: `num_ctx` não estava definido.** O Ollama usa, por padrão, uma janela de contexto de **2048 tokens** para o `llama3`, independentemente de o modelo suportar mais. O código estava montando um prompt com até **30 chunks × 6000 caracteres** (dezenas de milhares de tokens) e enviando para um modelo configurado para enxergar só os últimos ~2048 tokens da entrada. Na prática:

- A maior parte do contexto recuperado era **descartada silenciosamente**.
- Dependendo de como o backend trunca a entrada, a própria **pergunta podia ser cortada** (ela vinha ao final do prompt).
- O modelo "inventava" respostas porque estava recebendo contexto parcial/quebrado no meio de uma frase.

Um segundo fator agravante: a versão em produção usava **apenas busca vetorial (MMR)**, sem o `EnsembleRetriever` (BM25 + vetorial). Isso prejudicava perguntas com nomes próprios, números e termos exatos onde busca lexical supera busca semântica pura.

### Correção aplicada

```python
self.llm = ChatOllama(model="llama3", num_ctx=8192, temperature=0.1, num_predict=512)
```
```python
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
```
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

**Racional de cada mudança:**
- `num_ctx=8192`: garante que o contexto recuperado (agora dimensionado para caber com folga) chegue inteiro ao modelo, sem truncamento silencioso.
- `chunk_size=1200` (chunks bem menores que 6000): embeddings de blocos muito longos ficam "diluídos" menos discriminativos na busca por similaridade. Chunks menores tendem a produzir recuperação mais precisa.
- `k=5, fetch_k=20` (era `k=30, fetch_k=150`): proporcional ao que o modelo realmente processa; recuperar 30 chunks de 6000 caracteres nunca fazia sentido com uma janela de contexto de 2048-8192 tokens.
- `temperature=0.1`: reduz a aleatoriedade da geração, importante para tarefas factuais baseadas em contexto (o padrão do Ollama gira em torno de 0.8, adequado para criatividade, não para QA).
- Busca híbrida (BM25 + vetorial): cobre o ponto cego da busca puramente semântica para termos exatos.

---

## 2. Performance

### Diagnóstico

A maior parte da lentidão (10 minutos por pergunta) era consequência direta do problema de precisão acima: o sistema processava dezenas de milhares de tokens de contexto por pergunta simples, muito além do necessário e descartava boa parte desse processamento.

### Correção aplicada

- As mudanças de `num_ctx`/`k`/`chunk_size` da seção anterior já reduzem drasticamente o volume de tokens processados por consulta. Logo, a correção de precisão já é, em grande parte, a correção de performance.
- `num_predict=512`: limita o tamanho da resposta gerada, evitando gerações desnecessariamente longas.
- `HuggingFaceEmbeddings` foi documentado para uso opcional em GPU:
  ```python
  self.embedding_model = HuggingFaceEmbeddings(
      model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
      # model_kwargs={"device": "cuda"},  # descomente se houver GPU NVIDIA disponível
  )
  ```
  Acelera tanto a ingestão quanto a query em máquinas com GPU disponível, mantendo compatibilidade com CPU por padrão.
- `print()`s de debug (dump do conteúdo de cada chunk recuperado) permanecem no código como ferramenta de depuração, mas devem ser removidos ou reduzidos a nível `logger.debug` antes de qualquer avaliação de desempenho "limpa", já que I/O de console tem custo não desprezível quando repetido a cada chunk.

---

## 3. Usabilidade / consumo de memória

### Diagnóstico

O aplicativo carregava, simultaneamente, três *runtimes* pesados de ML no mesmo processo:
- **TensorFlow** (via `DeepFace`/RetinaFace, para a verificação biométrica);
- **PyTorch** (via `sentence-transformers`, para os embeddings);
- o processo do **Ollama** (para o LLM).

Além disso, `detector_backend="retinaface"` (usado numa versão anterior) é o detector mais preciso, porém também o mais pesado entre as opções do `DeepFace`, agravando o consumo de memória durante a etapa de verificação etária.

Também foi identificado que as variáveis `os.environ["USE_TF"] = "0"` / `os.environ["USE_TORCH"] = "1"` presentes no `app.py` **não tinham efeito real sobre o `DeepFace`**. Tais variáveis são específicas da biblioteca `transformers` da HuggingFace, e o `DeepFace` sempre depende de TensorFlow/Keras internamente, independentemente delas.

### Correção aplicada

1. **Troca do detector biométrico** de `"retinaface"` para `"opencv"` - mais leve, ao custo de robustez de detecção em condições de imagem mais difíceis (iluminação ruim, ângulos extremos). Trade-off aceitável para uma PoC.
2. **Isolamento da etapa biométrica em subprocesso** (`biometric_worker.py`): como a verificação de idade ocorre apenas uma vez por sessão, mas antes rodava dentro do mesmo processo do Streamlit mantendo TensorFlow residente na memória durante toda a sessão de chat, mesmo sem uso - a inferência foi movida para um **processo filho** dedicado:
   - `app.py` envia a imagem capturada (bytes, codificados em base64) via **stdin** para `biometric_worker.py`, chamado com `subprocess.run(...)`.
   - O processo filho carrega `DeepFace`, executa a inferência, imprime o resultado em JSON no **stdout** e termina.
   - Ao terminar o processo filho, o sistema operacional libera **toda** a memória associada ao TensorFlow e o processo principal do Streamlit nunca chega a importar `DeepFace` diretamente.
   - A imagem continua nunca sendo persistida em disco: o `stdin` mantém o dado só em memória, tanto no processo pai quanto no filho.
3. As variáveis de ambiente `USE_TF`/`USE_TORCH` foram mantidas no código (não removidas, para não gerar um diff maior que o necessário), mas o comportamento real de isolamento de memória agora vem do ponto (2) acima, não delas.

### Trade-offs registrados (não implementados nesta iteração, mas documentados como trabalho futuro)

- Reduzir ainda mais o footprint trocando o `llama3` (8B) por um modelo menor (`llama3.2:3b`).
- Investigar builds de `DeepFace`/TensorFlow mais leves (ex.: TFLite) para o subprocesso biométrico, já que ele é chamado apenas uma vez por sessão e domina o pico de memória do fluxo de onboarding.

---

## Resumo das mudanças por arquivo

| Arquivo                        | Mudanças                                                                                                                                                                                                                                                                           |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rag_chain.py`                 | `num_ctx`, `temperature`, `num_predict` no `ChatOllama`; `chunk_size`/`chunk_overlap` reduzidos; `k`/`fetch_k` reduzidos; busca híbrida (BM25 + MMR) reativada; `device="cuda"` documentado (comentado) nos embeddings; checagem de expiração de consentimento (`_verify_consent`) |
| `biometric_verifier.py`        | `detector_backend` padrão trocado para `"opencv"`                                                                                                                                                                                                                                  |
| `biometric_worker.py` *(novo)* | Processo isolado para a inferência biométrica, comunicação via stdin/stdout, nunca persiste imagem em disco                                                                                                                                                                        |
| `app.py`                       | Chamada à verificação biométrica via `subprocess` em vez de import direto; reuso do `consent_payload` assinado via `session_state` (evita reconstrução divergente); UI de renovação de consentimento                                                                               |
| `crypto_did.py`                | Keystore local criptografado (`save_keystore`/`load_keystore`) para persistência real da identidade entre sessões                                                                                                                                                                  |
