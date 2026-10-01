import { useState } from "react";
import {
    CategoryBadge,
    SeverityBadge,
    StatusAnalise,
    StatusComentario,
} from "./Badges";

function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("pt-BR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function shortSha(sha) {
    if (!sha) return "—";
    return sha.slice(0, 7);
}

/* ---- ISSUE CARD ---- */

function IssueCard({ issue }) {
    return (
        <div className="issue-card">
            <div className="issue-card__header">
                <CategoryBadge category={issue.category} />
                <SeverityBadge severity={issue.severity} />
            </div>

            <div className="issue-card__body">
                <div className="issue-card__location">
                    <code>{issue.file ?? "—"}</code>
                    {issue.line && (
                        <span>linha {issue.line}</span>
                    )}
                </div>

                {issue.evidence && (
                    <div className="issue-card__evidence">
                        {issue.evidence}
                    </div>
                )}

                <div>
                    <div className="issue-card__label">Descrição</div>
                    <div className="issue-card__text">
                        {issue.description}
                    </div>
                </div>

                {issue.suggestion && (
                    <div className="issue-card__suggestion">
                        <div className="issue-card__label">Sugestão</div>
                        <div className="issue-card__text">
                            {issue.suggestion}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

/* ---- ANALYSIS ITEM ---- */

export function AnalysisItem({ analysis }) {
    const [open, setOpen] = useState(false);

    const issues = Array.isArray(analysis.problemas)
        ? analysis.problemas
        : [];

    return (
        <div className="analysis-item">
            <div
                className="analysis-item__header"
                onClick={() => setOpen((v) => !v)}
            >
                <span className="analysis-item__sha">
                    {shortSha(analysis.head_sha)}
                </span>

                <div className="analysis-item__meta">
                    <StatusAnalise status={analysis.status} />
                    <StatusComentario
                        status={analysis.comentario_status}
                    />
                    {issues.length > 0 && (
                        <span className="badge badge--gray">
                            {issues.length}{" "}
                            {issues.length === 1
                                ? "problema"
                                : "problemas"}
                        </span>
                    )}
                </div>

                {analysis.nota_geral != null && (
                    <span className="analysis-item__score">
                        <span>{analysis.nota_geral}</span>/10
                    </span>
                )}

                <span className="analysis-item__date">
                    {formatDate(analysis.criado_em)}
                </span>

                <span
                    className={`chevron${open ? " chevron--open" : ""}`}
                >
                    ▼
                </span>
            </div>

            {open && (
                <>
                    {analysis.resumo && (
                        <div className="summary-box">
                            {analysis.resumo}
                        </div>
                    )}

                    {issues.length > 0 ? (
                        <div className="issues-section">
                            {issues.map((issue, idx) => (
                                <IssueCard key={idx} issue={issue} />
                            ))}
                        </div>
                    ) : (
                        <div
                            className="state-box"
                            style={{ padding: "24px" }}
                        >
                            <span className="state-box__text">
                                Nenhum problema encontrado nesta análise.
                            </span>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
