import os

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")


if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL não foi configurada."
    )

if not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "SUPABASE_SECRET_KEY não foi configurada."
    )


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


def salvar_pull_request(data: dict) -> dict:
    repo_full_name = data["repo_full_name"]
    pr_number = data["pr_number"]

    existing = (
        supabase
        .table("pull_requests")
        .select("id")
        .eq("repo_full_name", repo_full_name)
        .eq("pr_number", pr_number)
        .execute()
    )

    if existing.data:
        pr_id = existing.data[0]["id"]

        response = (
            supabase
            .table("pull_requests")
            .update(data)
            .eq("id", pr_id)
            .select("*")
            .execute()
        )

        return response.data[0]

    response = (
        supabase
        .table("pull_requests")
        .insert(data)
        .select("*")
        .execute()
    )

    return response.data[0]


def buscar_analise(
    pr_id: int,
    head_sha: str,
) -> dict | None:

    response = (
        supabase
        .table("analises")
        .select("*")
        .eq("pr_id", pr_id)
        .eq("head_sha", head_sha)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def criar_analise(
    pr_id: int,
    head_sha: str,
) -> dict:

    response = (
        supabase
        .table("analises")
        .insert({
            "pr_id": pr_id,
            "head_sha": head_sha,
            "status": "processando",
        })
        .select("*")
        .execute()
    )

    return response.data[0]


def finalizar_analise(
    analysis_id: int,
    result,
) -> dict:

    problemas = [
        issue.model_dump(mode="json")
        for issue in result.issues
    ]

    response = (
        supabase
        .table("analises")
        .update({
            "resumo": result.summary,
            "problemas": problemas,
            "nota_geral": result.overall_score,
            "status": "concluida",
        })
        .eq("id", analysis_id)
        .select("*")
        .execute()
    )

    return response.data[0]



def marcar_analise_erro(
    analysis_id: int,
    error: str,
) -> dict:

    response = (
        supabase
        .table("analises")
        .update({
            "status": "erro",
            "erro": error,
        })
        .eq("id", analysis_id)
        .select("*")
        .execute()
    )

    return response.data[0]


def marcar_comentario_publicado(
    analysis_id: int,
    comment_id: int,
    comment_url: str,
) -> dict:

    response = (
        supabase
        .table("analises")
        .update({
            "github_comment_id": comment_id,
            "github_comment_url": comment_url,
            "comentario_status": "publicado",
            "comentario_erro": None,
        })
        .eq("id", analysis_id)
        .select("*")
        .execute()
    )

    return response.data[0]


def marcar_comentario_erro(
    analysis_id: int,
    error: str,
) -> dict:

    response = (
        supabase
        .table("analises")
        .update({
            "comentario_status": "erro",
            "comentario_erro": error,
        })
        .eq("id", analysis_id)
        .select("*")
        .execute()
    )

    return response.data[0]


def salvar_analise(data: dict):
    response = (
        supabase
        .table("analises")
        .insert(data)
        .select("*")
        .execute()
    )

    return response.data


def listar_pull_requests() -> list[dict]:
    response = (
        supabase
        .table("pull_requests")
        .select("*")
        .order("atualizado_em", desc=True)
        .execute()
    )

    return response.data


def buscar_pull_request_por_id(
    pr_id: int,
) -> dict | None:
    response = (
        supabase
        .table("pull_requests")
        .select("*")
        .eq("id", pr_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def listar_analises_por_pr(
    pr_id: int,
) -> list[dict]:

    response = (
        supabase
        .table("analises")
        .select("*")
        .eq("pr_id", pr_id)
        .order("criado_em", desc=True)
        .execute()
    )

    return response.data



def obter_estatisticas() -> dict:
    # --------------------------------------------
    # Total de Pull Requests
    # --------------------------------------------

    prs_response = (
        supabase
        .table("pull_requests")
        .select("id", count="exact")
        .execute()
    )

    total_pull_requests = (
        prs_response.count or 0
    )

    # --------------------------------------------
    # Todas as análises
    # --------------------------------------------

    analyses_response = (
        supabase
        .table("analises")
        .select(
            "id, nota_geral, status, "
            "comentario_status, problemas"
        )
        .execute()
    )

    analyses = analyses_response.data

    # --------------------------------------------
    # Análises concluídas
    # --------------------------------------------

    concluidas = [
        analysis
        for analysis in analyses
        if analysis["status"] == "concluida"
    ]

    # --------------------------------------------
    # Notas
    # --------------------------------------------

    scores = [
        analysis["nota_geral"]
        for analysis in concluidas
        if analysis["nota_geral"] is not None
    ]

    nota_media = (
        sum(scores) / len(scores)
        if scores
        else 0
    )

    # --------------------------------------------
    # Quantidade de problemas
    # --------------------------------------------

    total_problemas = 0

    for analysis in concluidas:
        problemas = analysis.get("problemas")

        if isinstance(problemas, list):
            total_problemas += len(problemas)

    # --------------------------------------------
    # Comentários publicados
    # --------------------------------------------

    comentarios_publicados = sum(
        1
        for analysis in analyses
        if analysis["comentario_status"] == "publicado"
    )

    return {
        "total_pull_requests": total_pull_requests,
        "total_analises": len(analyses),
        "analises_concluidas": len(concluidas),
        "total_problemas": total_problemas,
        "comentarios_publicados": comentarios_publicados,
        "nota_media": round(nota_media, 2),
    }


def reiniciar_analise_para_retry(
    analysis_id: int,
) -> dict:
    """
    Reseta uma análise em estado 'erro' para 'processando',
    permitindo nova tentativa sem criar um registro duplicado.

    Nunca deve ser chamada para análises em estado 'concluida'.
    """
    response = (
        supabase
        .table("analises")
        .update({
            "status": "processando",
            "resumo": None,
            "problemas": None,
            "nota_geral": None,
        })
        .eq("id", analysis_id)
        .select("*")
        .execute()
    )

    return response.data[0]