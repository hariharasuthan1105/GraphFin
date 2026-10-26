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
  graph: lazy(() => import("./research/pages/GraphExplorer")),
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
  "Graph Explorer",
];

// Publicly accessible routes (Overview and Limitations)
const PUBLIC_ROUTES = new Set(["overview", "limitations"]);

interface SessionState {
  authenticated: boolean;
  role: string;
  user: string | null;
  csrf_token: string | null;
}

function locationRoute() {
  return window.location.hash.slice(2).split(/[/?]/)[0] || "overview";
}

export function App() {
  const [route, setRoute] = useState(locationRoute);
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLButtonElement>(null);

  // Examiner session management
  const [session, setSession] = useState<SessionState>({
    authenticated: false,
    role: "public",
    user: null,
    csrf_token: null,
  });
  const [checkingSession, setCheckingSession] = useState(true);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginUsername, setLoginUsername] = useState("examiner");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);

  const refreshSession = async () => {
    try {
      const res = await fetch("/api/auth/session", {
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        setSession(data);
      }
    } catch {
      // Offline or network error
    } finally {
      setCheckingSession(false);
    }
  };

  useEffect(() => {
    refreshSession();
  }, []);

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
      " - " +
      (labels[Object.keys(pages).indexOf(route)] ?? "Workspace");
  }, [route]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginBusy(true);
    setLoginError("");
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          username: loginUsername.trim(),
          password: loginPassword,
        }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        setLoginError(data?.message || "Invalid examiner username or password.");
        return;
      }
      setSession({
        authenticated: true,
        role: data.role || "examiner",
        user: data.user || loginUsername.trim(),
        csrf_token: data.csrf_token || null,
      });
      setShowLoginModal(false);
      setLoginPassword("");
    } catch {
      setLoginError("Failed to connect to authentication gateway.");
    } finally {
      setLoginBusy(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: {
          Accept: "application/json",
          ...(session.csrf_token ? { "X-CSRF-Token": session.csrf_token } : {}),
        },
      });
    } finally {
      setSession({
        authenticated: false,
        role: "public",
        user: null,
        csrf_token: null,
      });
      if (!PUBLIC_ROUTES.has(route)) {
        window.location.hash = "#/overview";
      }
    }
  };

  if (route === "workspace")
    return (
      <>
        <a className="workspace-return" href="#/overview">
          Read-only research terminal
        </a>
        <Suspense fallback={<p>Loading existing workspace.</p>}>
          <Legacy />
        </Suspense>
      </>
    );

  const Page = pages[route as keyof typeof pages];
  const isProtected = !PUBLIC_ROUTES.has(route);
  const requiresAuth = isProtected && !session.authenticated && !checkingSession;

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
          {Object.keys(pages).map((key, i) => {
            const protectedItem = !PUBLIC_ROUTES.has(key);
            return (
              <a
                key={key}
                href={"#/" + key}
                aria-current={route === key ? "page" : undefined}
                className={protectedItem && !session.authenticated ? "is-locked" : ""}
              >
                <span className="nav-icon" aria-hidden="true">
                  {protectedItem && !session.authenticated ? "[L]" : `0${i + 1}`}
                </span>
                {labels[i]}
                <span className="nav-number">
                  {protectedItem ? (session.authenticated ? "AUTH" : "LOCK") : "PUB"}
                </span>
              </a>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <p className="eyebrow">READ-ONLY RESEARCH</p>
          <p>
            Saved evidence.
            <br />
            Transparent limitations.
          </p>
          <div className="examiner-sidebar-status">
            {session.authenticated ? (
              <p className="eyebrow green">EXAMINER ACTIVE: {session.user}</p>
            ) : (
              <p className="eyebrow technical">PUBLIC VISITOR MODE</p>
            )}
          </div>
          <a href="#/workspace">Existing analysis workspace</a>
          <small>Operational tools in separate workspace</small>
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
            MENU
          </button>
          <span className="breadcrumb">
            GRAPHFIN <span>/</span>{" "}
            {labels[Object.keys(pages).indexOf(route)] ?? "Unknown route"}
          </span>
          <div className="toolbar-right-controls">
            {session.authenticated ? (
              <div className="examiner-badge-group">
                <span className="examiner-badge" title="Examiner authenticated session active">
                  <span className="auth-dot online" />
                  EXAMINER: {session.user}
                </span>
                <button
                  type="button"
                  className="examiner-logout-btn"
                  onClick={handleLogout}
                  title="Terminate examiner session"
                >
                  LOGOUT
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="examiner-login-btn"
                onClick={() => {
                  setLoginError("");
                  setShowLoginModal(true);
                }}
              >
                EXAMINER LOGIN
              </button>
            )}
            <span className="toolbar-mode">
              <i /> EVIDENCE TERMINAL
            </span>
          </div>
        </header>

        <main id="main" tabIndex={-1} key={route}>
          {requiresAuth ? (
            <div className="auth-gate-card">
              <div className="eyebrow red">EXAMINER AUTHENTICATION REQUIRED</div>
              <h2>Protected Research Section</h2>
              <p>
                Access to detailed dataset benchmarks, experimental comparisons,
                diagnostic provenance, and interactive graph exploration requires an active
                academic examiner session.
              </p>
              <p className="technical">
                Public visitors may explore the immutable Project Overview and Research Limitations.
                Academic evaluators may sign in below.
              </p>
              <button
                type="button"
                className="examiner-gate-btn"
                onClick={() => {
                  setLoginError("");
                  setShowLoginModal(true);
                }}
              >
                AUTHENTICATE AS EXAMINER
              </button>
            </div>
          ) : (
            <Suspense
              fallback={
                <div className="state" role="status">
                  Loading research module.
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
          )}
        </main>
        <footer className="research-footer">
          <span>{TITLE}</span>
          <span>RESEARCH, NOT FINANCIAL ADVICE / 008</span>
        </footer>
      </div>

      {showLoginModal && (
        <div
          className="auth-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="login-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowLoginModal(false);
          }}
        >
          <div className="auth-modal">
            <div className="eyebrow red">GRAPHFIN GATEWAY / SECURE ACCESS</div>
            <h2 id="login-title">Academic Examiner Sign-In</h2>
            <p className="auth-modal-desc">
              Authenticate to unlock protected research comparisons, diagnostics, and graph exploration.
            </p>
            {loginError && (
              <div className="auth-error-banner" role="alert">
                {loginError}
              </div>
            )}
            <form onSubmit={handleLogin}>
              <div className="auth-field">
                <label htmlFor="auth-username" className="auth-label">EXAMINER USERNAME</label>
                <input
                  id="auth-username"
                  type="text"
                  className="auth-input"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <div className="auth-field">
                <label htmlFor="auth-password" className="auth-label">EXAMINER PASSWORD</label>
                <input
                  id="auth-password"
                  type="password"
                  className="auth-input"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
              </div>
              <div className="auth-modal-actions">
                <button
                  type="button"
                  className="auth-btn-cancel"
                  onClick={() => setShowLoginModal(false)}
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  className="auth-btn-submit"
                  disabled={loginBusy}
                >
                  {loginBusy ? "AUTHENTICATING..." : "SIGN IN"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
