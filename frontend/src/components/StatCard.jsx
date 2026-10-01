export function StatCard({ label, value, variant }) {
    const valueClass = [
        "stat-card__value",
        variant ? `stat-card__value--${variant}` : "",
    ]
        .filter(Boolean)
        .join(" ");

    return (
        <div className="stat-card">
            <span className="stat-card__label">{label}</span>
            <span className={valueClass}>{value ?? "—"}</span>
        </div>
    );
}
