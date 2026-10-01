def gerar_marker(
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
) -> str:
    """
    Gera um marcador HTML determinístico e invisível para ser embutido
    no comentário do GitHub.

    O mesmo repo + PR + SHA sempre produz o mesmo marcador, o que
    permite detectar se o comentário já existe mesmo que o banco não
    tenha registrado o github_comment_id.
    """
    return (
        f"<!-- ai-code-review: "
        f"{repo_full_name}:{pr_number}:{head_sha} -->"
    )


def formatar_review(
    result,
    repo_full_name: str,
    pr_number: int,
    head_sha: str,
) -> str:
    lines = []

    lines.append("# 🤖 AI Code Review")
    lines.append("")

    lines.append(
        f"**Nota geral: {result.overall_score}/10**"
    )
    lines.append("")

    lines.append("## Resumo")
    lines.append("")
    lines.append(result.summary)
    lines.append("")

    if not result.issues:
        lines.append(
            "✅ **Nenhum problema concreto foi identificado.**"
        )
        lines.append("")
        lines.append(
            "_Esta análise foi gerada automaticamente por IA._"
        )
        lines.append("")
        lines.append(
            gerar_marker(repo_full_name, pr_number, head_sha)
        )

        return "\n".join(lines)

    lines.append("## Problemas encontrados")
    lines.append("")

    for index, issue in enumerate(
        result.issues,
        start=1,
    ):
        lines.append(
            f"### {index}. {issue.category.upper()} "
            f"— {issue.severity.upper()}"
        )

        lines.append("")

        if issue.file != "unknown":
            lines.append(
                f"**Arquivo:** `{issue.file}`"
            )

        if issue.line is not None:
            lines.append(
                f"**Linha:** `{issue.line}`"
            )

        lines.append("")

        lines.append("**Evidência:**")
        lines.append("```text")
        lines.append(issue.evidence)
        lines.append("```")
        lines.append("")

        lines.append("**Descrição:**")
        lines.append(issue.description)
        lines.append("")

        lines.append("**Sugestão:**")
        lines.append(issue.suggestion)
        lines.append("")

    lines.append("---")
    lines.append(
        "_Esta análise foi gerada automaticamente por IA "
        "e deve ser revisada por um desenvolvedor._"
    )
    lines.append("")
    lines.append(
        gerar_marker(repo_full_name, pr_number, head_sha)
    )

    return "\n".join(lines)

