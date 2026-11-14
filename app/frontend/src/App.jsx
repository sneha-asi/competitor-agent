import React, { useState, useRef, useEffect } from 'react'

// POST a JSON body and consume the SSE response, invoking onEvent for each `data:` frame.
async function streamPost(url, body, onEvent) {
  const res = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
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

const KINDS = [
  { v: 'url', label: 'Website' }, { v: 'repo', label: 'Repo' },
  { v: 'doc', label: 'Doc' }, { v: 'text', label: 'Describe' },
]
const PLACEHOLDER = { url: 'https://yourproduct.com', repo: '/path/to/repo  or  https://github.com/org/repo (cloned locally)', doc: '/path/to/brief.md', text: 'What it does, who it’s for, the problem it solves…' }
const MODELS = [
  { v: 'claude-opus-4-8', label: 'Claude Opus 4.8 — most capable' },
  { v: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 — ~40% cheaper' },
  { v: 'claude-haiku-4-5', label: 'Claude Haiku 4.5 — fastest / cheapest' },
]

const Check = () => (<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m20 6-11 11L4 12" /></svg>)
const Gear = () => (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>)

function Stepper({ step, done }) {
  const steps = [{ n: 1, label: 'Product' }, { n: 2, label: 'Rivals' }, { n: 3, label: 'Report' }]
  return (
    <div className="steps">
      {steps.map((s, i) => {
        const isDone = s.n < step || (s.n === 3 && done)
        const cls = isDone ? 'step done' : s.n === step ? 'step active' : 'step'
        return (
          <React.Fragment key={s.n}>
            {i > 0 && <span className="sep" />}
            <span className={cls}><span className="dot">{isDone ? <Check /> : s.n}</span><span>{s.label}</span></span>
          </React.Fragment>
        )
      })}
    </div>
  )
}

export default function App() {
  const [phase, setPhase] = useState('form')
  const [product, setProduct] = useState({ kind: 'url', ref: '', notes: '' })
  const [meta, setMeta] = useState({ org: '', author: '', date_label: '' })
  const [log, setLog] = useState([])
  const [profile, setProfile] = useState(null)
  const [ranked, setRanked] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [html, setHtml] = useState('')
  const [report, setReport] = useState(null)
  const logRef = useRef(null)

  // settings
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [hasKey, setHasKey] = useState(null)
  const [model, setModel] = useState('claude-opus-4-8')
  const [keyInput, setKeyInput] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [keyMsg, setKeyMsg] = useState(null)

  useEffect(() => {
    fetch('/api/health').then((r) => r.json()).then((d) => { setHasKey(!!d.has_key); if (d.model) setModel(d.model) }).catch(() => setHasKey(false))
  }, [])

  const addLog = (e) => setLog((L) => { queueMicrotask(() => logRef.current?.scrollTo(0, 1e9)); return [...L, e] })
  const onError = (msg) => { addLog({ phase: 'Error', message: msg }); if (/ANTHROPIC_API_KEY/i.test(msg)) { setHasKey(false); setSettingsOpen(true) } }

  async function saveSettings() {
    setSaving(true); setKeyMsg(null)
    try {
      const res = await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: keyInput.trim(), model }) })
      const d = await res.json()
      if (!res.ok) { setKeyMsg({ ok: false, t: d.error || 'Could not save.' }); return }
      setHasKey(!!d.has_key); if (d.model) setModel(d.model)
      setKeyMsg({ ok: true, t: keyInput.trim() ? 'Key saved and verified ✓' : 'Settings saved ✓' })
      setKeyInput('')
      setTimeout(() => setSettingsOpen(false), 700)
    } catch (e) { setKeyMsg({ ok: false, t: String(e.message || e) }) } finally { setSaving(false) }
  }

  async function runDiscover() {
    if (!product.ref.trim()) return
    setPhase('discovering'); setLog([]); setProfile(null); setRanked([])
    try {
      await streamPost('/api/discover', { product }, (e) => {
        if (e.type === 'progress') addLog(e)
        else if (e.type === 'error') onError(e.message)
        else if (e.type === 'result') { setProfile(e.productProfile); setRanked(e.ranked || []); setSelected(new Set((e.top2 || []).map((c) => c.name))); setPhase('review') }
      })
      setPhase((p) => (p === 'discovering' ? 'form' : p))
    } catch (err) { onError(String(err.message || err)); setPhase('form') }
  }

  async function runBuild() {
    const competitors = ranked.filter((r) => selected.has(r.name)).map((r) => ({ name: r.name, url: r.url }))
    if (!competitors.length) return
    setPhase('building')
    try {
      await streamPost('/api/build', { productProfile: profile, competitors, meta }, (e) => {
        if (e.type === 'progress') addLog(e)
        else if (e.type === 'error') onError(e.message)
        else if (e.type === 'result') { setHtml(e.html || ''); setReport(e.report); setPhase('done') }
      })
    } catch (err) { onError(String(err.message || err)); setPhase('review') }
  }

  const toggle = (name) => setSelected((s) => { const n = new Set(s); n.has(name) ? n.delete(name) : n.add(name); return n })
  const slug = (profile?.name || 'product').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  const download = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([html], { type: 'text/html' })); a.download = `${slug}-comparison.html`; a.click() }

  const busy = phase === 'discovering' || phase === 'building'
  const step = ['form', 'discovering'].includes(phase) ? 1 : phase === 'review' ? 2 : 3
  const lastPhase = log.length ? log[log.length - 1].phase : null

  return (
    <>
      <div className="topbar">
        <div className="brand"><span className="mark">◆</span> Competitor Agent <small>· competitive intelligence</small></div>
        <div className="topright">
          <Stepper step={step} done={phase === 'done'} />
          <button className={`icon-btn${hasKey ? ' ok' : ''}`} title="Settings · API key" onClick={() => setSettingsOpen(true)}>
            <Gear />{hasKey === false && <span className="needdot" />}{hasKey && <span className="okdot" />}
          </button>
        </div>
      </div>

      <div className="wrap">
        <div className="hero">
          <div className="kick"><i />Competitive Intelligence</div>
          <h1>Size up your competition, honestly.</h1>
          <p>Give it your product. It finds your top two market rivals, researches them, fact-checks every claim, and writes the briefing.</p>
          <div className="flow">
            <span><b>1</b> Read your product</span><span><b>2</b> Find the rivals</span>
            <span><b>3</b> Research + verify</span><span><b>4</b> Render the report</span>
          </div>
        </div>

        {hasKey === false && (
          <div className="banner">
            <span><b>No API key set.</b> Add your Anthropic key to run an analysis.</span>
            <button className="ghost btn sm" onClick={() => setSettingsOpen(true)}><Gear /> Open settings</button>
          </div>
        )}

        <div className="card">
          <div className="card-h"><span className="n">1</span><h2>Your product</h2></div>
          <p className="card-sub">A website, a repo, a doc, or a quick description. Your side is built only from what you give it.</p>
          <label>Input</label>
          <div className="seg">
            {KINDS.map((k) => (<button key={k.v} className={product.kind === k.v ? 'on' : ''} onClick={() => setProduct({ ...product, kind: k.v })}>{k.label}</button>))}
          </div>
          <label>{product.kind === 'text' ? 'Describe the product' : product.kind === 'url' ? 'Website URL' : 'Path'}</label>
          <input value={product.ref} placeholder={PLACEHOLDER[product.kind]} onChange={(e) => setProduct({ ...product, ref: e.target.value })} />
          <label>Notes for the analyst (optional)</label>
          <textarea value={product.notes} placeholder="Anything it should know about your product or who you compete with." onChange={(e) => setProduct({ ...product, notes: e.target.value })} />
          <div className="grid3">
            <div><label>Org / brand</label><input value={meta.org} placeholder="Acme" onChange={(e) => setMeta({ ...meta, org: e.target.value })} /></div>
            <div><label>Author</label><input value={meta.author} placeholder="Your name" onChange={(e) => setMeta({ ...meta, author: e.target.value })} /></div>
            <div><label>Date label</label><input value={meta.date_label} placeholder="June 2026 · Internal" onChange={(e) => setMeta({ ...meta, date_label: e.target.value })} /></div>
          </div>
          <div className="actions">
            <button className="btn" onClick={runDiscover} disabled={busy || !product.ref.trim()}>
              {phase === 'discovering' ? <><span className="spin" /> Discovering…</> : <>Find competitors →</>}
            </button>
            {profile && <span className="understood">Understood: <b>{profile.name}</b> — {profile.category}</span>}
          </div>
        </div>

        {(busy || log.length > 0) && (
          <div className="card">
            <div className="card-h"><span className="n">~</span><h2>Live progress</h2></div>
            {busy && <div className="live"><span className="pulse" /> Working{lastPhase ? ` · ${lastPhase}` : ''}…</div>}
            <div className="timeline" ref={logRef}>
              {log.map((e, i) => (<div className="tl-row" key={i}><span className={`chip chip-${e.phase}`}>{e.phase}</span><span className="msg">{e.message}</span></div>))}
            </div>
          </div>
        )}

        {phase === 'review' && (
          <div className="card">
            <div className="card-h"><span className="n">2</span><h2>Approve the rivals</h2></div>
            <p className="card-sub">Ranked by market leadership — the top two are pre-selected. Swap if you’d rather compare against others.</p>
            <div className="cands">
              {ranked.map((r) => (
                <div className={`cand${selected.has(r.name) ? ' sel' : ''}`} key={r.name} onClick={() => toggle(r.name)}>
                  <span className="tick"><Check /></span>
                  <div>
                    <div className="name">{r.name} {typeof r.leadership_score === 'number' && <span className="score">{Math.round(r.leadership_score)}</span>}</div>
                    <div className="why">{r.why}</div>
                    {r.url && <a href={r.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>{r.url}</a>}
                  </div>
                </div>
              ))}
            </div>
            <div className="actions">
              <button className="btn" onClick={runBuild} disabled={!selected.size || busy}>{phase === 'building' ? <><span className="spin" /> Building…</> : <>Build report ({selected.size}) →</>}</button>
              <button className="ghost btn" onClick={() => setPhase('form')}>Start over</button>
            </div>
          </div>
        )}

        {phase === 'done' && (
          <div className="card">
            <div className="card-h"><span className="n"><Check /></span><h2>Your report</h2></div>
            {report && (<p className="report-info">{report.rows} capabilities · vs {report.competitors?.join(', ')} · {report.sources} sources{report.claims_downgraded?.length ? ` · ${report.claims_downgraded.length} unverified claim(s) marked unknown` : ''}</p>)}
            <div className="actions" style={{ marginTop: 0, marginBottom: 16, marginLeft: 34 }}>
              <button className="btn" onClick={download}>Download HTML</button>
              <button className="ghost btn" onClick={() => setPhase('form')}>New analysis</button>
            </div>
            <div className="browser">
              <div className="bar"><div className="lights"><i style={{ background: '#FF5F57' }} /><i style={{ background: '#FEBC2E' }} /><i style={{ background: '#28C840' }} /></div><div className="url">{slug}-comparison.html</div></div>
              <iframe className="report" title="report" srcDoc={html} />
            </div>
          </div>
        )}

        <footer className="foot">Runs on the Anthropic API · every competitor claim is sourced and verified</footer>
      </div>

      {settingsOpen && (
        <div className="overlay" onClick={() => setSettingsOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-h"><h3><Gear /> Settings</h3><button className="x" onClick={() => setSettingsOpen(false)}>×</button></div>
            <label>Anthropic API key</label>
            <div className="keyrow">
              <input type={showKey ? 'text' : 'password'} value={keyInput} placeholder={hasKey ? '•••••••••• (a key is set — paste to replace)' : 'sk-ant-...'} onChange={(e) => setKeyInput(e.target.value)} />
              <button className="ghost btn sm" onClick={() => setShowKey((s) => !s)}>{showKey ? 'Hide' : 'Show'}</button>
            </div>
            <p className="hint">Get one at <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noreferrer">console.anthropic.com</a>. Stored locally in <code>app/.env</code> on this machine — it never leaves your computer except to call Anthropic.</p>
            <label>Model</label>
            <select value={model} onChange={(e) => setModel(e.target.value)}>{MODELS.map((m) => <option key={m.v} value={m.v}>{m.label}</option>)}</select>
            {keyMsg && <p className={keyMsg.ok ? 'msg ok' : 'msg err'}>{keyMsg.t}</p>}
            <div className="actions">
              <button className="btn" onClick={saveSettings} disabled={saving || (!keyInput.trim() && !hasKey)}>{saving ? <><span className="spin" /> Saving…</> : 'Save'}</button>
              <span className="understood">{hasKey ? 'A key is currently set ✓' : 'No key set yet'}</span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
