import React, { useState, useRef, useEffect } from "react";
import {
  useApp,
  ResearchTier,
  RESEARCH_TIER_IDS,
  RESEARCH_TIER_LABELS,
  isOfficialResearchDataset,
} from "../../context/AppContext";
import { truncateId } from "../../utils/formatters";

export const TopBar: React.FC = () => {
  const {
    datasetId,
    setDatasetId,
    researchTier,
    setResearchTier,
    isOfficialResearch,
    datasetHistory,
    setActiveNav,
  } = useApp();

  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Filter custom datasets (excluding official research IDs)
  const customDatasets = datasetHistory.filter(
    (d) => d.id !== RESEARCH_TIER_IDS.medium_real && d.id !== RESEARCH_TIER_IDS.large_real
  );

  // Current active label display
  let currentDisplay = "";
  if (datasetId === RESEARCH_TIER_IDS.medium_real) {
    currentDisplay = RESEARCH_TIER_LABELS.medium_real;
  } else if (datasetId === RESEARCH_TIER_IDS.large_real) {
    currentDisplay = RESEARCH_TIER_LABELS.large_real;
  } else {
    const matched = customDatasets.find((d) => d.id === datasetId);
    currentDisplay = matched?.name
      ? `Custom — ${matched.name}`
      : `Custom — ${truncateId(datasetId, 8, 6)}`;
  }

  const handleSelectOfficial = (tier: ResearchTier) => {
    setResearchTier(tier);
    setIsOpen(false);
  };

  const handleSelectCustom = (id: string) => {
    setDatasetId(id);
    setIsOpen(false);
  };

  const handleOpenUpload = () => {
    setActiveNav("datasets");
    setIsOpen(false);
  };

  return (
    <header className="h-14 bg-surface border-b border-hairline px-6 flex items-center justify-between flex-shrink-0 select-none relative z-30">
      {/* ── 3-Kind Dataset Selector ── */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-sans text-text-tertiary font-medium">
          Dataset:
        </span>

        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className={`px-3 py-1.5 text-xs font-sans rounded border transition-colors flex items-center gap-2 max-w-[460px] ${
              isOpen
                ? "bg-surface-raised border-accent-primary text-text-primary"
                : "bg-surface-raised/80 border-hairline text-text-primary hover:border-hairline-strong hover:bg-surface-raised"
            }`}
            title="Select dataset or upload new data"
          >
            {isOfficialResearch ? (
              <span className="w-1.5 h-1.5 rounded-full bg-accent-primary flex-shrink-0" />
            ) : (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
            )}

            <span className="truncate font-medium">{currentDisplay}</span>

            {isOfficialResearch ? (
              <span className="px-1.5 py-0.2 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-[10px] font-mono uppercase tracking-wider flex-shrink-0">
                Locked
              </span>
            ) : (
              <span className="px-1.5 py-0.2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded text-[10px] font-mono uppercase tracking-wider flex-shrink-0">
                Custom
              </span>
            )}

            <svg
              className={`w-3.5 h-3.5 text-text-tertiary transition-transform ml-1 flex-shrink-0 ${
                isOpen ? "rotate-180" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Dropdown Menu */}
          {isOpen && (
            <div className="absolute left-0 mt-1 w-[480px] bg-surface border border-hairline-strong rounded-md shadow-xl overflow-hidden z-50 text-left">
              {/* Section 1: Official Research Benchmarks */}
              <div className="p-2 border-b border-hairline bg-surface-raised/40">
                <span className="text-[10px] font-mono tracking-wider uppercase text-text-tertiary font-semibold px-2 block mb-1">
                  Official Research Benchmarks (Locked)
                </span>

                <button
                  type="button"
                  onClick={() => handleSelectOfficial("medium_real")}
                  className={`w-full text-left px-2.5 py-2 rounded text-xs font-sans transition-colors flex items-center justify-between ${
                    datasetId === RESEARCH_TIER_IDS.medium_real
                      ? "bg-accent-primary/15 text-text-primary font-medium"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-raised"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    <span>{RESEARCH_TIER_LABELS.medium_real}</span>
                  </div>
                  <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-[10px] font-mono uppercase">
                    Locked
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => handleSelectOfficial("large_real")}
                  className={`w-full text-left px-2.5 py-2 rounded text-xs font-sans transition-colors flex items-center justify-between mt-0.5 ${
                    datasetId === RESEARCH_TIER_IDS.large_real
                      ? "bg-accent-primary/15 text-text-primary font-medium"
                      : "text-text-secondary hover:text-text-primary hover:bg-surface-raised"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    <span>{RESEARCH_TIER_LABELS.large_real}</span>
                  </div>
                  <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-[10px] font-mono uppercase">
                    Locked
                  </span>
                </button>
              </div>

              {/* Section 2: Custom Uploaded Datasets */}
              {customDatasets.length > 0 && (
                <div className="p-2 border-b border-hairline max-h-48 overflow-y-auto">
                  <span className="text-[10px] font-mono tracking-wider uppercase text-text-tertiary font-semibold px-2 block mb-1">
                    Custom Uploaded Datasets
                  </span>
                  {customDatasets.map((item) => {
                    const isSelected = datasetId === item.id;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => handleSelectCustom(item.id)}
                        className={`w-full text-left px-2.5 py-1.5 rounded text-xs font-sans transition-colors flex items-center justify-between mb-0.5 ${
                          isSelected
                            ? "bg-emerald-500/15 text-text-primary font-medium"
                            : "text-text-secondary hover:text-text-primary hover:bg-surface-raised"
                        }`}
                      >
                        <div className="truncate pr-2">
                          <span className="text-text-primary">Custom — {item.name}</span>
                          <span className="text-[10px] font-mono text-text-tertiary block">
                            ID: {truncateId(item.id, 8, 4)}{" "}
                            {item.transactions ? `· ${item.transactions.toLocaleString()} txs` : ""}{" "}
                            {item.users ? `· ${item.users.toLocaleString()} accounts` : ""}
                          </span>
                        </div>
                        {isSelected && (
                          <span className="text-emerald-400 text-xs font-bold">✓</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Section 3: Upload Action */}
              <div className="p-2 bg-surface">
                <button
                  type="button"
                  onClick={handleOpenUpload}
                  className="w-full text-left px-2.5 py-2 rounded text-xs font-sans text-accent-primary hover:bg-accent-primary/10 transition-colors flex items-center gap-2 font-medium"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <span>Upload new dataset...</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right side status */}
      <div className="flex items-center gap-3 text-xs font-sans">
        {isOfficialResearch ? (
          <span className="text-text-tertiary font-sans text-[11px] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
            IBM AML HI-Small · locked research results
          </span>
        ) : (
          <span className="text-text-tertiary font-sans text-[11px] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Custom Evaluation · live dataset
          </span>
        )}
      </div>
    </header>
  );
};
