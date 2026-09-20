import React, { useState, useRef, useEffect } from "react";
import { api } from "../../api/client";

interface ExportDropdownProps {
  source: "official" | "custom";
  datasetId?: string;
  experimentLabel?: string;
  splitLabel?: string | null;
}

export const ExportDropdown: React.FC<ExportDropdownProps> = ({
  source,
  datasetId,
  experimentLabel,
  splitLabel,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleExport = async (format: "pdf" | "docx" | "csv") => {
    setIsExporting(true);
    setExportError(null);
    setIsOpen(false);

    try {
      const { blob, filename } = await api.generateReport({
        source,
        format,
        dataset_id: source === "custom" ? datasetId : undefined,
        experiment_label: experimentLabel || undefined,
        split_label: splitLabel || undefined,
      });

      // Trigger browser download
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err: any) {
      setExportError(err.message || "Failed to generate report.");
      setTimeout(() => setExportError(null), 5000);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
        className={`px-3 py-1.5 text-xs font-sans rounded border transition-colors flex items-center gap-2 ${
          isExporting
            ? "bg-surface-raised border-hairline text-text-tertiary cursor-not-allowed"
            : "border-hairline bg-surface hover:bg-surface-raised text-text-secondary hover:text-text-primary"
        }`}
        title="Export evaluation results"
      >
        {isExporting ? (
          <>
            <svg className="animate-spin h-3.5 w-3.5 text-accent-primary" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span>Generating...</span>
          </>
        ) : (
          <>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Export Report</span>
            <svg className="w-3 h-3 text-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1 w-48 bg-surface border border-hairline-strong rounded-md shadow-lg overflow-hidden z-50 py-1">
          <button
            type="button"
            onClick={() => handleExport("pdf")}
            className="w-full text-left px-3 py-2 text-xs font-sans text-text-primary hover:bg-surface-raised flex items-center gap-2"
          >
            <span className="font-mono text-[10px] px-1 py-0.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded">
              PDF
            </span>
            <span>Export as PDF</span>
          </button>

          <button
            type="button"
            onClick={() => handleExport("docx")}
            className="w-full text-left px-3 py-2 text-xs font-sans text-text-primary hover:bg-surface-raised flex items-center gap-2"
          >
            <span className="font-mono text-[10px] px-1 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded">
              DOCX
            </span>
            <span>Export as Word</span>
          </button>

          <button
            type="button"
            onClick={() => handleExport("csv")}
            className="w-full text-left px-3 py-2 text-xs font-sans text-text-primary hover:bg-surface-raised flex items-center gap-2"
          >
            <span className="font-mono text-[10px] px-1 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded">
              CSV
            </span>
            <span>Export as CSV</span>
          </button>
        </div>
      )}

      {exportError && (
        <div className="absolute right-0 mt-2 w-64 p-2 bg-red-950/90 border border-red-800 text-[11px] text-red-200 rounded shadow-md z-50">
          {exportError}
        </div>
      )}
    </div>
  );
};
