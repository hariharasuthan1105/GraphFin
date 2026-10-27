import{_ as e,n as t,t as n,v as r}from"./index-CMqupXlF.js";import{a as i,c as a,r as o,s}from"./ui-BcXga9eE.js";import{t as c}from"./DatasetReportDownload-Ot992Zt2.js";var l=r(e(),1),u=t();function d(){let{activeSession:e,loadBenchmarkSample:t}=n(),[r,d]=(0,l.useState)(null);return(0,u.jsxs)(`div`,{className:`research-page reports-page`,children:[(0,u.jsx)(o,{index:`11`,title:`Audit reports & evidence downloads`,children:`Download verified research PDF reports for benchmark datasets and export structured audit packages from your interactive analysis session.`}),(0,u.jsx)(a,{}),r&&(0,u.jsxs)(`div`,{style:{background:`#062822`,color:`#2dd4bf`,border:`1px solid #134e48`,borderRadius:`4px`,padding:`10px 14px`,marginBottom:`16px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`12px`},children:[`✓ `,r]}),(0,u.jsx)(s,{title:`Interactive Analysis Audit Report`,tag:`SESSION EXPORT`,children:(0,u.jsx)(`div`,{className:`panel-body`,children:e?(0,u.jsxs)(`div`,{children:[(0,u.jsxs)(`div`,{style:{display:`flex`,justifyContent:`space-between`,alignItems:`center`,flexWrap:`wrap`,gap:`10px`,marginBottom:`16px`},children:[(0,u.jsxs)(`div`,{children:[(0,u.jsxs)(`h3`,{style:{margin:`0 0 4px 0`,fontSize:`14px`,color:`#f8fafc`},children:[`Active Dataset: `,e.summary.datasetName]}),(0,u.jsxs)(`span`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,color:`#94a3b8`},children:[e.summary.uniqueAccounts,` accounts ·`,` `,e.summary.totalTransactions,` transactions ·`,` `,e.summary.suspiciousAccountCount,` anomalies`]})]}),(0,u.jsx)(`span`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`10px`,color:`#38bdf8`,padding:`3px 8px`,background:`#0c1f30`,border:`1px solid #0369a1`,borderRadius:`3px`},children:`AUDIT READY`})]}),(0,u.jsx)(`p`,{style:{fontSize:`12px`,color:`#94a3b8`,lineHeight:1.5,margin:`0 0 16px 0`},children:`Export complete anomaly rankings, network metrics, detected pattern motifs, and counterparty relationships in standard structured formats.`}),(0,u.jsxs)(`div`,{style:{display:`flex`,gap:`10px`,flexWrap:`wrap`},children:[(0,u.jsx)(`button`,{type:`button`,onClick:()=>{if(!e)return;let t=`data:text/json;charset=utf-8,`+encodeURIComponent(JSON.stringify({audit_metadata:{title:`GraphFin Financial Network Anomaly Audit Report`,generator:`GraphFin In-Browser Deterministic Analysis Engine v2.0`,timestamp:e.summary.processedAt,dataset_name:e.summary.datasetName,file_size_bytes:e.summary.fileSizeBytes},network_summary:e.summary,flagged_anomalies:e.topAnomalies,accounts_profiled:e.accounts.map(e=>({account_id:e.id,anomaly_score:e.anomalyScore,in_degree:e.inDegree,out_degree:e.outDegree,net_flow_volume:e.netFlow,detected_patterns:e.patterns}))},null,2)),n=document.createElement(`a`);n.setAttribute(`href`,t),n.setAttribute(`download`,`graphfin_audit_report_${e.summary.datasetName.replace(/\.[^/.]+$/,``)}.json`),document.body.appendChild(n),n.click(),n.remove(),d(`JSON audit package successfully exported.`),setTimeout(()=>d(null),3e3)},style:{background:`#0284c7`,color:`#ffffff`,border:`none`,padding:`8px 16px`,borderRadius:`4px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,fontWeight:600,cursor:`pointer`},children:`📥 Export JSON Audit Package`}),(0,u.jsx)(`button`,{type:`button`,onClick:()=>{if(!e)return;let t=[`rank`,`account_id`,`anomaly_score`,`in_degree`,`out_degree`,`total_sent`,`total_received`,`net_flow`,`patterns`].join(`,`),n=e.accounts.sort((e,t)=>t.anomalyScore-e.anomalyScore).map((e,t)=>[t+1,`"${e.id}"`,e.anomalyScore.toFixed(4),e.inDegree,e.outDegree,e.totalSent.toFixed(2),e.totalReceived.toFixed(2),e.netFlow.toFixed(2),`"${e.patterns.join(`;`)}"`].join(`,`)),r=`data:text/csv;charset=utf-8,`+encodeURIComponent([t,...n].join(`
`)),i=document.createElement(`a`);i.setAttribute(`href`,r),i.setAttribute(`download`,`graphfin_anomalies_${e.summary.datasetName.replace(/\.[^/.]+$/,``)}.csv`),document.body.appendChild(i),i.click(),i.remove(),d(`CSV anomaly ranking exported.`),setTimeout(()=>d(null),3e3)},style:{background:`#161b26`,color:`#38bdf8`,border:`1px solid #283144`,padding:`8px 16px`,borderRadius:`4px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,cursor:`pointer`},children:`📥 Export CSV Anomaly Rankings`}),(0,u.jsx)(`button`,{type:`button`,onClick:()=>{if(!e)return;let t=window.open(``,`_blank`);if(!t)return;let n=`
      <!DOCTYPE html>
      <html>
      <head>
        <title>GraphFin Executive Audit Report - ${e.summary.datasetName}</title>
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
        <div class="subtitle">DATASET: ${e.summary.datasetName} · PROCESSED: ${e.summary.processedAt}</div>
        
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
            <div class="kpi-val">$${e.summary.totalVolume.toLocaleString(`en-US`,{maximumFractionDigits:2})}</div>
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
            ${e.topAnomalies.slice(0,15).map((e,t)=>`
              <tr>
                <td>${t+1}</td>
                <td><strong>${e.id}</strong></td>
                <td style="color: ${e.anomalyScore>=.7?`#e11d48`:`#d97706`};">${e.anomalyScore.toFixed(3)}</td>
                <td>${e.inDegree} in / ${e.outDegree} out</td>
                <td>${e.netFlow<0?`-`:`+`}$${Math.abs(e.netFlow).toLocaleString()}</td>
                <td>${e.patterns.join(`, `)||`Elevated Degree`}</td>
              </tr>
            `).join(``)}
          </tbody>
        </table>

        <div class="disclaimer">
          <strong>Methodology Disclosure:</strong> Anomaly rankings are derived from deterministic topological and transaction flow metrics (in/out degree asymmetry, volume outliers, directed fan-in/fan-out, and cycle participation). These metrics indicate structural network anomalies and do not constitute legal determinations of financial misconduct.
        </div>
      </body>
      </html>
    `;t.document.write(n),t.document.close(),t.focus(),setTimeout(()=>t.print(),250)},style:{background:`#161b26`,color:`#e2e8f0`,border:`1px solid #283144`,padding:`8px 16px`,borderRadius:`4px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,cursor:`pointer`},children:`🖨️ Printable Executive Summary`})]})]}):(0,u.jsxs)(`div`,{style:{textAlign:`center`,padding:`16px 0`},children:[(0,u.jsx)(`p`,{style:{fontSize:`12px`,color:`#94a3b8`,margin:`0 0 12px 0`},children:`No active session dataset loaded. Load the synthetic benchmark sample or upload a transaction file to generate an audit report.`}),(0,u.jsx)(`button`,{type:`button`,onClick:t,style:{background:`#0284c7`,color:`#ffffff`,border:`none`,padding:`6px 14px`,borderRadius:`4px`,fontFamily:`IBM Plex Mono, monospace`,fontSize:`11px`,fontWeight:600,cursor:`pointer`},children:`✦ Load Benchmark Sample Dataset`})]})})}),(0,u.jsx)(s,{title:`Historical Research Dataset Reports (PDF)`,tag:`PEER EVIDENCE`,children:(0,u.jsxs)(`div`,{className:`panel-body`,children:[(0,u.jsx)(`p`,{style:{fontSize:`12px`,color:`#94a3b8`,lineHeight:1.6,margin:`0 0 16px 0`},children:`Download official research audit documents for the historical benchmark datasets. Reports include verified record counts, label provenance status, cross-dataset limitations, and cryptographic checksums.`}),(0,u.jsxs)(`div`,{style:{display:`grid`,gridTemplateColumns:`repeat(auto-fit, minmax(280px, 1fr))`,gap:`12px`},children:[(0,u.jsxs)(`div`,{style:{background:`#08090d`,border:`1px solid #1a1e28`,borderRadius:`4px`,padding:`14px`},children:[(0,u.jsx)(`div`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`12px`,fontWeight:700,color:`#f8fafc`,marginBottom:`4px`},children:`IBM AML 5k Dataset Report`}),(0,u.jsx)(`div`,{style:{fontSize:`11px`,color:`#94a3b8`,marginBottom:`12px`,fontFamily:`IBM Plex Mono, monospace`},children:`5,000 accounts · 31,463 transfers · 20 positives`}),(0,u.jsx)(c,{datasetId:`ibm-5k`})]}),(0,u.jsxs)(`div`,{style:{background:`#08090d`,border:`1px solid #1a1e28`,borderRadius:`4px`,padding:`14px`},children:[(0,u.jsx)(`div`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`12px`,fontWeight:700,color:`#f8fafc`,marginBottom:`4px`},children:`IBM AML 50k Dataset Report`}),(0,u.jsx)(`div`,{style:{fontSize:`11px`,color:`#94a3b8`,marginBottom:`12px`,fontFamily:`IBM Plex Mono, monospace`},children:`49,992 accounts · 353,850 transfers · 249 positives`}),(0,u.jsx)(c,{datasetId:`ibm-50k`})]}),(0,u.jsxs)(`div`,{style:{background:`#08090d`,border:`1px solid #1a1e28`,borderRadius:`4px`,padding:`14px`},children:[(0,u.jsx)(`div`,{style:{fontFamily:`IBM Plex Mono, monospace`,fontSize:`12px`,fontWeight:700,color:`#f8fafc`,marginBottom:`4px`},children:`PaySim Anomaly Audit Report`}),(0,u.jsx)(`div`,{style:{fontSize:`11px`,color:`#94a3b8`,marginBottom:`12px`,fontFamily:`IBM Plex Mono, monospace`},children:`547,686 accounts · 1,832 label disagreements`}),(0,u.jsx)(c,{datasetId:`paysim`})]})]})]})}),(0,u.jsxs)(i,{children:[(0,u.jsx)(`strong`,{style:{display:`block`,marginBottom:`4px`},children:`Audit Integrity Guarantee`}),(0,u.jsx)(`p`,{style:{margin:0,fontSize:`12px`,lineHeight:1.5},children:`All exported audit reports adhere strictly to reproducible schemas. Interactive analysis exports are derived on-the-fly from verified client-side graph structures, ensuring zero data leakage to external networks.`})]})]})}export{d as default};