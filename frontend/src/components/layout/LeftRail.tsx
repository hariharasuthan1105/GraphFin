import React from "react";
import { useApp, NavItem } from "../../context/AppContext";

interface NavOption {
  id: NavItem;
  label: string;
}

const NAV_ITEMS: NavOption[] = [
  { id: "overview", label: "Overview" },
  { id: "datasets", label: "Datasets" },
  { id: "graph", label: "Graph" },
  { id: "features", label: "Features" },
  { id: "anomalies", label: "Anomaly Models" },
  { id: "labels_splits", label: "Labels & Splits" },
  { id: "evaluation", label: "Evaluation" },
];

export const LeftRail: React.FC = () => {
  const {
    activeNav,
    setActiveNav,
    isBackendConnected,
    datasetId,
  } = useApp();

  return (
    <aside className="w-[240px] flex-shrink-0 bg-surface border-r border-hairline flex flex-col justify-between h-screen select-none">
      <div>
        {/* Wordmark */}
        <div className="h-14 px-6 flex items-center border-b border-hairline">
          <span className="text-base font-medium font-sans text-text-primary tracking-tight">
            GraphFin
          </span>
          <span className="ml-2 text-xs font-mono text-text-tertiary">
            v1.0
          </span>
        </div>

        {/* Primary navigation list */}
        <nav className="py-4">
          <ul className="space-y-0.5">
            {NAV_ITEMS.map((item) => {
              const isActive = activeNav === item.id;
              return (
                <li key={item.id}>
                  <button
                    onClick={() => setActiveNav(item.id)}
                    className={`w-full text-left px-5 py-2.5 text-sm font-sans transition-colors flex items-center justify-between border-l-2 ${
                      isActive
                        ? "border-accent-primary text-text-primary font-medium bg-surface-raised/40"
                        : "border-transparent text-text-secondary hover:text-text-primary hover:bg-surface-raised/20"
                    }`}
                  >
                    <span>{item.label}</span>
                    {item.id === "datasets" && !datasetId && (
                      <span className="w-1.5 h-1.5 rounded-full bg-status-warning" title="No dataset selected" />
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>

      {/* Backend connection status footer */}
      <div className="p-4 border-t border-hairline text-xs font-sans text-text-tertiary flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isBackendConnected === true
                ? "bg-status-normal"
                : isBackendConnected === false
                ? "bg-status-suspicious"
                : "bg-status-warning"
            }`}
          />
          <span>
            {isBackendConnected === true
              ? "Backend connected"
              : isBackendConnected === false
              ? "Backend offline"
              : "Checking backend..."}
          </span>
        </div>
        <span className="font-mono text-[11px] text-text-tertiary">
          :8000
        </span>
      </div>
    </aside>
  );
};
