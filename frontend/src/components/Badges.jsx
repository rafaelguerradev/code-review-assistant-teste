/**
 * Retorna a classe CSS do badge com base em um mapa de valores.
 */
export function getBadgeClass(value, map) {
    return `badge badge--${map[value] ?? "gray"}`;
}

/* ---- STATUS DA ANÁLISE ---- */

const STATUS_ANALISE_MAP = {
    concluida:    "green",
    processando:  "yellow",
    erro:         "red",
};

export function StatusAnalise({ status }) {
    return (
        <span className={getBadgeClass(status, STATUS_ANALISE_MAP)}>
            {status ?? "—"}
        </span>
    );
}

/* ---- STATUS DO COMENTÁRIO ---- */

const STATUS_COMENTARIO_MAP = {
    publicado: "green",
    pendente:  "gray",
    erro:      "red",
};

export function StatusComentario({ status }) {
    return (
        <span className={getBadgeClass(status, STATUS_COMENTARIO_MAP)}>
            {status ?? "pendente"}
        </span>
    );
}

/* ---- ESTADO DA PR ---- */

const ESTADO_PR_MAP = {
    open:   "green",
    closed: "gray",
    merged: "purple",
};

export function EstadoPR({ state }) {
    return (
        <span className={getBadgeClass(state, ESTADO_PR_MAP)}>
            {state ?? "—"}
        </span>
    );
}

/* ---- SEVERIDADE ---- */

const SEVERITY_MAP = {
    critical: "red",
    high:     "orange",
    medium:   "yellow",
    low:      "blue",
};

export function SeverityBadge({ severity }) {
    return (
        <span className={getBadgeClass(severity, SEVERITY_MAP)}>
            {severity ?? "—"}
        </span>
    );
}

/* ---- CATEGORIA ---- */

const CATEGORY_MAP = {
    bug:         "red",
    security:    "orange",
    performance: "yellow",
    design:      "purple",
    readability: "blue",
    other:       "gray",
};

export function CategoryBadge({ category }) {
    return (
        <span className={getBadgeClass(category, CATEGORY_MAP)}>
            {category ?? "—"}
        </span>
    );
}
