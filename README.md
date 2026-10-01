# Code Review Assistant com IA

Sistema que acompanha Pull Requests do GitHub, analisa as alterações de código usando um modelo de linguagem local e publica automaticamente uma revisão como comentário na PR.

## Sobre o projeto

O Code Review Assistant recebe eventos de Pull Request via webhook do GitHub, busca o diff das alterações, envia o código para um modelo de linguagem local (Ollama/Qwen) e publica o resultado como comentário na PR. As análises são persistidas no Supabase e ficam acessíveis por um dashboard em React.

O projeto foi desenvolvido com foco em arquitetura robusta: processamento determinístico do diff, validação estrutural da resposta do LLM, idempotência no processamento e prevenção de comentários duplicados.

## Arquitetura

```
GitHub
   ↓
Webhook
   ↓
FastAPI
   ↓
GitHub API
   ↓
Diff Parser
   ↓
Ollama / Qwen
   ↓
Pydantic
   ↓
Supabase
   ↓
GitHub Comment
   ↓
React Dashboard
```

## Tecnologias

**Backend**
- Python 3.12+
- FastAPI
- httpx
- Pydantic
- supabase-py

**Modelo de linguagem**
- Ollama
- Qwen 2.5 Coder 7B

**Banco de dados**
- Supabase (PostgreSQL)

**Frontend**
- React 19
- Vite

## Como funciona

1. Um evento `pull_request` chega via webhook do GitHub.
2. A assinatura HMAC-SHA256 é validada.
3. O processamento é delegado para uma background task.
4. O sistema verifica se aquele PR + SHA já foi analisado (idempotência).
5. O diff é buscado na GitHub API.
6. Comentários são removidos e strings são mascaradas antes de enviar ao LLM.
7. O diff formatado é enviado ao Ollama/Qwen com structured output via Pydantic.
8. A localização dos problemas (arquivo e linha) é determinada deterministicamente pelo diff parser, não pelo LLM.
9. O resultado é salvo no Supabase.
10. Um comentário em Markdown é publicado na PR, com um marker HTML invisível para controle de idempotência.
11. O dashboard em React consome a API do backend para exibir o histórico de análises.

## Estrutura do projeto

```
code-review-assistant/
│
├── app/
│   ├── db.py                    # Persistência no Supabase
│   ├── diff_parser.py           # Parser determinístico do diff
│   ├── github_client.py         # Comunicação com a GitHub API
│   ├── llm_client.py            # Ollama/Qwen e validação da resposta
│   ├── main.py                  # FastAPI, webhook, endpoints da API
│   ├── review_formatter.py      # Conversão da análise para Markdown
│   ├── review_service.py        # Orquestração do pipeline
│   │
│   ├── test_diff_parser.py
│   ├── test_github.py
│   ├── test_github_comment.py
│   ├── test_llm.py
│   └── test_retry_idempotency.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   ├── public/
│   └── package.json
│
├── .env
├── .env.example
├── .gitignore
└── README.md
```

## Configuração

Copie o arquivo de exemplo e preencha as variáveis:

```bash
cp .env.example .env
```

```env
GITHUB_WEBHOOK_SECRET=   # segredo configurado no webhook do GitHub
GITHUB_TOKEN=            # Personal Access Token com permissão Pull requests: Read and write
SUPABASE_URL=            # URL do projeto no Supabase
SUPABASE_SECRET_KEY=     # chave de serviço (service role key)
```

O banco de dados requer duas tabelas no Supabase:

**`pull_requests`** — com constraint `unique (repo_full_name, pr_number)`

**`analises`** — com constraint `unique (pr_id, head_sha)` e campos:
`id`, `pr_id`, `head_sha`, `resumo`, `problemas`, `nota_geral`, `status`, `criado_em`, `github_comment_id`, `github_comment_url`, `comentario_status`, `comentario_erro`

## Como executar

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

O servidor sobe em `http://localhost:8000`.

### Ollama

```bash
ollama pull qwen2.5-coder:7b
ollama serve
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

O dashboard abre em `http://localhost:5173`.

## Configuração do GitHub Webhook

1. No repositório do GitHub, acesse **Settings → Webhooks → Add webhook**.
2. Configure:
   - **Payload URL:** URL pública do servidor (ex: via ngrok em desenvolvimento)
   - **Content type:** `application/json`
   - **Secret:** o mesmo valor de `GITHUB_WEBHOOK_SECRET`
   - **Events:** selecione `Pull requests`
3. Em desenvolvimento, use ngrok para expor o servidor local:

```bash
ngrok http 8000
```

## Testes

Os testes unitários de idempotência e retry não dependem de serviços externos — GitHub API, Ollama e Supabase são mockados:

```bash
source .venv/bin/activate
python -m unittest app.test_retry_idempotency -v
```

Os demais arquivos de teste (`test_github.py`, `test_llm.py`, `test_github_comment.py`) requerem serviços reais e são usados para validação manual do ambiente.

## Limitações conhecidas

A análise é realizada por um modelo de linguagem local e pode produzir falsos positivos ou falsos negativos. O sistema utiliza processamento determinístico do diff e validação estrutural da resposta para reduzir a dependência do modelo em informações como arquivo e linha.

A proteção contra prompt injection também é uma camada de mitigação, não uma garantia de segurança absoluta.

## Roadmap / trabalhos futuros

- Comentários inline na PR (por arquivo e linha)
- Feedback humano nas sugestões (👍 / 👎)
- Métricas por categoria e severidade no dashboard
- Histórico visual de evolução do score por commit
- Observabilidade (tempo de processamento por etapa)
- Testes de integração automatizados
- Deploy em ambiente de produção
- Avaliação quantitativa do modelo (precision, recall, falsos positivos)
- Suporte a múltiplos repositórios e usuários
- Migração de Personal Access Token para GitHub App