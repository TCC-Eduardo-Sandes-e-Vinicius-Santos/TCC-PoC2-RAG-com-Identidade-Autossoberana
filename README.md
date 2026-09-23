# TCC-PoC2 RAG com Identidade Autossoberana

| Aluno                             | Matrícula |
| --------------------------------- | --------- |
| Eduardo Matheus dos Santos Sandes | 221008024 |
| Vinícius de Oliveira Santos       | 202017263 |

Esta Prova de Conceito (PoC) tem como objetivo demonstrar a aplicação do *softgoal* **Identidade Autossoberana**, através das técnicas: **Geração Local de DIDs**, **Verificação Biométrica Etária opaca**, **Assinatura Criptográfica de Consentimento** e **Desbloqueio Condicional de RAG (Retrieval-Augmented Generation)**. A PoC avalia a viabilidade de um assistente pessoal baseado em Inteligência Artificial Generativa (LLM local) operando 100% em ambiente local (*edge computing*), no qual a recuperação de informações privadas em um banco vetorial é estritamente condicionada à validação do consentimento assinado digitalmente pelo titular dos dados.

## Objetivos da PoC

1. **Validação Biométrica e Emissão de Credencial Etária:** Processar imagens faciais localmente via Visão Computacional (`DeepFace`), extraindo a alegação "maior de idade" sem expor ou armazenar biometria sensível.
2. **Consentimento Criptográfico e Trava Lógica de Acesso ao RAG:** Implementar o par de chaves assimétricas do DID para assinar o termo de permissão, utilizando a assinatura digital como "chave de acesso" lógica ao banco vetorial (`ChromaDB`) consultado pelo LLM local (`Ollama`).
3. **Interoperabilidade e Portabilidade da Identidade:** Formatar e disponibilizar para download uma ficha de identidade estruturada em formato `JSON` (padrão *Verifiable Credentials*), contendo o DID do usuário, as permissões concedidas e a alegação de maioridade assinada.

## Arquitetura e Fluxo de Dados

O processo está dividido em 5 etapas lineares (ver [`docs/arquitetura.md`](docs/arquitetura.md) para o detalhamento técnico completo, com diagramas):

1. **Geração ou Restauração de DID (`cryptography`):** Na primeira execução, é gerado um par de chaves Ed25519 localmente, criando o DID do usuário; opcionalmente, a chave privada pode ser salva em um keystore local criptografado (PBKDF2 + Fernet) protegido por senha, para reuso em sessões futuras.
2. **Captura e Validação Etária em Processo Isolado (`DeepFace`):** A câmera local captura a imagem do usuário; a inferência de idade roda em um **subprocesso dedicado** (`biometric_worker.py`), que carrega o TensorFlow/DeepFace, retorna apenas a alegação booleana com a idade estimada, e é encerrado liberando toda a memória do TensorFlow antes de o usuário começar a conversar com o RAG. A imagem em si nunca é persistida em disco.
3. **Assinatura de Consentimento com Expiração:** O termo de consentimento (`allow_rag`, `did`, `issued_at`, `expires_at`) é assinado digitalmente com a chave privada do usuário. O consentimento tem validade de 15 minutos por padrão, mitigando reuso indevido (*replay*) de uma assinatura antiga.
4. **Processamento RAG e Trava Lógica (`LangChain` + `ChromaDB` + `Ollama`):** O banco de dados vetorial local é consultado por uma **busca híbrida** (vetorial + BM25) apenas após a rotina `_verify_consent` validar criptograficamente a assinatura, a autorização e a validade temporal do consentimento.
5. **Exportação Estruturada (`JSON`):** O usuário pode exportar uma credencial `.json` alinhada ao modelo de dados de *Verifiable Credentials* do W3C, contendo seu DID, a alegação etária e o histórico de permissões concedidas.

---

## Documentação

- [`docs/arquitetura.md`](docs/arquitetura.md): detalhamento técnico da arquitetura, dos módulos e do fluxo de dados (com diagramas).
- [`docs/otimizacoes-e-aprendizados.md`](docs/otimizacoes-e-aprendizados.md): problemas de precisão, performance e usabilidade enfrentados durante o desenvolvimento, e como foram resolvidos.
- [`docs/historias-de-usuario.md`](docs/historias-de-usuario.md): histórias de usuário (US01-US07) que orientaram os requisitos da PoC.

---

## Estrutura de Diretórios

O repositório segue a seguinte estrutura:

```text
root/
│
├── data/
│   ├── documentos/             # Documentos locais (.txt/.pdf) para ingestão no RAG
│   ├── chroma_db/               # Banco vetorial persistido (ChromaDB, git-ignorado)
│   └── keystore/                 # Keystore criptografado da identidade (git-ignorado)
│
├── docs/
│   ├── historias-de-usuario.md
│   ├── arquitetura.md              # Detalhamento técnico da arquitetura
│   └── otimizacoes-e-aprendizados.md  # Histórico de problemas e soluções
│
├── src/
│   ├── app.py                  # Aplicação principal e interface visual em Streamlit
│   ├── biometric_verifier.py   # Módulo de visão computacional (DeepFace/OpenCV)
│   ├── biometric_worker.py     # Processo isolado que executa a verificação etária
│   ├── crypto_did.py           # Módulo criptográfico (DIDs, assinaturas, keystore)
│   ├── rag_chain.py            # Módulo do RAG, ChromaDB e integração com Ollama
│   └── test/                   # Scripts de teste manual por módulo
│
├── requirements.txt            # Dependências do projeto em Python
└── README.md

```

---

## Como Executar

### Opção 1: Rodando a Aplicação Completa via Streamlit (com Ollama)

1. **Pré-requisitos:** Certifique-se de ter o Python 3.8+ e o **Ollama** instalados no computador.

```bash
# Verificar a versão do Python
python3 --version

```

2. Instale e baixe o modelo local no Ollama:

```bash
ollama pull llama3

```

> A aplicação usa `num_ctx=8192` ao chamar o modelo (ver `docs/otimizacoes-e-aprendizados.md`). Se sua máquina tiver pouca RAM/VRAM, considere um modelo menor (ex.: `llama3.2:3b`) trocando o parâmetro `model` em `rag_chain.py`.

3. Clone este repositório e navegue até a pasta do projeto:

```bash
git clone [https://github.com/TCC-Eduardo-Sandes-e-Vinicius-Santos/TCC-PoC2-RAG-com-Identidade-Autossoberana](https://github.com/TCC-Eduardo-Sandes-e-Vinicius-Santos/TCC-PoC2-RAG-com-Identidade-Autossoberana)

cd TCC-PoC2-RAG-com-Identidade-Autossoberana

```

4. Abra o terminal na raiz do projeto e crie um ambiente virtual (recomendado):

```bash
python3 -m venv venv

# Para ativar no Windows:
venv\Scripts\activate
# Para ativar no Linux/Mac:
source venv/bin/activate

```

5. Instale as dependências executando:

```bash
pip install -r requirements.txt

```

6. Inicie a aplicação Streamlit:

```bash
streamlit run src/app.py

```

7. Acesse o endereço exibido no terminal (ex: `http://localhost:8501`) no seu navegador.

### Opção 2: Executando Módulos em Terminal (Modo Desenvolvimento)

Caso queira testar a execução isolada de cada etapa da solução sem a interface gráfica:

```bash
# Módulo de geração de DIDs, assinaturas e keystore
python3 src/test/test_crypto_did.py

# Módulo de validação biométrica
python3 src/test/test_biometric_verifier.py

# Módulo do RAG (ingestão + query)
python3 src/test/test_rag_chain.py

```
