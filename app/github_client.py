import os

import httpx
from dotenv import load_dotenv


load_dotenv()


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise RuntimeError(
        "GITHUB_TOKEN não foi configurado."
    )


BASE_URL = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2026-03-10",
    "User-Agent": "code-review-assistant",
}


async def buscar_pull_request(
    repo_full_name: str,
    pr_number: int
) -> dict:

    url = (
        f"{BASE_URL}/repos/"
        f"{repo_full_name}/pulls/{pr_number}"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=HEADERS
        )

    response.raise_for_status()

    return response.json()


async def buscar_diff(
    repo_full_name: str,
    pr_number: int
) -> str:

    url = (
        f"{BASE_URL}/repos/"
        f"{repo_full_name}/pulls/{pr_number}"
    )

    diff_headers = {
        **HEADERS,
        "Accept": "application/vnd.github.diff",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=diff_headers
        )

    response.raise_for_status()

    return response.text


async def comentar_pull_request(
    repo_full_name: str,
    pr_number: int,
    body: str,
) -> dict:

    url = (
        f"{BASE_URL}/repos/"
        f"{repo_full_name}/issues/"
        f"{pr_number}/comments"
    )

    payload = {
        "body": body,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=HEADERS,
            json=payload,
        )

    response.raise_for_status()

    return response.json()


async def buscar_comentarios_pull_request(
    repo_full_name: str,
    pr_number: int,
) -> list[dict]:
    """
    Retorna todos os comentários de uma Pull Request.

    Utilizado para verificar se um comentário com o marker
    de idempotência já existe antes de criar um novo.
    """
    url = (
        f"{BASE_URL}/repos/"
        f"{repo_full_name}/issues/"
        f"{pr_number}/comments"
    )

    params = {
        "per_page": 100,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=HEADERS,
            params=params,
        )

    response.raise_for_status()

    return response.json()