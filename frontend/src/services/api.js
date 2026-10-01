const BASE_URL = "http://localhost:8000";


async function apiFetch(path) {
    const response = await fetch(`${BASE_URL}${path}`);

    if (!response.ok) {
        throw new Error(
            `Erro ${response.status}: ${response.statusText}`
        );
    }

    return response.json();
}


export function getStats() {
    return apiFetch("/stats");
}


export function getPullRequests() {
    return apiFetch("/pull-requests");
}


export function getPullRequest(id) {
    return apiFetch(`/pull-requests/${id}`);
}


export function getPullRequestAnalyses(id) {
    return apiFetch(`/pull-requests/${id}/analyses`);
}
