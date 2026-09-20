import React, { useState, useEffect, Suspense, lazy } from "react";
import { AppProvider, useApp, NavItem } from "./context/AppContext";
import { LeftRail } from "./components/layout/LeftRail";
import { TopBar } from "./components/layout/TopBar";
import { OverviewScreen } from "./screens/OverviewScreen";

// Dynamic code-splitting: Heavy screens loaded on demand when navigated to
const DatasetsScreen = lazy(() =>
  import("./screens/DatasetsScreen").then((m) => ({ default: m.DatasetsScreen }))
);
const GraphScreen = lazy(() =>
  import("./screens/GraphScreen").then((m) => ({ default: m.GraphScreen }))
);
const FeaturesScreen = lazy(() =>
  import("./screens/FeaturesScreen").then((m) => ({ default: m.FeaturesScreen }))
);
const AnomalyScreen = lazy(() =>
  import("./screens/AnomalyScreen").then((m) => ({ default: m.AnomalyScreen }))
);
const LabelsSplitScreen = lazy(() =>
  import("./screens/LabelsSplitScreen").then((m) => ({ default: m.LabelsSplitScreen }))
);
const EvaluationScreen = lazy(() =>
  import("./screens/EvaluationScreen").then((m) => ({ default: m.EvaluationScreen }))
);

const ScreenLoadingFallback: React.FC = () => (
  <div className="flex flex-col items-center justify-center min-h-[360px] space-y-3">
    <div className="w-6 h-6 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
    <span className="text-xs font-mono text-text-tertiary">Loading module...</span>
  </div>
);

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
            <Suspense fallback={<ScreenLoadingFallback />}>
              {displayNav === "overview" && <OverviewScreen />}
              {displayNav === "datasets" && <DatasetsScreen />}
              {displayNav === "graph" && <GraphScreen />}
              {displayNav === "features" && <FeaturesScreen />}
              {displayNav === "anomalies" && <AnomalyScreen />}
              {displayNav === "labels_splits" && <LabelsSplitScreen />}
              {displayNav === "evaluation" && <EvaluationScreen />}
            </Suspense>
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
