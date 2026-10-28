import { useRef, type CSSProperties } from 'react';
import { TITLE } from './state';
import { useSession } from './sessionContext';
import artwork from '../assets/portal-reference.webp';

function ActionIcon({ kind }: { kind: 'dataset' | 'graph' | 'research' | 'reports' }) {
  return <svg viewBox="0 0 28 28" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
    {kind === 'dataset' && <><ellipse cx="14" cy="6" rx="9" ry="3.5" /><path d="M5 6v16c0 5 18 5 18 0V6M5 14c0 5 18 5 18 0M5 21c0 5 18 5 18 0" /></>}
    {kind === 'graph' && <><path d="m13 6-7 14m10-14 7 14M7 23h14"/><circle cx="14" cy="4" r="3"/><circle cx="4" cy="23" r="3"/><circle cx="24" cy="23" r="3"/></>}
    {kind === 'research' && <><path d="M8 3h12l4 4v17H8zM4 7v20h15M19 3v6h5M12 13h8M12 17h8M12 21h5"/></>}
    {kind === 'reports' && <><path d="M4 15h4v11H4zM12 9h4v17h-4zM20 3h4v23h-4z" fill="currentColor" stroke="none"/></>}
  </svg>;
}

export default function Cover() {
  const cover = useRef<HTMLElement>(null);
  const { setAppMode } = useSession();
  return <div className="research cover-root">
    <section className="cover" ref={cover} style={{ '--portal': `url(${artwork})` } as CSSProperties}
      onPointerMove={event => {
        if (event.pointerType !== 'mouse' || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        cover.current?.style.setProperty('--drift-x', `${(event.clientX / innerWidth - .5) * 10}px`);
        cover.current?.style.setProperty('--drift-y', `${(event.clientY / innerHeight - .5) * 6}px`);
      }} onPointerLeave={() => {
        cover.current?.style.setProperty('--drift-x', '0px');
        cover.current?.style.setProperty('--drift-y', '0px');
      }}>
      <div className="cover-art" aria-hidden="true" />
      <div className="cover-particles" aria-hidden="true" />
      <nav className="cover-nav" aria-label="Cover navigation">
        <a className="cover-edition" href="#/" aria-label="GraphFin home">GRAPHFIN<span>_</span></a>
        <div><a href="#/" aria-current="page">Home</a><a href="#/experiments" onClick={() => setAppMode('research')}>Research</a><a href="#/reproducibility">Documentation</a><a href="#/limitations">About</a></div>
        <a className="cover-enter" href="#/overview" aria-label="Get Started — Enter GraphFin">Get Started <span aria-hidden="true">→</span></a>
      </nav>
      <header className="cover-heading">
        <h1>GRAPHFIN<span>_</span></h1>
        <p className="cover-title">{TITLE}</p>
        <p className="cover-tagline">Detect <span>✦</span> Investigate <span>✦</span> Understand</p>
      </header>
      <div className="cover-caption"><p>Financial<br />networks<br />hide<br />patterns.<br />We<br />reveal<br />them.</p><i /></div>
      <div className="cover-index"><span>Graph Analysis</span><span>ML Detection</span><span>Network Forensics</span><span>Risk Visualization</span><span>Research Evidence</span></div>
      <div className="cover-principles"><span>Real data</span><span>Real algorithms</span><span>Real insights</span><span>Academic research</span></div>
      <div className="cover-bottom">
        <div className="cover-actions">
          <div><a className="primary" href="#/analyze" onClick={() => setAppMode('interactive')}><ActionIcon kind="dataset" /> Upload Dataset</a><p>Transaction Network Analysis</p></div>
          <div><a href="#/graph"><ActionIcon kind="graph" /> Explore Graph</a><p>ML Anomaly Detection</p></div>
          <div><a href="#/experiments" onClick={() => setAppMode('research')}><ActionIcon kind="research" /> Research Evidence</a><p>Graph Visualization</p></div>
          <div><a href="#/reports"><ActionIcon kind="reports" /> View Reports</a><p>Comprehensive Reports</p></div>
        </div>
        <button className="scroll-explore" onClick={() => document.getElementById('explore')?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })}><span className="scroll-mouse" aria-hidden="true" /><span>Scroll to Explore</span><span className="scroll-chevron" aria-hidden="true">⌄</span></button>
      </div>
    </section>
    <section id="explore" className="cover-explore">
      <span className="eyebrow">01 / ENTER THE WORKSPACE</span>
      <h2>Every transaction tells a story.<br />See how they connect.</h2>
      <p>Explore financial networks, investigate unusual account behavior, and inspect the evidence behind the results.</p>
      <div className="cover-paths">
        <a href="#/overview"><span className="eyebrow">01 / OVERVIEW</span><h3>Your intelligence workspace ↗</h3><p>Actual session metrics, clear engine status, and one connected workflow.</p></a>
        <a href="#/analyze"><span className="eyebrow">02 / ANALYSIS</span><h3>Bring your transaction data ↗</h3><p>CSV, TSV, or JSON. Local analysis with explicit consent before any backend upload.</p></a>
        <a href="#/experiments" onClick={() => setAppMode('research')}><span className="eyebrow">03 / EVIDENCE</span><h3>Inspect the research ↗</h3><p>Recorded experiments, reproducibility metadata, and documented limitations.</p></a>
      </div>
    </section>
  </div>;
}
