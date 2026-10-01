import { useState } from "react";
import { Header } from "./components/Header";
import { Dashboard } from "./pages/Dashboard";
import { PullRequestDetails } from "./pages/PullRequestDetails";


function App() {
    // Navegação simples por estado: null = dashboard, id = detalhes da PR
    const [selectedPrId, setSelectedPrId] = useState(null);

    function handleSelectPR(pr) {
        setSelectedPrId(pr.id);
    }

    function handleBack() {
        setSelectedPrId(null);
    }

    return (
        <div className="layout">
            <Header onLogoClick={handleBack} />

            {selectedPrId === null ? (
                <Dashboard onSelectPR={handleSelectPR} />
            ) : (
                <PullRequestDetails
                    prId={selectedPrId}
                    onBack={handleBack}
                />
            )}
        </div>
    );
}


export default App;