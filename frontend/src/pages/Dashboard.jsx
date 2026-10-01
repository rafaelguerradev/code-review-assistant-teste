import { useEffect, useState } from "react";
import { getPullRequests, getStats } from "../services/api";
import { StatCard } from "../components/StatCard";
import { PullRequestTable } from "../components/PullRequestTable";
import { StateBox } from "../components/StateBox";


export function Dashboard({ onSelectPR }) {
    const [stats, setStats] = useState(null);
    const [pullRequests, setPullRequests] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function load() {
            try {
                setLoading(true);
                setError(null);

                const [statsData, prsData] = await Promise.all([
                    getStats(),
                    getPullRequests(),
                ]);

                setStats(statsData);
                setPullRequests(prsData);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        load();
    }, []);

    if (loading) {
        return (
            <StateBox icon="⏳" text="Carregando dashboard..." />
        );
    }

    if (error) {
        return (
            <StateBox
                icon="⚠️"
                text={`Erro ao carregar dados: ${error}`}
                isError
            />
        );
    }

    return (
        <div className="page">
            <div className="container">
                <div className="page__header">
                    <h1 className="page__title">Dashboard</h1>
                    <p className="page__subtitle">
                        Visão geral das análises automáticas de Pull Requests
                    </p>
                </div>

                {/* MÉTRICAS */}
                <div className="stat-grid">
                    <StatCard
                        label="Pull Requests"
                        value={stats?.total_pull_requests}
                    />
                    <StatCard
                        label="Total de análises"
                        value={stats?.total_analises}
                    />
                    <StatCard
                        label="Análises concluídas"
                        value={stats?.analises_concluidas}
                        variant="green"
                    />
                    <StatCard
                        label="Problemas encontrados"
                        value={stats?.total_problemas}
                    />
                    <StatCard
                        label="Comentários publicados"
                        value={stats?.comentarios_publicados}
                    />
                    <StatCard
                        label="Nota média"
                        value={
                            stats?.nota_media != null
                                ? `${stats.nota_media}/10`
                                : null
                        }
                        variant="accent"
                    />
                </div>

                {/* LISTA DE PRs */}
                <div className="section">
                    <div className="section__header">
                        <span className="section__title">
                            Pull Requests
                        </span>
                        <span className="section__count">
                            {pullRequests.length}
                        </span>
                    </div>

                    {pullRequests.length === 0 ? (
                        <StateBox
                            icon="📭"
                            text="Nenhuma Pull Request registrada ainda."
                        />
                    ) : (
                        <PullRequestTable
                            pullRequests={pullRequests}
                            onSelect={onSelectPR}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}
