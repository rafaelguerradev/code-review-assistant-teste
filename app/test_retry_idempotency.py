"""
Testes de idempotência e retry do review_service.

Todos os testes são unitários e mocam GitHub API, Ollama e Supabase.
Não dependem de nenhum serviço externo.

Cenários cobertos:
  Teste 1 — Primeira execução (caminho feliz completo)
  Teste 2 — Mesmo SHA: análise concluída + comentário publicado → ignorar
  Teste 3 — Análise concluída + comentário com erro → retry comentário
  Teste 4 — Comentário existe no GitHub, banco sem github_comment_id
  Teste 5 — Análise ainda processando → não duplicar
  Teste 6 — Análise em erro → reiniciar e tentar novamente
  Teste 7 — Novo SHA → nova análise independente
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payload(
    action="opened",
    repo="owner/repo",
    pr_number=42,
    sha="abc1234567890",
    state="open",
):
    return {
        "action": action,
        "repository": {"full_name": repo},
        "pull_request": {
            "number": pr_number,
            "title": "Test PR",
            "user": {"login": "dev"},
            "state": state,
            "head": {"sha": sha},
            "html_url": f"https://github.com/{repo}/pull/{pr_number}",
        },
    }


def _make_analysis(
    id=1,
    pr_id=10,
    head_sha="abc1234567890",
    status="concluida",
    comentario_status="publicado",
    resumo="Análise ok.",
    nota_geral=8,
    problemas=None,
):
    return {
        "id": id,
        "pr_id": pr_id,
        "head_sha": head_sha,
        "status": status,
        "comentario_status": comentario_status,
        "resumo": resumo,
        "nota_geral": nota_geral,
        "problemas": problemas or [],
    }


def _make_comment(id=999, html_url="https://github.com/c/999"):
    return {"id": id, "html_url": html_url, "body": ""}


# ---------------------------------------------------------------------------
# Base com patches comuns
# ---------------------------------------------------------------------------

PATCHES = {
    "salvar_pr":        "app.review_service.salvar_pull_request",
    "buscar_analise":   "app.review_service.buscar_analise",
    "criar_analise":    "app.review_service.criar_analise",
    "finalizar":        "app.review_service.finalizar_analise",
    "marcar_erro":      "app.review_service.marcar_analise_erro",
    "marcar_pub":       "app.review_service.marcar_comentario_publicado",
    "marcar_com_erro":  "app.review_service.marcar_comentario_erro",
    "reiniciar":        "app.review_service.reiniciar_analise_para_retry",
    "buscar_diff":      "app.review_service.buscar_diff",
    "buscar_comments":  "app.review_service.buscar_comentarios_pull_request",
    "comentar":         "app.review_service.comentar_pull_request",
    "analisar_diff":    "app.review_service.analisar_diff",
    "formatar":         "app.review_service.formatar_review",
}


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# TESTE 1 — Primeira execução (caminho feliz)
# ---------------------------------------------------------------------------

class TestPrimeiraExecucao(unittest.TestCase):
    def test_cria_analise_chama_llm_publica_comentario(self):
        """
        Não existe análise prévia.
        Esperado: cria análise → chama LLM → salva → publica comentário.
        """
        from app.review_service import processar_pull_request

        pr_salva = {"id": 10}
        analise_criada = _make_analysis(
            id=1, status="processando", comentario_status=None
        )
        resultado_llm = MagicMock()
        resultado_llm.issues = []
        resultado_llm.summary = "Tudo ok."
        resultado_llm.overall_score = 10
        comentario = _make_comment()

        with (
            patch(PATCHES["salvar_pr"], return_value=pr_salva),
            patch(PATCHES["buscar_analise"], return_value=None),
            patch(PATCHES["criar_analise"], return_value=analise_criada),
            patch(PATCHES["buscar_diff"], new_callable=AsyncMock, return_value="diff"),
            patch(PATCHES["analisar_diff"], new_callable=AsyncMock, return_value=resultado_llm),
            patch(PATCHES["finalizar"], return_value={}),
            patch(PATCHES["buscar_comments"], new_callable=AsyncMock, return_value=[]),
            patch(PATCHES["comentar"], new_callable=AsyncMock, return_value=comentario),
            patch(PATCHES["marcar_pub"], return_value={}),
            patch(PATCHES["formatar"], return_value="## Review\n<!-- marker -->"),
        ):
            result = run(processar_pull_request(_make_payload()))

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["analysis_id"], 1)


# ---------------------------------------------------------------------------
# TESTE 2 — Mesmo SHA: concluída + publicado → ignorar
# ---------------------------------------------------------------------------

class TestJaProcessado(unittest.TestCase):
    def test_nao_chama_llm_nao_publica_comentario(self):
        """
        Análise já concluída e comentário publicado.
        Esperado: retorna already_processed sem chamar LLM nem GitHub.
        """
        from app.review_service import processar_pull_request

        analise = _make_analysis(
            status="concluida", comentario_status="publicado"
        )

        mock_llm = AsyncMock()
        mock_comentar = AsyncMock()

        with (
            patch(PATCHES["salvar_pr"], return_value={"id": 10}),
            patch(PATCHES["buscar_analise"], return_value=analise),
            patch(PATCHES["analisar_diff"], mock_llm),
            patch(PATCHES["comentar"], mock_comentar),
        ):
            result = run(processar_pull_request(_make_payload()))

        self.assertEqual(result["status"], "already_processed")
        self.assertEqual(result["analysis_id"], 1)
        mock_llm.assert_not_called()
        mock_comentar.assert_not_called()


# ---------------------------------------------------------------------------
# TESTE 3 — Análise concluída + comentário com erro → retry comentário
# ---------------------------------------------------------------------------

class TestRetryComentario(unittest.TestCase):
    def test_nao_chama_llm_tenta_comentario_novamente(self):
        """
        Análise concluída, mas comentario_status = 'erro'.
        Esperado: não chama LLM, tenta publicar comentário novamente.
        """
        from app.review_service import processar_pull_request

        analise = _make_analysis(
            status="concluida",
            comentario_status="erro",
            problemas=[],
        )
        comentario = _make_comment()

        mock_llm = AsyncMock()

        with (
            patch(PATCHES["salvar_pr"], return_value={"id": 10}),
            patch(PATCHES["buscar_analise"], return_value=analise),
            patch(PATCHES["analisar_diff"], mock_llm),
            patch(PATCHES["buscar_comments"], new_callable=AsyncMock, return_value=[]),
            patch(PATCHES["comentar"], new_callable=AsyncMock, return_value=comentario),
            patch(PATCHES["marcar_pub"], return_value={}),
            patch(PATCHES["formatar"], return_value="## Review\n<!-- marker -->"),
        ):
            result = run(processar_pull_request(_make_payload()))

        self.assertEqual(result["status"], "comment_retried")
        mock_llm.assert_not_called()


# ---------------------------------------------------------------------------
# TESTE 4 — Comentário existe no GitHub, banco sem github_comment_id
# ---------------------------------------------------------------------------

class TestComentarioExisteNoGitHub(unittest.TestCase):
    def test_detecta_marker_nao_cria_duplicata(self):
        """
        Análise concluída + comentario_status = 'erro'.
        GitHub já tem comentário com o marker correto.
        Esperado: recupera comentário existente, não cria duplicata.
        """
        from app.review_service import processar_pull_request
        from app.review_formatter import gerar_marker

        sha = "abc1234567890"
        marker = gerar_marker("owner/repo", 42, sha)

        analise = _make_analysis(
            status="concluida",
            comentario_status="erro",
            problemas=[],
        )

        comentario_existente = {
            "id": 777,
            "html_url": "https://github.com/c/777",
            "body": f"## Review\n{marker}",
        }

        mock_comentar = AsyncMock()
        mock_marcar_pub = MagicMock()

        with (
            patch(PATCHES["salvar_pr"], return_value={"id": 10}),
            patch(PATCHES["buscar_analise"], return_value=analise),
            patch(PATCHES["analisar_diff"], AsyncMock()),
            patch(
                PATCHES["buscar_comments"],
                new_callable=AsyncMock,
                return_value=[comentario_existente],
            ),
            patch(PATCHES["comentar"], mock_comentar),
            patch(PATCHES["marcar_pub"], mock_marcar_pub),
            patch(PATCHES["formatar"], return_value=f"## Review\n{marker}"),
        ):
            result = run(processar_pull_request(_make_payload(sha=sha)))

        # Não deve ter chamado POST de criação de comentário
        mock_comentar.assert_not_called()

        # Deve ter registrado o comentário existente no banco
        mock_marcar_pub.assert_called_once_with(
            analysis_id=1,
            comment_id=777,
            comment_url="https://github.com/c/777",
        )


# ---------------------------------------------------------------------------
# TESTE 5 — Análise ainda processando → não duplicar
# ---------------------------------------------------------------------------

class TestAnaliseProcessando(unittest.TestCase):
    def test_retorna_processing_sem_criar_nova_analise(self):
        """
        Análise com status = 'processando' já existe.
        Esperado: retorna 'processing', não cria outra análise.
        """
        from app.review_service import processar_pull_request

        analise = _make_analysis(status="processando", comentario_status=None)
        mock_criar = MagicMock()
        mock_llm = AsyncMock()

        with (
            patch(PATCHES["salvar_pr"], return_value={"id": 10}),
            patch(PATCHES["buscar_analise"], return_value=analise),
            patch(PATCHES["criar_analise"], mock_criar),
            patch(PATCHES["analisar_diff"], mock_llm),
        ):
            result = run(processar_pull_request(_make_payload()))

        self.assertEqual(result["status"], "processing")
        self.assertEqual(result["analysis_id"], 1)
        mock_criar.assert_not_called()
        mock_llm.assert_not_called()


# ---------------------------------------------------------------------------
# TESTE 6 — Análise em erro → reinicia e tenta novamente
# ---------------------------------------------------------------------------

class TestRetryAnalise(unittest.TestCase):
    def test_reinicia_analise_em_erro_e_chama_llm(self):
        """
        Análise com status = 'erro' já existe.
        Esperado: reinicia o registro e executa o pipeline novamente.
        """
        from app.review_service import processar_pull_request

        analise_erro = _make_analysis(
            id=5, status="erro", comentario_status=None
        )
        analise_reiniciada = _make_analysis(
            id=5, status="processando", comentario_status=None
        )
        resultado_llm = MagicMock()
        resultado_llm.issues = []
        resultado_llm.summary = "Ok após retry."
        resultado_llm.overall_score = 9
        comentario = _make_comment()

        with (
            patch(PATCHES["salvar_pr"], return_value={"id": 10}),
            patch(PATCHES["buscar_analise"], return_value=analise_erro),
            patch(PATCHES["reiniciar"], return_value=analise_reiniciada),
            patch(PATCHES["buscar_diff"], new_callable=AsyncMock, return_value="diff"),
            patch(PATCHES["analisar_diff"], new_callable=AsyncMock, return_value=resultado_llm),
            patch(PATCHES["finalizar"], return_value={}),
            patch(PATCHES["buscar_comments"], new_callable=AsyncMock, return_value=[]),
            patch(PATCHES["comentar"], new_callable=AsyncMock, return_value=comentario),
            patch(PATCHES["marcar_pub"], return_value={}),
            patch(PATCHES["formatar"], return_value="## Review\n<!-- marker -->"),
        ):
            result = run(processar_pull_request(_make_payload()))

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["analysis_id"], 5)


# ---------------------------------------------------------------------------
# TESTE 7 — Novo SHA → nova análise independente
# ---------------------------------------------------------------------------

class TestNovoSHA(unittest.TestCase):
    def test_sha_diferente_gera_nova_analise(self):
        """
        SHA A já existe com análise concluída.
        SHA B não existe.
        Esperado: SHA B cria nova análise independente.
        """
        from app.review_service import processar_pull_request

        analise_sha_b_criada = _make_analysis(
            id=20,
            head_sha="bbb0000000000",
            status="processando",
            comentario_status=None,
        )
        resultado_llm = MagicMock()
        resultado_llm.issues = []
        resultado_llm.summary = "SHA B ok."
        resultado_llm.overall_score = 10
        comentario = _make_comment()

        with (
            patch(PATCHES["salvar_pr"], return_value={"id": 10}),
            # SHA B não tem análise ainda
            patch(PATCHES["buscar_analise"], return_value=None),
            patch(PATCHES["criar_analise"], return_value=analise_sha_b_criada),
            patch(PATCHES["buscar_diff"], new_callable=AsyncMock, return_value="diff"),
            patch(PATCHES["analisar_diff"], new_callable=AsyncMock, return_value=resultado_llm),
            patch(PATCHES["finalizar"], return_value={}),
            patch(PATCHES["buscar_comments"], new_callable=AsyncMock, return_value=[]),
            patch(PATCHES["comentar"], new_callable=AsyncMock, return_value=comentario),
            patch(PATCHES["marcar_pub"], return_value={}),
            patch(PATCHES["formatar"], return_value="## Review\n<!-- marker -->"),
        ):
            result = run(
                processar_pull_request(
                    _make_payload(sha="bbb0000000000", action="synchronize")
                )
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["analysis_id"], 20)


# ---------------------------------------------------------------------------
# TESTES DO MARKER (review_formatter)
# ---------------------------------------------------------------------------

class TestMarker(unittest.TestCase):
    def test_marker_deterministico(self):
        """O mesmo input sempre produz o mesmo marker."""
        from app.review_formatter import gerar_marker

        m1 = gerar_marker("owner/repo", 12, "abc123")
        m2 = gerar_marker("owner/repo", 12, "abc123")
        self.assertEqual(m1, m2)

    def test_marker_diferente_para_sha_diferente(self):
        from app.review_formatter import gerar_marker

        m1 = gerar_marker("owner/repo", 12, "abc123")
        m2 = gerar_marker("owner/repo", 12, "xyz999")
        self.assertNotEqual(m1, m2)

    def test_marker_presente_no_comentario(self):
        """formatar_review deve incluir o marker no corpo."""
        from app.review_formatter import formatar_review, gerar_marker
        from app.llm_client import CodeReviewResult

        result = CodeReviewResult(
            summary="Sem problemas.",
            issues=[],
            overall_score=10,
        )
        marker = gerar_marker("owner/repo", 42, "sha123")
        body = formatar_review(result, "owner/repo", 42, "sha123")

        self.assertIn(marker, body)

    def test_acao_ignorada_nao_processa(self):
        """Ações como 'closed' não devem iniciar análise."""
        from app.review_service import processar_pull_request

        with (
            patch(PATCHES["salvar_pr"], return_value={"id": 10}),
            patch(PATCHES["buscar_analise"], return_value=None),
        ):
            result = run(
                processar_pull_request(_make_payload(action="closed"))
            )

        self.assertEqual(result["status"], "ignored")


if __name__ == "__main__":
    unittest.main(verbosity=2)
