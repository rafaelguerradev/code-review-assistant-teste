export function StateBox({ icon, text, isError }) {
    return (
        <div className={`state-box${isError ? " state-box--error" : ""}`}>
            <span className="state-box__icon">{icon}</span>
            <span className="state-box__text">{text}</span>
        </div>
    );
}
