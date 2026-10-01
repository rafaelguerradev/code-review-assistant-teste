# Code Review Assistant com IA

Sistema de revisão automática de Pull Requests do GitHub utilizando um modelo de linguagem local. O projeto recebe eventos via webhook, obtém o diff da Pull Request, estrutura as alterações, analisa o código com Ollama/Qwen, armazena o resultado no Supabase/PostgreSQL e publica automaticamente uma revisão como comentário na Pull Request.

O projeto também possui uma API REST para histórico e métricas e um dashboard em React para acompanhamento dos resultados.

---

## O que pode ser avaliado sem serviços externos

Dois grupos de testes funcionam com apenas Python e as dependências do `requirements.txt`, sem precisar de GitHub, Ollama, Supabase ou ngrok:

**Diff Parser** — processa e estrutura diffs de Pull Requests:

```bash
python3 -m app.test_diff_parser
```

**Retry e Idempotência** — lógica de estados, prevenção de duplicatas, retry após falhas. Todos os serviços externos são mockados:

```bash
python3 -m unittest app.test_retry_idempotency -v
```

Os demais testes (`test_llm`, `test_github`, `test_github_comment`) exigem serviços reais e são para validação do ambiente completo.

---

## 1. Visão geral

Fluxo principal:

```text
GitHub Pull Request
        │
        │ Webhook
        ▼
     FastAPI
        │
        ├── valida assinatura HMAC-SHA256
        │
        └── inicia processamento em background
                     │
                     ▼
                GitHub API
                     │
                     ▼
                    Diff
                     │
                     ▼
                Diff Parser
                     │
                     ▼
              Ollama + Qwen
                     │
                     ▼
          Structured Output / Pydantic
                     │
                     ▼
              Supabase / PostgreSQL
                     │
                     ▼
             Comentário na PR
                     │
                     ▼
              React Dashboard
```

---

## 2. Principais funcionalidades

- Recebimento de Pull Requests por webhook do GitHub
- Validação HMAC-SHA256 do webhook
- Processamento em background
- Consulta de Pull Requests pela GitHub API
- Obtenção e parsing determinístico do diff
- Identificação determinística de arquivo e linha das evidências
- Análise de código com Qwen 2.5 Coder 7B
- Execução local do modelo através do Ollama
- Structured output validado com Pydantic
- Persistência de Pull Requests e análises no PostgreSQL/Supabase
- Histórico de análises por Pull Request e `head_sha`
- Idempotência para evitar análises duplicadas
- Retry após falhas parciais
- Detecção de comentários já existentes por marker
- Publicação automática de comentário em Markdown no GitHub
- API REST de histórico e métricas
- Dashboard em React

---

## 3. Tecnologias

### Backend

- Python 3.12+
- FastAPI
- Uvicorn
- HTTPX
- Pydantic
- python-dotenv
- supabase-py

### Inteligência Artificial

- Ollama
- Qwen 2.5 Coder 7B

### Banco de dados

- Supabase
- PostgreSQL

### Frontend

- React
- Vite
- Node.js / npm

### Integração

- GitHub Webhooks
- GitHub REST API
- HMAC-SHA256

---

## 4. Dependências externas

O projeto integra serviços reais. Para execução completa são necessários:

| Dependência | Para que serve | Obrigatório para os testes automáticos |
|---|---|---|
| Python 3.12+ | backend | ✅ sim |
| Node.js / npm | frontend | apenas para o dashboard |
| Ollama + Qwen 2.5 Coder 7B | modelo de IA local | apenas para `test_llm` |
| Supabase (conta gratuita) | banco de dados | apenas para o pipeline completo |
| GitHub + Personal Access Token | integração com PRs | apenas para `test_github` |
| ngrok (ou similar) | túnel público para o webhook durante testes locais | apenas para acionar o webhook via GitHub |

Os testes `test_diff_parser` e `test_retry_idempotency` funcionam sem nenhum desses serviços.

---

## 5. Instalação

### 5.1 Obter o projeto

```bash
cd code-review-assistant
```

