import React, { useState, useRef } from 'react'

// POST a JSON body and consume the SSE response, invoking onEvent for each `data:` frame.
async function streamPost(url, body, onEvent) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try { msg = (await res.json()).error || msg } catch {}
    throw new Error(msg)
  }
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n\n')) !== -1) {
      const frame = buf.slice(0, i); buf = buf.slice(i + 2)
      const line = frame.split('\n').find((l) => l.startsWith('data:'))
      if (line) { try { onEvent(JSON.parse(line.slice(5).trim())) } catch {} }
    }
  }
}

export default function App() {
  const [phase, setPhase] = useState('form') // form | discovering | review | building | done
  const [product, setProduct] = useState({ kind: 'url', ref: '', notes: '' })
  const [meta, setMeta] = useState({ org: '', author: '', date_label: '' })
  const [log, setLog] = useState([])
  const [profile, setProfile] = useState(null)
  const [ranked, setRanked] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [html, setHtml] = useState('')
  const [report, setReport] = useState(null)
  const logRef = useRef(null)

  const addLog = (e) => setLog((L) => {
    const next = [...L, e]
    queueMicrotask(() => logRef.current?.scrollTo(0, 1e9))
    return next
  })

  async function runDiscover() {
    if (!product.ref.trim()) return
    setPhase('discovering'); setLog([]); setProfile(null); setRanked([])
    try {
      await streamPost('/api/discover', { product }, (e) => {
        if (e.type === 'progress') addLog(e)
        else if (e.type === 'error') addLog({ phase: 'Error', message: e.message, err: true })
        else if (e.type === 'result') {
          setProfile(e.productProfile)
          setRanked(e.ranked || [])
          setSelected(new Set((e.top2 || []).map((c) => c.name)))
          setPhase('review')
        }
      })
    } catch (err) {
      addLog({ phase: 'Error', message: String(err.message || err), err: true }); setPhase('form')
    }
  }

  async function runBuild() {
    const competitors = ranked.filter((r) => selected.has(r.name)).map((r) => ({ name: r.name, url: r.url }))
    if (!competitors.length) return
    setPhase('building')
    try {
      await streamPost('/api/build', { productProfile: profile, competitors, meta }, (e) => {
        if (e.type === 'progress') addLog(e)
        else if (e.type === 'error') addLog({ phase: 'Error', message: e.message, err: true })
        else if (e.type === 'result') { setHtml(e.html || ''); setReport(e.report); setPhase('done') }
      })
    } catch (err) {
      addLog({ phase: 'Error', message: String(err.message || err), err: true }); setPhase('review')
    }
  }

  const toggle = (name) => setSelected((s) => {
    const n = new Set(s); n.has(name) ? n.delete(name) : n.add(name); return n
  })

  const download = () => {
    const slug = (profile?.name || 'product').toLowerCase().replace(/[^a-z0-9]+/g, '-')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
    a.download = `${slug}-comparison.html`; a.click()
  }

  const busy = phase === 'discovering' || phase === 'building'

  return (
    <div className="wrap">
      <header className="hero">
        <div className="kick">● Competitive Intelligence</div>
        <h1>Competitor Agent</h1>
        <p>Give it your product. It finds the top 2 market leaders, researches them, and builds the briefing.</p>
      </header>

      <div className="card">
        <h2>1 · Your product</h2>
        <div className="row">
          <div>
            <label>Input type</label>
            <select value={product.kind} onChange={(e) => setProduct({ ...product, kind: e.target.value })}>
              <option value="url">Website / URL</option>
              <option value="repo">Local repo path</option>
              <option value="doc">Local doc path</option>
              <option value="text">Pasted description</option>
            </select>
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <label>{product.kind === 'text' ? 'Describe the product' : 'Path or URL'}</label>
            <input value={product.ref} placeholder={product.kind === 'url' ? 'https://yourproduct.com' : product.kind === 'text' ? 'What it does, who it’s for…' : '/path/to/repo'}
              onChange={(e) => setProduct({ ...product, ref: e.target.value })} />
          </div>
        </div>
        <label>Notes for the analyst (optional)</label>
        <textarea value={product.notes} onChange={(e) => setProduct({ ...product, notes: e.target.value })}
          placeholder="Anything the agent should know about your product or who you compete with." />
        <div className="row" style={{ marginTop: 4 }}>
          <div><label>Org / brand</label><input value={meta.org} onChange={(e) => setMeta({ ...meta, org: e.target.value })} placeholder="Acme" /></div>
          <div><label>Author</label><input value={meta.author} onChange={(e) => setMeta({ ...meta, author: e.target.value })} placeholder="Your name" /></div>
          <div><label>Date label</label><input value={meta.date_label} onChange={(e) => setMeta({ ...meta, date_label: e.target.value })} placeholder="June 2026 · Internal" /></div>
        </div>
        <div className="actions">
          <button onClick={runDiscover} disabled={busy || !product.ref.trim()}>
            {phase === 'discovering' ? <><span className="spin" /> &nbsp;Discovering…</> : 'Find competitors →'}
          </button>
          {profile && <span style={{ color: 'var(--muted)', fontSize: 13 }}>Understood: <b>{profile.name}</b> — {profile.category}</span>}
        </div>
      </div>

      {(busy || log.length > 0) && (
        <div className="card">
          <h2>Progress</h2>
          <div className="log" ref={logRef}>
            {log.map((e, i) => (
              <div key={i} className={e.err ? 'err' : ''}>
                <span className="phase">[{e.phase}]</span> {e.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {phase === 'review' && (
        <div className="card">
          <h2>2 · Approve the rivals <span className="pill">{selected.size} selected</span></h2>
          <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 0 }}>
            Ranked by market leadership. The top 2 are pre-selected — swap if you’d rather compare against others.
          </p>
          {ranked.map((r) => (
            <label className="cand" key={r.name} style={{ cursor: 'pointer' }}>
              <input type="checkbox" checked={selected.has(r.name)} onChange={() => toggle(r.name)} />
              <div>
                <div><b>{r.name}</b> {typeof r.leadership_score === 'number' && <span className="pill num">{Math.round(r.leadership_score)}</span>}</div>
                <div className="why">{r.why}</div>
                {r.url && <a href={r.url} target="_blank" rel="noreferrer">{r.url}</a>}
              </div>
            </label>
          ))}
          <div className="actions">
            <button onClick={runBuild} disabled={!selected.size}>Build report ({selected.size}) →</button>
            <button className="secondary" onClick={() => setPhase('form')}>Start over</button>
          </div>
        </div>
      )}

      {phase === 'done' && (
        <div className="card">
          <h2>3 · Report</h2>
          {report && (
            <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 0 }}>
              {report.rows} capabilities · vs {report.competitors?.join(', ')} · {report.sources} sources
              {report.claims_downgraded?.length ? ` · ${report.claims_downgraded.length} claim(s) downgraded to unknown` : ''}
            </p>
          )}
          <div className="actions" style={{ marginTop: 0, marginBottom: 14 }}>
            <button onClick={download}>Download HTML</button>
            <button className="secondary" onClick={() => setPhase('form')}>New analysis</button>
          </div>
          <iframe className="report" title="report" srcDoc={html} />
        </div>
      )}
    </div>
  )
}
