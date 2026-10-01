import asyncio

from app.github_client import buscar_diff


async def main():
    diff = await buscar_diff(
        "rafaelguerradev/plano-de-estudo",
        1
    )

    print(diff)


asyncio.run(main())