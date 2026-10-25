import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { TITLE } from "./research/state";
import "./research/research.css";
const Legacy = lazy(() => import("./LegacyApp"));
const pages = {
  overview: lazy(() => import("./research/pages/Overview")),
  datasets: lazy(() => import("./research/pages/Datasets")),
  experiments: lazy(() => import("./research/pages/Experiments")),
  comparison: lazy(() => import("./research/pages/Comparison")),
  seeds: lazy(() => import("./research/pages/Seeds")),
  reproducibility: lazy(() => import("./research/pages/Reproducibility")),
  diagnostics: lazy(() => import("./research/pages/Diagnostics")),
  limitations: lazy(() => import("./research/pages/Limitations")),
};
const labels = [
  "Overview",
  "Datasets",
  "Experiments",
  "Model Comparison",
  "Seed Analysis",
  "Reproducibility",
  "CREST Diagnostics",
  "Research Limitations",
];
function locationRoute() {
  return window.location.hash.slice(2).split("/")[0] || "overview";
}
export function App() {
  const [route, setRoute] = useState(locationRoute);
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const update = () => {
      setRoute(locationRoute());
      setOpen(false);
    };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  useEffect(() => {
    document.title =
      TITLE +
      " — " +
      (labels[Object.keys(pages).indexOf(route)] ?? "Workspace");
  }, [route]);
  if (route === "workspace")
    return (
      <>
        <a className="workspace-return" href="#/overview">
          ← Read-only research terminal
        </a>
        <Suspense fallback={<p>Loading existing workspace…</p>}>
          <Legacy />
        </Suspense>
      </>
    );
  const Page = pages[route as keyof typeof pages];
  return (
    <div className="research">
      <a
        className="skip"
        href="#main"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main")?.focus();
        }}
      >
        Skip to research content
      </a>
      <aside
        className={"sidebar " + (open ? "is-open" : "")}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setOpen(false);
            menu.current?.focus();
          }
        }}
      >
        <a className="brand" href="#/overview" aria-label="GraphFin overview">
          <span>GRAPHFIN</span>
          <b aria-hidden="true">_</b>
        </a>
        <div className="nav-label eyebrow">RESEARCH WORKSPACE / 08</div>
        <nav aria-label="Research navigation">
          {Object.keys(pages).map((key, i) => (
            <a
              key={key}
              href={"#/" + key}
              aria-current={route === key ? "page" : undefined}
            >
              <span className="nav-icon" aria-hidden="true">
                {["◫", "▦", "≡", "▥", "⠿", "◎", "⌁", "⊞"][i]}
              </span>
              {labels[i]}
              <span className="nav-number">0{i + 1}</span>
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <p className="eyebrow">□ READ-ONLY RESEARCH</p>
          <p>
            Saved evidence.
            <br />
            Transparent limitations.
          </p>
          <a href="#/workspace">Existing analysis workspace ↗</a>
          <small>Operational tools · separate workspace</small>
        </div>
      </aside>
      {open && (
        <button
          className="nav-backdrop"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <div className="workspace">
        <header className="toolbar">
          <button
            className="menu-toggle"
            ref={menu}
            aria-label="Toggle navigation"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            ☰
          </button>
          <span className="breadcrumb">
            GRAPHFIN <span>/</span>{" "}
            {labels[Object.keys(pages).indexOf(route)] ?? "Unknown route"}
          </span>
          <span className="toolbar-mode">
            <i /> EVIDENCE TERMINAL
          </span>
        </header>
        <main id="main" tabIndex={-1} key={route}>
          <Suspense
            fallback={
              <div className="state" role="status">
                Loading research module…
              </div>
            }
          >
            {Page ? (
              <Page />
            ) : (
              <div className="state">
                <h1>Page not found</h1>
                <a href="#/overview">Return to overview</a>
              </div>
            )}
          </Suspense>
        </main>
        <footer className="research-footer">
          <span>{TITLE}</span>
          <span>RESEARCH, NOT FINANCIAL ADVICE / 008</span>
        </footer>
      </div>
    </div>
  );
}
export default App;
