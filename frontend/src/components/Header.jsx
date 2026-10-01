export function Header({ onLogoClick }) {
    return (
        <header className="header">
            <div className="container">
                <div className="header__inner">
                    <div
                        className="header__logo"
                        onClick={onLogoClick}
                    >
                        <div className="header__icon">🤖</div>
                        <span className="header__title">
                            AI Code Review
                        </span>
                    </div>
                    <span className="header__subtitle">
                        Análise automática de Pull Requests
                    </span>
                </div>
            </div>
        </header>
    );
}