### 5.2 Criar o ambiente Python

```bash
python3 -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instalar as dependências:

```bash
python3 -m pip install -r requirements.txt
```

### 5.3 Instalar as dependências do frontend

```bash
cd frontend
npm install
cd ..
```

---

## 6. Configurar o Supabase

### 6.1 Criar o projeto

Acesse o Supabase e crie um novo projeto PostgreSQL.

### 6.2 Criar as tabelas

Na raiz do projeto existe o arquivo `database.sql`.

No Supabase: **SQL Editor → New query**, cole o conteúdo de `database.sql` e execute.

O script cria as tabelas `pull_requests` e `analises` com suas chaves, constraints e foreign keys.

---

## 7. Configurar as variáveis de ambiente

```bash
cp .env.example .env
```

Preencha o `.env`:

```env
GITHUB_WEBHOOK_SECRET=   # segredo do webhook
GITHUB_TOKEN=            # Personal Access Token (Pull requests: Read and write)
SUPABASE_URL=            # URL do projeto Supabase
SUPABASE_SECRET_KEY=     # service role key do Supabase
```

> Nunca publique o `.env`, tokens ou chaves.

---

## 8. Configurar o GitHub

### Personal Access Token

Caminho: **Settings → Developer Settings → Personal access tokens → Fine-grained tokens**

Permissões mínimas:

```text
Pull requests → Read and write
Contents      → Read-only
Metadata      → Read-only
```

### Webhook

**Settings → Webhooks → Add webhook**

```text
Payload URL:  https://SEU-ENDERECO-PUBLICO/webhook/github
Content type: application/json
Secret:       mesmo valor de GITHUB_WEBHOOK_SECRET
Eventos:      Pull requests
```

Para testes locais, exponha o backend com ngrok:

```bash
ngrok http 8000
```

e use o endereço gerado como Payload URL.

---

## 9. Executar o Ollama

```bash
ollama pull qwen2.5-coder:7b
ollama serve
```

O `requirements.txt` instala o cliente Python `ollama`, mas não instala o programa Ollama nem baixa o modelo.

---

## 10. Executar o backend

```bash
uvicorn app.main:app --reload
```

Disponível em `http://localhost:8000`.
Documentação interativa: `http://localhost:8000/docs`.

### Endpoints

```text
GET  /
POST /webhook/github

GET /pull-requests
GET /pull-requests/{pr_id}
GET /pull-requests/{pr_id}/analyses
GET /stats
```

---

## 11. Executar o frontend

```bash
cd frontend
npm run dev
```

Dashboard em `http://localhost:5173`.

O frontend se comunica com o FastAPI e não acessa o Supabase diretamente.

---

## 12. Testes

### Sem dependências externas

**Diff Parser:**

```bash
source .venv/bin/activate
python3 -m app.test_diff_parser
```

**Retry e Idempotência** (GitHub, Ollama e Supabase são mockados):

```bash
python3 -m unittest app.test_retry_idempotency -v
```

### Com Ollama instalado

```bash
python3 -m app.test_llm
```

### Com GitHub configurado

```bash
python3 -m app.test_github
python3 -m app.test_github_comment
```

---

## 13. Ordem recomendada para uma instalação nova

