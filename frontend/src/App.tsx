import React, { useState, useEffect } from "react";
import { AppProvider, useApp, NavItem } from "./context/AppContext";
import { LeftRail } from "./components/layout/LeftRail";
import { TopBar } from "./components/layout/TopBar";
import { OverviewScreen } from "./screens/OverviewScreen";
import { DatasetsScreen } from "./screens/DatasetsScreen";
import { GraphScreen } from "./screens/GraphScreen";
import { FeaturesScreen } from "./screens/FeaturesScreen";
import { AnomalyScreen } from "./screens/AnomalyScreen";
import { LabelsSplitScreen } from "./screens/LabelsSplitScreen";
import { EvaluationScreen } from "./screens/EvaluationScreen";

const MainLayout: React.FC = () => {
  const { activeNav, isBackendConnected, checkBackendHealth } = useApp();
  const [displayNav, setDisplayNav] = useState<NavItem>(activeNav);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // 150ms depth-shift panel transitions:
  // Outgoing panel scales to 0.98 & fades out; incoming scales from 1.02 to 1.0 & fades in
  useEffect(() => {
    if (activeNav !== displayNav) {
      setIsTransitioning(true);
      const timer = setTimeout(() => {
        setDisplayNav(activeNav);
        setIsTransitioning(false);
      }, 140);
      return () => clearTimeout(timer);
    }
  }, [activeNav, displayNav]);

  return (
    <div className="flex h-screen w-screen bg-canvas text-text-primary overflow-hidden font-sans">
      {/* Left Navigation Rail (240px fixed) */}
      <LeftRail />

      {/* Main Content Pane */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Top bar with dataset ID and experiment context */}
        <TopBar />

        {/* Backend offline warning banner */}
        {isBackendConnected === false && (
          <div className="bg-[#2D1619] border-b border-[#521A1F] px-6 py-2 flex items-center justify-between text-xs font-sans text-status-suspicious select-none">
            <span>
              FastAPI backend is unreachable at port 8000. Start backend server or check network connection.
            </span>
            <button
              onClick={() => checkBackendHealth()}
              className="px-2 py-0.5 rounded bg-surface border border-[#521A1F] text-text-primary hover:bg-surface-raised transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Dynamic Screen Container with 150ms depth-shift transitions */}
        <main
          className={`flex-1 overflow-y-auto ${
            displayNav === "graph" ? "p-0 overflow-hidden" : "p-8"
          }`}
        >
          <div
            key={displayNav}
            className={`w-full ${displayNav === "graph" ? "h-full" : "min-h-full"} ${
              isTransitioning ? "animate-panel-out" : "animate-panel-in"
            }`}
          >
            {displayNav === "overview" && <OverviewScreen />}
            {displayNav === "datasets" && <DatasetsScreen />}
            {displayNav === "graph" && <GraphScreen />}
            {displayNav === "features" && <FeaturesScreen />}
            {displayNav === "anomalies" && <AnomalyScreen />}
            {displayNav === "labels_splits" && <LabelsSplitScreen />}
            {displayNav === "evaluation" && <EvaluationScreen />}
          </div>
        </main>
      </div>
    </div>
  );
};

export function App() {
  return (
    <AppProvider>
      <MainLayout />
    </AppProvider>
  );
}

export default App;
