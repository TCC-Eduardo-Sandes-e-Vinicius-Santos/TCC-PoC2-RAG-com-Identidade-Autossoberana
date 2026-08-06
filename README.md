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

O processo está dividido em 4 etapas lineares:

1. **Captura e Validação Etária (`DeepFace`):** A câmera local captura a imagem do usuário, o modelo de Visão Computacional infere a faixa etária e a imagem é imediatamente descartada da memória.
2. **Geração de DID e Assinatura (`cryptography`):** É gerado o par de chaves (pública e privada) na máquina do usuário, criando o DID local e gerando um arquivo de consentimento assinado digitalmente.
3. **Processamento RAG e Trava Lógica (`LangChain` + `ChromaDB` + `Ollama`):** O banco de dados vetorial carrega o documento de texto local. A rotina de busca de contexto (*retrieval*) do LLM executa uma verificação da assinatura do consentimento antes de liberar as informações para a resposta do modelo.
4. **Exportação Estruturada (`JSON`):** O usuário pode exportar um arquivo `.json` interoperável contendo sua credencial, seu DID e o histórico de permissões concedidas.

---

## Documentação

- Item

---

## Estrutura de Diretórios

O repositório segue a seguinte estrutura:

```text
root/
│
├── .github/
│   └── workflows/              # Workflow de verificação do repositório
│
├── data/
│   ├── documentos/             # Documentos locais (.txt) para ingestão no RAG
│   └── export/                 # Pasta de destino das identidades exportadas em .json
│
├── docs/
│   └── dicionario-requisitos.md# Detalhamento do mapeamento do SIG e DIDs
│
├── src/
│   ├── app.py                  # Aplicação principal e interface visual em Streamlit
│   ├── biometric_verifier.py   # Módulo de visão computacional (DeepFace/OpenCV)
│   ├── crypto_did.py           # Módulo criptográfico (geração de DIDs e assinaturas)
│   └── rag_chain.py            # Módulo do RAG, ChromaDB e integração com Ollama
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

2. Instale e baixe o modelo local no Ollama (ex: Llama 3 ou Phi-3):

```bash
ollama run llama3

```

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

1. Execute o módulo de validação biométrica:

```bash
python3 src/biometric_verifier.py

```

2. Execute o módulo de geração de DIDs e assinaturas:

```bash
python3 src/crypto_did.py

```