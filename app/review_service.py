from app.db import (
    buscar_analise,
    criar_analise,
    finalizar_analise,
    marcar_analise_erro,
    marcar_comentario_erro,
    marcar_comentario_publicado,
    reiniciar_analise_para_retry,
    salvar_pull_request,
)

from app.github_client import (
    buscar_comentarios_pull_request,
    buscar_diff,
    comentar_pull_request,
)

from app.llm_client import analisar_diff
from app.review_formatter import formatar_review, gerar_marker


# ------------------------------------------------------------------
# IDEMPOTÊNCIA DO COMENTÁRIO
# ------------------------------------------------------------------

async def _encontrar_comentario_existente(
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
) -> dict | None:
    """
    Verifica se já existe um comentário com o marker desta análise
    no GitHub.

    Retorna o comentário (dict com id e html_url) caso encontre,
    ou None caso não exista.

    Isso protege contra o cenário em que o comentário foi criado no
    GitHub mas o banco não registrou o github_comment_id antes de
    uma falha.
    """
    marker = gerar_marker(repo_full_name, pr_number, head_sha)

    try:
        comentarios = await buscar_comentarios_pull_request(
            repo_full_name,
            pr_number,
        )
    except Exception as err:
        # Falha ao listar comentários não deve bloquear o fluxo.
        print(
            f"[REVIEW] Aviso: não foi possível consultar comentários "
            f"existentes: {err}"
        )
        return None

    for comentario in comentarios:
        corpo = comentario.get("body", "")
        if marker in corpo:
            return comentario

    return None


# ------------------------------------------------------------------
# PUBLICAÇÃO DO COMENTÁRIO (com detecção de duplicata)
# ------------------------------------------------------------------

async def _publicar_comentario(
    analysis_id: int,
    result,
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
) -> None:
    """
    Publica o comentário na Pull Request ou recupera um já existente.

    Fluxo:
    1. Verifica se o comentário já existe pelo marker.
    2. Se sim: registra o ID/URL no banco sem criar novo comentário.
    3. Se não: cria o comentário e registra no banco.

    Em caso de falha ao publicar, marca comentario_status = erro
    sem alterar o status da análise.
    """
    try:
        # 1. Detectar comentário existente pelo marker
        comentario_existente = await _encontrar_comentario_existente(
            repo_full_name,
            pr_number,
            head_sha,
        )

        if comentario_existente:
            print(
                f"[REVIEW] Comentário já existe no GitHub "
                f"(id={comentario_existente['id']}). "
                f"Registrando no banco sem criar duplicata."
            )

            marcar_comentario_publicado(
                analysis_id=analysis_id,
                comment_id=comentario_existente["id"],
                comment_url=comentario_existente["html_url"],
            )

            return

        # 2. Criar novo comentário
        review_body = formatar_review(
            result,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            head_sha=head_sha,
        )

        comment = await comentar_pull_request(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            body=review_body,
        )

        marcar_comentario_publicado(
            analysis_id=analysis_id,
            comment_id=comment["id"],
            comment_url=comment["html_url"],
        )

        print(
            f"[REVIEW] Comentário publicado: {comment['html_url']}"
        )

    except Exception as err:
        print(
            f"[REVIEW] Erro ao publicar comentário: {err}"
        )

        marcar_comentario_erro(
            analysis_id=analysis_id,
            error=str(err),
        )


# ------------------------------------------------------------------
# RETRY DE COMENTÁRIO (análise já concluída, comentário falhou)
# ------------------------------------------------------------------

async def _retry_comentario(
    analysis: dict,
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
) -> dict:
    """
    Tenta publicar o comentário de uma análise já concluída cujo
    comentário anterior falhou ou ainda está pendente.

    Não chama o LLM novamente — reconstrói o Markdown a partir dos
    dados já salvos no banco.
    """
    from app.llm_client import CodeReviewResult, ReviewIssue

    analysis_id = analysis["id"]

    print(
        f"[REVIEW] Análise já concluída (id={analysis_id}). "
        f"Tentando publicar comentário."
    )

    # Reconstrói o resultado a partir dos dados salvos.
    problemas_raw = analysis.get("problemas") or []
    issues = [ReviewIssue(**p) for p in problemas_raw]

    result = CodeReviewResult(
        summary=analysis.get("resumo", ""),
        issues=issues,
        overall_score=analysis.get("nota_geral", 0),
    )

    await _publicar_comentario(
        analysis_id=analysis_id,
        result=result,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        head_sha=head_sha,
    )

    return {
        "status": "comment_retried",
        "analysis_id": analysis_id,
    }


