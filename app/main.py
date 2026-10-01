import hashlib
import hmac
import json
import os

from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Request,
)
from .db import (
    buscar_pull_request_por_id,
    listar_analises_por_pr,
    listar_pull_requests,
    obter_estatisticas,
)
from .github_client import buscar_diff
from .review_service import processar_pull_request
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

GITHUB_WEBHOOK_SECRET = os.getenv(
    "GITHUB_WEBHOOK_SECRET"
)

if not GITHUB_WEBHOOK_SECRET:
    raise RuntimeError(
        "GITHUB_WEBHOOK_SECRET não foi configurado."
    )


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_github_signature(
    payload: bytes,
    signature: str | None
) -> None:

    if not signature:
        raise HTTPException(
            status_code=403,
            detail="Assinatura ausente."
        )

    expected_signature = (
        "sha256="
        + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()
    )

    if not hmac.compare_digest(
        expected_signature,
        signature
    ):
        raise HTTPException(
            status_code=403,
            detail="Assinatura inválida."
        )


@app.get("/")
async def root():
    return {
        "message": "Code Review Assistant API"
    }


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    body = await request.body()

    # --------------------------------------------
    # Validação da assinatura
    # --------------------------------------------

    signature = request.headers.get(
        "X-Hub-Signature-256"
    )

    if not signature:
        raise HTTPException(
            status_code=401,
            detail="Assinatura ausente.",
        )

    verify_github_signature(
    body,
    signature,
    )

    # --------------------------------------------
    # Identifica o evento
    # --------------------------------------------

    event = request.headers.get(
        "X-GitHub-Event"
    )

    if event != "pull_request":
        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": event,
        }

    payload = await request.json()

    action = payload.get(
        "action"
    )

    # --------------------------------------------
    # Processamento em background
    # --------------------------------------------

    background_tasks.add_task(
        processar_pull_request,
        payload,
    )

    return {
        "status": "accepted",
        "event": event,
        "action": action,
    }


@app.get("/pull-requests")
async def get_pull_requests():
    return listar_pull_requests()


@app.get("/pull-requests/{pr_id}")
async def get_pull_request(
    pr_id: int,
):
    pull_request = buscar_pull_request_por_id(
        pr_id
    )

    if pull_request is None:
        raise HTTPException(
            status_code=404,
            detail="Pull Request não encontrada.",
        )

    return pull_request


@app.get("/pull-requests/{pr_id}/analyses")
async def get_pull_request_analyses(
    pr_id: int,
):
    pull_request = buscar_pull_request_por_id(
        pr_id
    )

    if pull_request is None:
        raise HTTPException(
            status_code=404,
            detail="Pull Request não encontrada.",
        )

    return listar_analises_por_pr(
        pr_id
    )


@app.get("/stats")
async def get_stats():
    return obter_estatisticas()