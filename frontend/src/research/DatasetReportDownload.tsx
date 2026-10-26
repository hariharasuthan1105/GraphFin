import { useEffect, useRef, useState } from "react";
import { datasetReportUrl, getAuthHeaders } from "./client";

export function DatasetReportDownload({ datasetId }: { datasetId: string }) {
  const controller = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  useEffect(() => () => controller.current?.abort(), []);
  async function download() {
    if (!["ibm-5k", "ibm-50k", "paysim"].includes(datasetId) || busy) return;
    const current = new AbortController();
    controller.current = current;
    setBusy(true);
    setMessage("Preparing verified dataset evidence…");
    setError(false);
    try {
      const response = await fetch(datasetReportUrl(datasetId), {
        method: "GET",
        signal: current.signal,
        credentials: "include",
        headers: {
          Accept: "application/pdf",
          ...getAuthHeaders(),
        },
        cache: "no-store",
      });
      if (!response.ok) {
        const value = await response.json().catch(() => null);
        throw new Error(
          typeof value?.message === "string"
            ? value.message
            : `Report unavailable (${response.status}).`,
        );
      }
      if (!response.headers.get("Content-Type")?.startsWith("application/pdf"))
        throw new Error("The server did not return a PDF report.");
      if (Number(response.headers.get("Content-Length") ?? 0) > 2 * 1024 * 1024)
        throw new Error("The report exceeds the download limit.");
      const data = await response.arrayBuffer();
      if (
        data.byteLength > 2 * 1024 * 1024 ||
        new TextDecoder().decode(data.slice(0, 5)) !== "%PDF-"
      )
        throw new Error("The downloaded report is invalid.");
      if (current.signal.aborted) return;
      const url = URL.createObjectURL(
        new Blob([data], { type: "application/pdf" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `GraphFin_${datasetId}_dataset_report.pdf`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage("Dataset report downloaded.");
    } catch (e) {
      if (!current.signal.aborted) {
        setError(true);
        setMessage(
          e instanceof Error ? e.message : "Dataset report unavailable.",
        );
      }
    } finally {
      if (!current.signal.aborted) setBusy(false);
    }
  }
  return (
    <div className="report-download">
      <button onClick={download} disabled={busy} aria-busy={busy}>
        {busy ? "Preparing report…" : "Download Dataset Report (PDF)"}{" "}
        <span aria-hidden="true">↓</span>
      </button>
      <p role={error ? "alert" : "status"}>{message}</p>
    </div>
  );
}