```bash
cd code-review-assistant
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

1. Executar os testes que não exigem serviços externos:

```bash
python3 -m app.test_diff_parser
python3 -m unittest app.test_retry_idempotency -v
```

2. Criar o projeto no Supabase e executar `database.sql`.
3. Preencher o `.env`.
4. Instalar o Ollama e baixar o modelo:

```bash
ollama pull qwen2.5-coder:7b
```

5. Executar o teste do LLM:

```bash
python3 -m app.test_llm
```

6. Com GitHub configurado:

```bash
python3 -m app.test_github
python3 -m app.test_github_comment
```

7. Iniciar o backend:

```bash
uvicorn app.main:app --reload
```

8. Em outro terminal, iniciar o frontend:

```bash
cd frontend
npm run dev
```

9. Para acionar o webhook via GitHub, iniciar o ngrok:

```bash
ngrok http 8000
```

---

## 14. Estrutura do projeto

```text
code-review-assistant/
│
├── app/
│   ├── __init__.py
│   ├── db.py                    # persistência no Supabase/PostgreSQL
│   ├── diff_parser.py           # parsing determinístico do diff
│   ├── github_client.py         # comunicação com a GitHub API
│   ├── llm_client.py            # Ollama/Qwen e validação da resposta
│   ├── main.py                  # FastAPI, webhook, CORS, rotas
│   ├── review_formatter.py      # conversão da análise para Markdown
│   ├── review_service.py        # orquestração do pipeline
│   │
│   ├── test_diff_parser.py      # testes do parser (sem deps externas)
│   ├── test_retry_idempotency.py# testes de retry/idempotência (sem deps externas)
│   ├── test_llm.py              # requer Ollama
│   ├── test_github.py           # requer GitHub token
│   └── test_github_comment.py   # requer GitHub token e PR real
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── ...
│   ├── public/
│   └── package.json
│
├── database.sql                 # script de criação das tabelas
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 15. Arquitetura de responsabilidades

```text
main.py          → HTTP, webhook, CORS, rotas
github_client.py → comunicação com a GitHub API
diff_parser.py   → parsing e localização determinística do diff
llm_client.py    → Ollama/Qwen e validação da resposta
db.py            → persistência no Supabase/PostgreSQL
review_formatter → conversão da análise para Markdown
review_service.py→ orquestração do pipeline e gerenciamento de estados
frontend/        → dashboard e visualização dos dados
```

---

## 16. Princípios técnicos

**Localização determinística** — arquivo e linha são determinados diretamente do diff, não pelo LLM.

**Structured output** — a resposta da IA é validada com Pydantic antes de persistir.

**Idempotência** — a constraint `unique (pr_id, head_sha)` impede análises duplicadas para a mesma versão da PR.

**Retry granular** — falha na análise e falha no comentário são tratadas separadamente. Um erro no comentário não invalida uma análise já concluída.

**Marker de idempotência** — um marcador HTML invisível é embutido em todo comentário publicado. Se o processo falhar após criar o comentário no GitHub mas antes de salvar o ID no banco, o sistema detecta o comentário existente pelo marker e não cria duplicata.

---

## 17. Limitações conhecidas

O modelo pode produzir falsos positivos, falsos negativos e classificações que precisam de revisão humana. A IA não substitui um code review humano.

O projeto possui uma camada de mitigação contra prompt injection (remoção de comentários, mascaramento de strings, localização determinística), mas não representa uma garantia absoluta.

O processamento utiliza `BackgroundTasks` do FastAPI. Para maior volume, uma arquitetura com filas dedicadas seria mais adequada.

---

## 18. Segurança

Nunca publique `.env`, `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET` ou `SUPABASE_SECRET_KEY`. O repositório contém apenas `.env.example` com placeholders.

Se um token real for exposto acidentalmente, revogue-o imediatamente.

---

## 19. Trabalhos futuros

- Comentários inline por arquivo e linha
- Feedback humano sobre as sugestões
- Métricas detalhadas por categoria e severidade
- Histórico visual de evolução do score por commit
- Observabilidade (tempo de processamento por etapa)
- Testes de integração automatizados
- Deploy em ambiente de produção
- Avaliação quantitativa do modelo (precision, recall, falsos positivos)
- Suporte a múltiplos repositórios e usuários
- Migração de Personal Access Token para GitHub App

---

## 20. Status

```text
✅ GitHub Webhook
✅ Validação HMAC-SHA256
✅ FastAPI + background tasks
✅ GitHub API (diff, comentário, listagem de comentários)
✅ Diff Parser determinístico
✅ Ollama + Qwen 2.5 Coder 7B
✅ Structured Output + Pydantic
✅ Supabase / PostgreSQL
✅ Idempotência (pr_id + head_sha)
✅ Retry granular (análise e comentário independentes)
✅ Marker de idempotência no comentário
✅ API de histórico e métricas
✅ Dashboard React
```