# ------------------------------------------------------------------
# PIPELINE PRINCIPAL
# ------------------------------------------------------------------

async def processar_pull_request(payload: dict) -> dict:
    repository = payload["repository"]
    pull_request = payload["pull_request"]

    action = payload["action"]

    repo_full_name = repository["full_name"]
    pr_number = pull_request["number"]
    head_sha = pull_request["head"]["sha"]

    print(
        f"[REVIEW] PR #{pr_number} SHA {head_sha[:7]} "
        f"({repo_full_name}) — ação: {action}"
    )

    # ------------------------------------------------------------------
    # 1. Salva ou atualiza a PR no banco
    # ------------------------------------------------------------------

    pr_data = {
        "repo_full_name": repo_full_name,
        "pr_number": pr_number,
        "title": pull_request["title"],
        "author": pull_request["user"]["login"],
        "action": action,
        "state": pull_request["state"],
        "head_sha": head_sha,
        "url": pull_request["html_url"],
    }

    pr = salvar_pull_request(pr_data)
    pr_id = pr["id"]

    # ------------------------------------------------------------------
    # 2. Filtra ações que não exigem análise
    # ------------------------------------------------------------------

    if action not in {"opened", "synchronize"}:
        print(
            f"[REVIEW] Ação '{action}' não exige análise. Ignorando."
        )

        return {
            "status": "ignored",
            "reason": "action_not_analyzable",
            "action": action,
        }

    # ------------------------------------------------------------------
    # 3. Verifica análise existente para este PR + SHA
    # ------------------------------------------------------------------

    analysis = buscar_analise(pr_id, head_sha)

    if analysis:
        status = analysis["status"]
        comentario_status = analysis.get("comentario_status")
        analysis_id = analysis["id"]

        # CASO 2 — análise concluída e comentário publicado
        if status == "concluida" and comentario_status == "publicado":
            print(
                f"[REVIEW] Análise {analysis_id} já concluída e "
                f"comentário publicado. Nenhuma ação necessária."
            )

            return {
                "status": "already_processed",
                "analysis_id": analysis_id,
            }

        # CASO 3 e 4 — análise concluída, comentário pendente ou com erro
        if status == "concluida" and comentario_status in {
            "erro", "pendente", None
        }:
            print(
                f"[REVIEW] Análise {analysis_id} existente, "
                f"mas comentário com status '{comentario_status}'. "
                f"Tentando publicar novamente."
            )

            return await _retry_comentario(
                analysis=analysis,
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                head_sha=head_sha,
            )

        # CASO 5 — análise ainda está sendo processada
        if status == "processando":
            print(
                f"[REVIEW] Análise {analysis_id} ainda está "
                f"processando. Não duplicar."
            )

            return {
                "status": "processing",
                "analysis_id": analysis_id,
            }

        # CASO 6 — análise anterior com erro: reinicia para retry
        if status == "erro":
            print(
                f"[REVIEW] Análise {analysis_id} com erro anterior. "
                f"Reiniciando para nova tentativa."
            )

            analysis = reiniciar_analise_para_retry(analysis_id)
            analysis_id = analysis["id"]

    else:
        # CASO 1 — primeira execução
        print(
            f"[REVIEW] Nenhuma análise encontrada para SHA "
            f"{head_sha[:7]}. Criando nova análise."
        )

        analysis = criar_analise(
            pr_id=pr_id,
            head_sha=head_sha,
        )
        analysis_id = analysis["id"]

    # ------------------------------------------------------------------
    # 4. Pipeline de análise (diff → LLM → banco)
    # ------------------------------------------------------------------

    try:
        diff = await buscar_diff(repo_full_name, pr_number)

        print(
            f"[REVIEW] Diff recebido: {len(diff)} caracteres."
        )

        result = await analisar_diff(diff)

        print("[REVIEW] Análise do LLM concluída.")

        finalizar_analise(
            analysis_id=analysis_id,
            result=result,
        )

        print(f"[REVIEW] Análise {analysis_id} salva com sucesso.")

    except Exception as err:
        print(f"[REVIEW] Erro durante análise: {err}")

        marcar_analise_erro(
            analysis_id=analysis_id,
            error=str(err),
        )

        raise

    # ------------------------------------------------------------------
    # 5. Publicação do comentário no GitHub
    # ------------------------------------------------------------------

    await _publicar_comentario(
        analysis_id=analysis_id,
        result=result,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        head_sha=head_sha,
    )

    return {
        "status": "completed",
        "analysis_id": analysis_id,
    }