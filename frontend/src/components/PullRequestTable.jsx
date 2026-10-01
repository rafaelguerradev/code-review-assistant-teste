import { EstadoPR } from "./Badges";

function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function shortSha(sha) {
    if (!sha) return "—";
    return sha.slice(0, 7);
}

export function PullRequestTable({ pullRequests, onSelect }) {
    return (
        <div className="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Título</th>
                        <th>Autor</th>
                        <th>Estado</th>
                        <th>Ação</th>
                        <th>Commit</th>
                        <th>Atualizado</th>
                    </tr>
                </thead>
                <tbody>
                    {pullRequests.map((pr) => (
                        <tr
                            key={pr.id}
                            onClick={() => onSelect(pr)}
                        >
                            <td className="td-mono">#{pr.pr_number}</td>
                            <td className="td-strong td-link">
                                {pr.title}
                            </td>
                            <td>{pr.author}</td>
                            <td>
                                <EstadoPR state={pr.state} />
                            </td>
                            <td className="td-mono">{pr.action}</td>
                            <td className="td-mono">
                                {shortSha(pr.head_sha)}
                            </td>
                            <td className="td-mono">
                                {formatDate(pr.atualizado_em)}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
