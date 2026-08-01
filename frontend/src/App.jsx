import { useState, useRef, useCallback } from 'react'

const API_BASE = '/api'

const PIPELINE_STEPS = [
  { id: 'parse',   label: 'Parsing document' },
  { id: 'extract', label: 'AI extracting financials' },
  { id: 'charts',  label: 'Generating charts' },
  { id: 'pdf',     label: 'Building PDF report' },
]

const FORMATS = [
  { ext: 'PDF', icon: '📄' },
  { ext: 'CSV', icon: '📊' },
  { ext: 'TXT', icon: '📝' },
  { ext: 'XLSX', icon: '📈' },
]

const HOW_IT_WORKS = [
  { n: '01', name: 'Upload Document', desc: 'Upload any financial PDF, CSV, or TXT — annual report, quarterly result, earnings doc.' },
  { n: '02', name: 'AI Extraction', desc: 'Gemini AI reads the document and extracts all key financials, metrics, and narratives.' },
  { n: '03', name: 'Charts Generated', desc: 'Revenue, PAT, margins, and shareholding charts are auto-generated.' },
  { n: '04', name: 'Download PDF', desc: 'A Geojit-style professional research report is compiled and ready to download.' },
]

export default function App() {
  const [companyName, setCompanyName] = useState('')
  const [file, setFile] = useState(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [state, setState] = useState('idle') // idle | processing | done | error
  const [taskId, setTaskId] = useState(null)
  const [downloadUrl, setDownloadUrl] = useState(null)
  const [downloadFilename, setDownloadFilename] = useState('report.pdf')
  const [error, setError] = useState('')
  const [stepIdx, setStepIdx] = useState(0)
  const [progress, setProgress] = useState(0)

  const fileInputRef = useRef(null)
  const pollRef = useRef(null)

  // ── File selection ──────────────────────────────────────
  const handleFileSelect = useCallback((f) => {
    if (!f) return
    const allowed = ['.pdf', '.csv', '.txt', '.xlsx', '.xls', '.md']
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (!allowed.includes(ext)) {
      setError(`Unsupported file type: ${ext}. Please upload: ${allowed.join(', ')}`)
      return
    }
    setFile(f)
    setError('')
    // Auto-fill company name from filename if empty
    if (!companyName) {
      const name = f.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ')
      setCompanyName(name.trim())
    }
  }, [companyName])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFileSelect(f)
  }, [handleFileSelect])

  const handleDragOver = (e) => { e.preventDefault(); setIsDragOver(true) }
  const handleDragLeave = () => setIsDragOver(false)

  // ── Polling ─────────────────────────────────────────────
  const startPolling = useCallback((tid) => {
    let attempt = 0
    const STEP_DURATIONS = [4000, 10000, 5000, 6000] // ~ms per step
    let elapsed = 0
    const totalTime = STEP_DURATIONS.reduce((a, b) => a + b, 0)

    // Animate steps
    const animateSteps = () => {
      let cumulative = 0
      STEP_DURATIONS.forEach((dur, idx) => {
        setTimeout(() => {
          setStepIdx(idx)
          setProgress(Math.round(((cumulative + dur / 2) / totalTime) * 90))
          cumulative += dur
        }, cumulative)
      })
    }
    animateSteps()

    pollRef.current = setInterval(async () => {
      attempt++
      try {
        const res = await fetch(`${API_BASE}/report/${tid}/status`)
        const json = await res.json()

        if (json.status === 'done') {
          clearInterval(pollRef.current)
          setProgress(100)
          setStepIdx(PIPELINE_STEPS.length)
          setDownloadUrl(`${API_BASE}/report/${tid}`)
          setDownloadFilename(`${companyName.replace(/\s+/g, '_')}_report.pdf`)
          setState('done')
        } else if (json.status === 'error') {
          clearInterval(pollRef.current)
          setError(json.error || 'Report generation failed. Please try again.')
          setState('error')
        }
        // 'processing' → keep polling
      } catch (err) {
        if (attempt > 60) {
          clearInterval(pollRef.current)
          setError('Request timed out. Please try again.')
          setState('error')
        }
      }
    }, 2500)
  }, [companyName])

  // ── Submit ──────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!companyName.trim()) { setError('Please enter a company name.'); return }
    if (!file) { setError('Please upload a financial document.'); return }

    setState('processing')
    setError('')
    setProgress(5)
    setStepIdx(0)

    const form = new FormData()
    form.append('company_name', companyName.trim())
    form.append('file', file)

    try {
      const res = await fetch(`${API_BASE}/generate-report`, {
        method: 'POST',
        body: form,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const { task_id } = await res.json()
      setTaskId(task_id)
      startPolling(task_id)
    } catch (err) {
      setError(err.message || 'Failed to connect to server. Is the backend running?')
      setState('error')
    }
  }

  // ── Reset ───────────────────────────────────────────────
  const reset = () => {
    clearInterval(pollRef.current)
    setState('idle')
    setTaskId(null)
    setDownloadUrl(null)
    setFile(null)
    setError('')
    setProgress(0)
    setStepIdx(0)
    setCompanyName('')
  }

  const canSubmit = companyName.trim().length > 0 && file !== null && state === 'idle'
  const fileExt = file ? file.name.split('.').pop().toUpperCase() : ''

  return (
    <div className="app">
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <div className="navbar-logo">B</div>
          <span className="navbar-name">AI Financial Research Report Generator</span>
          <span className="navbar-badge">Research Engine</span>
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--gray-500)' }}>
          <a href={`${API_BASE}/template`} style={{ color: 'inherit' }}>Download editable template</a>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero">
        <div className="hero-tag">
          <span className="hero-tag-dot" />
          AI-Powered Equity Research
        </div>
        <h1 className="hero-title">
          Instant{' '}
          <span className="hero-title-gradient">Research Reports</span>
          <br />from Any Financial Doc
        </h1>
        <p className="hero-subtitle">
          Upload a quarterly result, annual report, or earnings PDF and get a
          professional Geojit-style research report with tables, charts, and
          AI-written analysis — in under 60 seconds.
        </p>
        <div className="hero-features">
          {['PDF / CSV / TXT', 'AI Extraction', '4 Chart Types', 'One-click Download', 'Geojit Template'].map((f) => (
            <span key={f} className="hero-feature-chip">
              <span className="chip-icon">✦</span> {f}
            </span>
          ))}
        </div>
      </section>

      {/* Main */}
      <main className="main-content">

        {/* Upload Form Card */}
        {state === 'idle' || state === 'processing' ? (
          <div className="upload-card">
            <div className="card-title">
              <div className="card-title-icon">📋</div>
              Generate Research Report
            </div>

            <form onSubmit={handleSubmit}>
              <div className="form-grid">
                <div className="form-group full-width">
                  <label className="form-label" htmlFor="company-name-input">Company Name</label>
                  <input
                    id="company-name-input"
                    className="form-input"
                    type="text"
                    placeholder="e.g. Eternal Limited, ICICI Bank, POCL..."
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    disabled={state === 'processing'}
                  />
                </div>

                <div className="form-group full-width">
                  <label className="form-label">Financial Document</label>
                  <div
                    id="file-drop-zone"
                    className={`drop-zone ${isDragOver ? 'drag-over' : ''} ${file ? 'file-selected' : ''}`}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => !file && fileInputRef.current?.click()}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.csv,.txt,.xlsx,.xls,.md"
                      onChange={(e) => handleFileSelect(e.target.files[0])}
                      disabled={state === 'processing'}
                      id="file-input"
                      tabIndex={-1}
                    />

                    {!file ? (
                      <>
                        <span className="drop-icon">📂</span>
                        <p className="drop-text-primary">Drop your file here or <span style={{color:'var(--teal-400)'}}>browse</span></p>
                        <p className="drop-text-secondary">
                          Supports <span>PDF</span>, <span>CSV</span>, <span>TXT</span>, <span>XLSX</span>
                        </p>
                      </>
                    ) : (
                      <div className="file-info">
                        <span className="file-type-badge">{fileExt}</span>
                        <span style={{maxWidth:'300px', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>
                          {file.name}
                        </span>
                        <span style={{fontSize:'0.75rem', color:'var(--gray-600)'}}>
                          ({(file.size / 1024).toFixed(0)} KB)
                        </span>
                        {state === 'idle' && (
                          <button
                            type="button"
                            className="file-remove-btn"
                            onClick={(e) => { e.stopPropagation(); setFile(null) }}
                            title="Remove file"
                          >✕</button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {error && state === 'idle' && (
                <div className="error-card" style={{marginTop:'0.75rem', marginBottom:'0'}}>
                  <span className="error-icon">⚠️</span>
                  <div className="error-content">
                    <div className="error-title">Input Error</div>
                    <div className="error-msg">{error}</div>
                  </div>
                </div>
              )}

              <button
                id="generate-btn"
                type="submit"
                className="submit-btn"
                disabled={!canSubmit}
              >
                {state === 'processing' ? (
                  <>
                    <span style={{width:16,height:16,border:'2px solid rgba(255,255,255,0.3)',borderTopColor:'white',borderRadius:'50%',display:'inline-block',animation:'spin 0.8s linear infinite'}} />
                    Generating Report…
                  </>
                ) : (
                  <> ✦ Generate Research Report </>
                )}
              </button>
            </form>
          </div>
        ) : null}

        {/* Processing Progress */}
        {state === 'processing' && (
          <div className="progress-card">
            <div className="progress-header">
              <div className="progress-spinner" />
              <div>
                <div className="progress-title">Generating Your Report</div>
                <div className="progress-subtitle">
                  AI is analyzing {file?.name} for {companyName}…
                </div>
              </div>
            </div>

            <div className="progress-bar-track">
              <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
            </div>

            <div className="progress-steps">
              {PIPELINE_STEPS.map((step, idx) => {
                const status = idx < stepIdx ? 'done' : idx === stepIdx ? 'active' : 'pending'
                return (
                  <div key={step.id} className={`progress-step ${status}`}>
                    <div className={`step-icon ${status}`}>
                      {status === 'done' ? '✓' : status === 'active' ? '◉' : '○'}
                    </div>
                    <span>{step.label}</span>
                    {status === 'active' && (
                      <span style={{fontSize:'0.72rem', color:'var(--teal-500)', marginLeft:'auto'}}>
                        in progress…
                      </span>
                    )}
                    {status === 'done' && (
                      <span style={{fontSize:'0.72rem', color:'var(--gray-600)', marginLeft:'auto'}}>done</span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Error */}
        {state === 'error' && (
          <div className="error-card" style={{marginTop:'1.5rem'}}>
            <span className="error-icon">❌</span>
            <div className="error-content">
              <div className="error-title">Report Generation Failed</div>
              <div className="error-msg">{error}</div>
              <button className="error-retry-btn" onClick={reset}>↩ Try Again</button>
            </div>
          </div>
        )}

        {/* Success + Download */}
        {state === 'done' && (
          <div className="success-card">
            <span className="success-icon">🎉</span>
            <h2 className="success-title">Report Ready!</h2>
            <p className="success-subtitle">
              Your <strong>{companyName}</strong> research report has been generated with
              financial tables, AI narratives, and charts.
            </p>
            <div style={{display:'flex', gap:'0.75rem', justifyContent:'center', flexWrap:'wrap'}}>
              <a
                id="download-pdf-btn"
                className="download-btn"
                href={downloadUrl}
                download={downloadFilename}
                target="_blank"
                rel="noreferrer"
              >
                ⬇ Download PDF Report
              </a>
              <button className="new-report-btn" onClick={reset}>
                ✦ New Report
              </button>
            </div>
          </div>
        )}

        {/* How It Works */}
        <div className="how-it-works">
          <div className="section-label">How it works</div>
          <h2 className="section-title">Four steps to a professional report</h2>
          <div className="steps-grid">
            {HOW_IT_WORKS.map((s) => (
              <div key={s.n} className="step-card">
                <div className="step-number">STEP {s.n}</div>
                <div className="step-name">{s.name}</div>
                <div className="step-desc">{s.desc}</div>
              </div>
            ))}
          </div>

          <div style={{marginTop:'1.5rem'}}>
            <div className="section-label">Supported formats</div>
            <div className="formats-row">
              {FORMATS.map((f) => (
                <span key={f.ext} className="format-badge">{f.icon} .{f.ext}</span>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        AI Financial Research Report Generator &mdash;
        {' '}<a href="https://github.com/Shamshuu/AI-Financial-Research-Report-Generator" target="_blank" rel="noreferrer">GitHub</a>
        &nbsp;|&nbsp; Template fields defined in{' '}
        <code style={{fontFamily:'var(--font-mono)', fontSize:'0.72rem'}}>backend/template_fields.py</code>
      </footer>
    </div>
  )
}
