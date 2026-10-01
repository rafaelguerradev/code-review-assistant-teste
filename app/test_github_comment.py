import asyncio

from app.github_client import comentar_pull_request


REPO = "rafaelguerradev/plano-de-estudo"
PR_NUMBER = 11


async def main():
    body = """
# 🤖 Teste do AI Code Review

Este é um comentário enviado automaticamente
pela API do projeto.

✅ Comunicação com GitHub funcionando.
"""

    response = await comentar_pull_request(
        REPO,
        PR_NUMBER,
        body,
    )

    print("Comentário criado!")
    print(
        "ID:",
        response["id"],
    )
    print(
        "URL:",
        response["html_url"],
    )


if __name__ == "__main__":
    asyncio.run(main())