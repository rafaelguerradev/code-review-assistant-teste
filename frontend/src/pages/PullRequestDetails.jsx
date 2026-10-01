import { useEffect, useState } from "react";
import { getPullRequest, getPullRequestAnalyses } from "../services/api";
import { AnalysisItem } from "../components/AnalysisItem";
import { EstadoPR } from "../components/Badges";
import { StateBox } from "../components/StateBox";


export function PullRequestDetails({ prId, onBack }) {
    const [pr, setPr] = useState(null);
    const [analyses, setAnalyses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function load() {
            try {
                setLoading(true);
                setError(null);

                const [prData, analysesData] = await Promise.all([
                    getPullRequest(prId),
                    getPullRequestAnalyses(prId),
                ]);

                setPr(prData);
                setAnalyses(analysesData);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        load();
    }, [prId]);


    if (loading) {
        return (
            <div className="page">
                <div className="container">
                    <StateBox icon="⏳" text="Carregando detalhes..." />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="page">
                <div className="container">
                    <StateBox
                        icon="⚠️"
                        text={`Erro: ${error}`}
                        isError
                    />
                </div>
            </div>
        );
    }

    return (
        <div className="page">
            <div className="container">
                <button className="btn-back" onClick={onBack}>
                    ← Voltar ao dashboard
                </button>

                {/* CABEÇALHO DA PR */}
                <div className="detail-card">
                    <div className="detail-card__title">
                        PR #{pr.pr_number} — {pr.title}
                    </div>

                    <div className="detail-meta">
                        <div className="detail-meta__item">
                            <span>Repositório</span>
                            <strong>{pr.repo_full_name}</strong>
                        </div>
                        <div className="detail-meta__item">
                            <span>Autor</span>
                            <strong>{pr.author}</strong>
                        </div>
                        <div className="detail-meta__item">
                            <span>Estado</span>
                            <EstadoPR state={pr.state} />
                        </div>
                        <div className="detail-meta__item">
                            <span>Ação</span>
                            <strong>{pr.action}</strong>
                        </div>
                    </div>

                    {pr.url && (
                        <a
                            href={pr.url}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            Abrir no GitHub ↗
                        </a>
                    )}
                </div>

                {/* HISTÓRICO DE ANÁLISES */}
                <div className="section">
                    <div className="section__header">
                        <span className="section__title">
                            Histórico de análises
                        </span>
                        <span className="section__count">
                            {analyses.length}
                        </span>
                    </div>

                    {analyses.length === 0 ? (
                        <StateBox
                            icon="📭"
                            text="Nenhuma análise registrada para esta Pull Request."
                        />
                    ) : (
                        <div className="analysis-list">
                            {analyses.map((analysis) => (
                                <AnalysisItem
                                    key={analysis.id}
                                    analysis={analysis}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
