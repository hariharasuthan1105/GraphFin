import{n as e}from"./rolldown-runtime-CbXtAM7H.js";import{n as t,r as n,y as r}from"./index-Dltpf0xr.js";import{t as i}from"./reportGenerator-XvWx0HDx.js";import{a,c as o,r as s,s as c}from"./ui-IUoXL2Xz.js";import{t as l}from"./sessionMetadata-2_5Fcnil.js";import{t as u}from"./DatasetReportDownload-Blp4b2df.js";var d=n(),f=e(r(),1),p=e=>e.replace(/[&<>]/g,e=>({"&":`&amp;`,"<":`&lt;`,">":`&gt;`})[e]);function m(){let{activeSession:e,loadBenchmarkSample:n,backendModel:r}=t(),[m,h]=(0,f.useState)(null),[g,_]=(0,f.useState)(null),v=g?.session===e?g.url:null;return(0,f.useEffect)(()=>()=>{g&&URL.revokeObjectURL(g.url)},[g]),(0,d.jsxs)(`div`,{className:`research-page reports-page`,children:[(0,d.jsx)(s,{index:`11`,title:`Audit reports & evidence downloads`,children:`Download verified research PDF reports for benchmark datasets and export structured audit packages from your interactive analysis session.`}),(0,d.jsx)(o,{}),m&&(0,d.jsxs)(`div`,{style:{background:`#171719`,color:`#ffffff`,border:`1px solid #b44a50`,borderRadius:`4px`,padding:`10px 14px`,marginBottom:`16px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`12px`},children:[`✓ `,m]}),e&&(0,d.jsx)(c,{title:`PDF document preview`,tag:`GENERATED FROM ACTIVE RESULTS`,children:(0,d.jsxs)(`div`,{className:`panel-body`,children:[(0,d.jsx)(`button`,{onClick:()=>{let t=i(e,e.backendModel||r,!1);_({url:URL.createObjectURL(t.output(`blob`)),session:e})},children:`Generate PDF preview`}),v&&(0,d.jsxs)(d.Fragment,{children:[(0,d.jsx)(`p`,{children:(0,d.jsx)(`a`,{href:v,target:`_blank`,rel:`noreferrer`,children:`Open PDF in a new tab ↗`})}),(0,d.jsx)(`iframe`,{title:`Active analysis PDF preview`,src:v,style:{width:`100%`,height:560,border:0}})]})]})}),(0,d.jsx)(c,{title:`Interactive Analysis Audit Report`,tag:`SESSION EXPORT`,children:(0,d.jsx)(`div`,{className:`panel-body`,children:e?(0,d.jsxs)(`div`,{children:[(0,d.jsxs)(`div`,{style:{display:`flex`,justifyContent:`space-between`,alignItems:`center`,flexWrap:`wrap`,gap:`10px`,marginBottom:`16px`},children:[(0,d.jsxs)(`div`,{children:[(0,d.jsxs)(`h3`,{style:{margin:`0 0 4px 0`,fontSize:`14px`,color:`#f8fafc`},children:[`Active Dataset: `,e.summary.datasetName]}),(0,d.jsxs)(`span`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,color:`#94a3b8`},children:[e.summary.uniqueAccounts,` accounts ·`,` `,e.summary.totalTransactions,` transactions ·`,` `,e.summary.suspiciousAccountCount,` anomalies`]})]}),(0,d.jsxs)(`span`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`10px`,color:`#f5f5f5`,padding:`3px 8px`,background:`#171719`,border:`1px solid #303034`,borderRadius:`3px`},children:[(0,d.jsx)(`b`,{style:{color:`#c04b52`},children:`●`}),` AUDIT READY`]})]}),(0,d.jsx)(`p`,{style:{fontSize:`12px`,color:`#94a3b8`,lineHeight:1.5,margin:`0 0 16px 0`},children:`Export complete anomaly rankings, network metrics, detected pattern motifs, and counterparty relationships in standard structured formats.`}),(0,d.jsxs)(`div`,{style:{display:`flex`,gap:`10px`,flexWrap:`wrap`,alignItems:`center`},children:[(0,d.jsx)(`button`,{type:`button`,onClick:()=>{i(e,e.backendModel||r),h(`Institutional PDF Audit Report generated and downloaded.`),setTimeout(()=>h(null),3e3)},style:{background:`#842d35`,color:`#ffffff`,border:`1px solid #b44a50`,padding:`8px 16px`,borderRadius:`4px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,fontWeight:600,cursor:`pointer`,display:`inline-flex`,alignItems:`center`,gap:`6px`},children:`📄 Download Audit Report (PDF)`}),(0,d.jsx)(`button`,{type:`button`,onClick:()=>{if(!e)return;let t=`data:text/json;charset=utf-8,`+encodeURIComponent(JSON.stringify({audit_metadata:{title:`GraphFin Financial Network Anomaly Audit Report`,generator:`GraphFin In-Browser Deterministic Analysis Engine v2.1`,timestamp:e.summary.processedAt,dataset_name:e.summary.datasetName,file_size_bytes:e.summary.fileSizeBytes},network_summary:l(e.summary),flagged_anomalies:e.topAnomalies,accounts_profiled:e.accounts.map(e=>({account_id:e.id,anomaly_score:e.anomalyScore,in_degree:e.inDegree,out_degree:e.outDegree,net_flow_volume:e.netFlow,detected_patterns:e.patterns}))},null,2)),n=document.createElement(`a`);n.setAttribute(`href`,t),n.setAttribute(`download`,`graphfin_audit_report_${e.summary.datasetName.replace(/\.[^/.]+$/,``)}.json`),document.body.appendChild(n),n.click(),n.remove(),h(`JSON audit package successfully exported.`),setTimeout(()=>h(null),3e3)},style:{background:`#171719`,color:`#f5f5f5`,border:`1px solid #303034`,padding:`8px 16px`,borderRadius:`4px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,fontWeight:600,cursor:`pointer`},children:`📥 Export JSON Audit Package`}),(0,d.jsx)(`button`,{type:`button`,onClick:()=>{if(!e)return;let t=[`rank`,`account_id`,`anomaly_score`,`in_degree`,`out_degree`,`total_sent`,`total_received`,`net_flow`,`patterns`].join(`,`),n=e.accounts.sort((e,t)=>t.anomalyScore-e.anomalyScore).map((e,t)=>[t+1,`"${e.id}"`,e.anomalyScore.toFixed(4),e.inDegree,e.outDegree,e.totalSent.toFixed(2),e.totalReceived.toFixed(2),e.netFlow.toFixed(2),`"${e.patterns.join(`;`)}"`].join(`,`)),r=`data:text/csv;charset=utf-8,`+encodeURIComponent([t,...n].join(`
`)),i=document.createElement(`a`);i.setAttribute(`href`,r),i.setAttribute(`download`,`graphfin_anomalies_${e.summary.datasetName.replace(/\.[^/.]+$/,``)}.csv`),document.body.appendChild(i),i.click(),i.remove(),h(`CSV anomaly ranking exported.`),setTimeout(()=>h(null),3e3)},style:{background:`#171719`,color:`#f5f5f5`,border:`1px solid #303034`,padding:`8px 16px`,borderRadius:`4px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,cursor:`pointer`},children:`📥 Export CSV Anomaly Rankings`}),(0,d.jsx)(`button`,{type:`button`,onClick:()=>{if(!e)return;let t=window.open(``,`_blank`);if(!t)return;let n=`
      <!DOCTYPE html>
      <html>
      <head>
        <title>GraphFin Executive Audit Report - ${p(e.summary.datasetName)}</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 40px; color: #1e293b; line-height: 1.5; }
          h1 { font-size: 20px; border-bottom: 2px solid #0f172a; padding-bottom: 8px; margin-bottom: 4px; }
          .subtitle { color: #64748b; font-size: 12px; margin-bottom: 24px; font-family: monospace; }
          .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
          .kpi-card { border: 1px solid #cbd5e1; padding: 12px; border-radius: 4px; }
          .kpi-val { font-size: 18px; font-weight: 700; color: #0f172a; }
          .kpi-label { font-size: 11px; text-transform: uppercase; color: #64748b; margin-top: 4px; }
          table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 12px; }
          th { text-align: left; padding: 8px; border-bottom: 2px solid #cbd5e1; background: #f8fafc; font-family: monospace; }
          td { padding: 8px; border-bottom: 1px solid #e2e8f0; font-family: monospace; }
          .disclaimer { margin-top: 32px; border-top: 1px solid #cbd5e1; padding-top: 12px; font-size: 11px; color: #64748b; }
        </style>
      </head>
      <body>
        <h1>GraphFin — Transaction Network Anomaly Audit Report</h1>
        <div class="subtitle">DATASET: ${p(e.summary.datasetName)} · PROCESSED: ${e.summary.processedAt}</div>
        
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-val">${e.summary.uniqueAccounts.toLocaleString()}</div>
            <div class="kpi-label">Accounts Profiled</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val">${e.summary.totalTransactions.toLocaleString()}</div>
            <div class="kpi-label">Transactions Parsed</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val">${e.summary.currency===`INR`?`₹`:e.summary.currency?e.summary.currency+` `:`Unknown `}${e.summary.totalVolume.toLocaleString(`en-US`,{maximumFractionDigits:2})}</div>
            <div class="kpi-label">Total Transfer Volume</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val" style="color: #e11d48;">${e.summary.suspiciousAccountCount}</div>
            <div class="kpi-label">Flagged Anomalies</div>
          </div>
        </div>

        <h2>Top Flagged Accounts & Anomaly Indicators</h2>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Account ID</th>
              <th>Score</th>
              <th>In/Out Deg</th>
              <th>Net Flow</th>
              <th>Topological Patterns</th>
            </tr>
          </thead>
          <tbody>
            ${e.topAnomalies.slice(0,15).map((t,n)=>`
              <tr>
                <td>${n+1}</td>
                <td><strong>${p(t.id)}</strong></td>
                <td style="color: ${t.anomalyScore>=.7?`#e11d48`:`#d97706`};">${t.anomalyScore.toFixed(3)}</td>
                <td>${t.inDegree} in / ${t.outDegree} out</td>
                <td>${t.netFlow<0?`-`:`+`}${e.summary.currency===`INR`?`₹`:e.summary.currency?e.summary.currency+` `:`Unknown `}${Math.abs(t.netFlow).toLocaleString()}</td>
                <td>${t.patterns.join(`, `)||`Elevated Degree`}</td>
              </tr>
            `).join(``)}
          </tbody>
        </table>

        <div class="disclaimer">
          <strong>Methodology Disclosure:</strong> Anomaly rankings are derived from deterministic topological and transaction flow metrics (in/out degree asymmetry, volume outliers, directed fan-in/fan-out, and cycle participation). These metrics indicate structural network anomalies and do not constitute legal determinations of financial misconduct.
        </div>
      </body>
      </html>
    `;t.document.write(n),t.document.close(),t.focus(),setTimeout(()=>t.print(),250)},style:{background:`#171719`,color:`#f5f5f5`,border:`1px solid #303034`,padding:`8px 16px`,borderRadius:`4px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,cursor:`pointer`},children:`🖨️ Printable Executive Summary`})]})]}):(0,d.jsxs)(`div`,{style:{textAlign:`center`,padding:`16px 0`},children:[(0,d.jsx)(`p`,{style:{fontSize:`12px`,color:`#94a3b8`,margin:`0 0 12px 0`},children:`No active session dataset loaded. Load the synthetic benchmark sample or upload a transaction file to generate an audit report.`}),(0,d.jsx)(`button`,{type:`button`,onClick:n,style:{background:`#b44a50`,color:`#ffffff`,border:`1px solid #842d35`,padding:`6px 14px`,borderRadius:`4px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,fontWeight:600,cursor:`pointer`},children:`✦ Load Benchmark Sample Dataset`})]})})}),(0,d.jsx)(c,{title:`Historical Research Dataset Reports (PDF)`,tag:`PEER EVIDENCE`,children:(0,d.jsxs)(`div`,{className:`panel-body`,children:[(0,d.jsx)(`p`,{style:{fontSize:`12px`,color:`#94a3b8`,lineHeight:1.6,margin:`0 0 16px 0`},children:`Download official research audit documents for the historical benchmark datasets. Reports include verified record counts, label provenance status, cross-dataset limitations, and cryptographic checksums.`}),(0,d.jsxs)(`div`,{style:{display:`grid`,gridTemplateColumns:`repeat(auto-fit, minmax(280px, 1fr))`,gap:`12px`},children:[(0,d.jsxs)(`div`,{style:{background:`#08090d`,border:`1px solid #1a1e28`,borderRadius:`4px`,padding:`14px`},children:[(0,d.jsx)(`div`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`12px`,fontWeight:700,color:`#f8fafc`,marginBottom:`4px`},children:`IBM AML 5k Dataset Report`}),(0,d.jsx)(`div`,{style:{fontSize:`11px`,color:`#94a3b8`,marginBottom:`12px`,fontFamily:`IBM Plex Mono, monospace`},children:`5,000 accounts · 31,463 transfers · 20 positives`}),(0,d.jsx)(u,{datasetId:`ibm-5k`})]}),(0,d.jsxs)(`div`,{style:{background:`#08090d`,border:`1px solid #1a1e28`,borderRadius:`4px`,padding:`14px`},children:[(0,d.jsx)(`div`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`12px`,fontWeight:700,color:`#f8fafc`,marginBottom:`4px`},children:`IBM AML 50k Dataset Report`}),(0,d.jsx)(`div`,{style:{fontSize:`11px`,color:`#94a3b8`,marginBottom:`12px`,fontFamily:`IBM Plex Mono, monospace`},children:`49,992 accounts · 353,850 transfers · 249 positives`}),(0,d.jsx)(u,{datasetId:`ibm-50k`})]}),(0,d.jsxs)(`div`,{style:{background:`#08090d`,border:`1px solid #1a1e28`,borderRadius:`4px`,padding:`14px`},children:[(0,d.jsx)(`div`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`12px`,fontWeight:700,color:`#f8fafc`,marginBottom:`4px`},children:`PaySim Anomaly Audit Report`}),(0,d.jsx)(`div`,{style:{fontSize:`11px`,color:`#94a3b8`,marginBottom:`12px`,fontFamily:`IBM Plex Mono, monospace`},children:`547,686 accounts · 1,832 label disagreements`}),(0,d.jsx)(u,{datasetId:`paysim`})]})]})]})}),(0,d.jsxs)(a,{children:[(0,d.jsx)(`strong`,{style:{display:`block`,marginBottom:`4px`},children:`Audit Integrity Guarantee`}),(0,d.jsx)(`p`,{style:{margin:0,fontSize:`12px`,lineHeight:1.5},children:`All exported audit reports adhere strictly to reproducible schemas. Interactive analysis exports are derived on-the-fly from verified client-side graph structures, ensuring zero data leakage to external networks.`})]})]})}export{m as default};