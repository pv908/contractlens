# app/main.py
from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .models import AnalyzeResponse
from .ingestion import extract_contract_text
from .extraction_agent import extract_contract
from .risk_engine import analyse_clauses
from .report_agent import build_contract_analysis
from .qdrant_client import ensure_collection


app = FastAPI(title="ContractLens")


# Open CORS (fine for demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """
    Ensure the Qdrant collection exists when the app starts.
    """
    ensure_collection()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    contract_type: str = Form(...),   # "saas" | "services" | "employment"
    risk_profile: str = Form(...),    # "conservative" | "balanced" | "aggressive"
) -> AnalyzeResponse:
    """
    Main analysis endpoint: upload a contract + basic metadata → JSON analysis.
    """

    # 1. Ingest the file into raw text
    raw_text = extract_contract_text(file)

    # 2. Extract structured data + clauses with Gemini
    extracted = extract_contract(raw_text)

    # 3. Decide contract_type: use extracted one if present, otherwise user-provided
    final_contract_type = extracted.contract_type or contract_type

    # 4. Run risk analysis for the key clause types
    clause_analyses = analyse_clauses(
        clauses=extracted.clauses,
        contract_type=final_contract_type,
        risk_profile=risk_profile,
    )

    # 5. Build overall contract analysis (summary + key_terms)
    report = build_contract_analysis(extracted, clause_analyses)

    return AnalyzeResponse(analysis=report)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """
    Single-page UI served by FastAPI itself.
    """
    html = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>ContractLens</title>
  <style>
    :root {
      color-scheme: light dark;
    }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      margin: 0;
      background: #0b1120;
      color: #e5e7eb;
    }
    .app-shell {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      border-bottom: 1px solid #1f2937;
      padding: 1.25rem 2rem;
      background: radial-gradient(circle at top left, #111827, #020617);
    }
    header h1 {
      margin: 0;
      font-size: 1.9rem;
      letter-spacing: -0.03em;
    }
    header h1 span.badge {
      font-size: 0.8rem;
      margin-left: 0.75rem;
      padding: 0.15rem 0.6rem;
      border-radius: 999px;
      border: 1px solid #4b5563;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    header p {
      margin: 0.4rem 0 0;
      color: #9ca3af;
      max-width: 60rem;
    }
    main {
      flex: 1;
      padding: 1.5rem 2rem 2rem;
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.8fr);
      gap: 1.5rem;
    }
    @media (max-width: 960px) {
      main {
        grid-template-columns: 1fr;
      }
    }

    .card {
      background: #020617;
      border-radius: 1rem;
      border: 1px solid #111827;
      padding: 1.1rem 1.2rem 1.2rem;
      box-shadow: 0 18px 45px rgba(15,23,42,0.8);
    }
    .card h2 {
      margin: 0 0 0.5rem;
      font-size: 1.05rem;
    }
    .card p.sub {
      margin: 0;
      font-size: 0.85rem;
      color: #9ca3af;
    }

    form {
      margin-top: 0.9rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    label {
      font-size: 0.85rem;
      font-weight: 500;
      color: #e5e7eb;
      margin-bottom: 0.1rem;
      display: block;
    }
    input[type="file"],
    select {
      width: 100%;
      font-size: 0.9rem;
    }
    .field {
      display: flex;
      flex-direction: column;
    }
    .field-row {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.75rem;
    }
    button {
      align-self: flex-start;
      margin-top: 0.4rem;
      padding: 0.55rem 1.35rem;
      border-radius: 999px;
      border: none;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      background: linear-gradient(135deg, #22c55e, #16a34a);
      color: #022c22;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      box-shadow: 0 14px 30px rgba(21,128,61,0.45);
    }
    button:hover {
      filter: brightness(1.08);
    }
    button:disabled {
      opacity: 0.6;
      cursor: default;
      box-shadow: none;
    }

    .spinner {
      width: 16px;
      height: 16px;
      border-radius: 999px;
      border: 2px solid #1f2937;
      border-top-color: #22c55e;
      animation: spin 0.55s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    #status {
      margin-top: 0.3rem;
      font-size: 0.88rem;
      color: #9ca3af;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      min-height: 1.4rem;
    }
    #status.error {
      color: #fecaca;
    }

    .preview-shell {
      margin-top: 0.9rem;
      border-radius: 0.9rem;
      border: 1px dashed #374151;
      background: radial-gradient(circle at top left, #020617, #020617);
      padding: 0.75rem 0.85rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      height: 260px;
    }
    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 0.5rem;
      font-size: 0.82rem;
      color: #9ca3af;
    }
    .preview-name {
      font-weight: 500;
      color: #e5e7eb;
    }
    .preview-body {
      flex: 1;
      border-radius: 0.6rem;
      background: #020617;
      overflow: hidden;
      border: 1px solid #111827;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      color: #6b7280;
    }
    .preview-body embed {
      width: 100%;
      height: 100%;
      border: none;
      background: #111827;
    }

    /* Right column */
    #output {
      margin-top: 0.6rem;
      font-size: 0.94rem;
      line-height: 1.5;
    }
    #output h2, #output h3 {
      margin-top: 0.8rem;
      margin-bottom: 0.25rem;
    }
    #output p {
      margin-top: 0.15rem;
      margin-bottom: 0.4rem;
    }

    .badge {
      padding: 0.15rem 0.55rem;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 600;
      display: inline-block;
    }
    .GREEN { background: #064e3b; color: #bbf7d0; }
    .AMBER { background: #78350f; color: #fed7aa; }
    .RED { background: #7f1d1d; color: #fecaca; }

    .clause {
      border: 1px solid #1f2937;
      margin-top: 0.75rem;
      padding: 0.7rem 0.8rem;
      border-radius: 0.8rem;
      background: #020617;
    }
    .clause strong { text-transform: capitalize; }
    pre {
      white-space: pre-wrap;
      font-size: 0.83rem;
      background: #020617;
      padding: 0.55rem;
      border-radius: 0.45rem;
      overflow-x: auto;
      border: 1px solid #111827;
    }
    details { margin-top: 0.3rem; }
    details > summary {
      cursor: pointer;
      font-size: 0.82rem;
      color: #60a5fa;
    }

    .muted {
      color: #6b7280;
      font-size: 0.82rem;
    }

    .history-card {
      margin-top: 1rem;
      border-top: 1px solid #111827;
      padding-top: 0.8rem;
    }
    .history-card h3 {
      margin: 0 0 0.35rem;
      font-size: 0.95rem;
    }
    .history-list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      max-height: 210px;
      overflow-y: auto;
    }
    .history-item {
      padding: 0.4rem 0.45rem;
      border-radius: 0.5rem;
      background: #020617;
      border: 1px solid #0f172a;
      font-size: 0.8rem;
      display: flex;
      flex-direction: column;
      gap: 0.1rem;
    }
    .history-item-title {
      display: flex;
      justify-content: space-between;
      gap: 0.5rem;
    }
    .history-item span.name {
      font-weight: 500;
      color: #e5e7eb;
      max-width: 14rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .history-item span.time {
      color: #6b7280;
      white-space: nowrap;
    }
    .history-item span.risk {
      color: #facc15;
    }

    footer {
      padding: 0.5rem 2rem 0.9rem;
      font-size: 0.78rem;
      color: #4b5563;
      border-top: 1px solid #020617;
      text-align: right;
    }
  </style>
</head>
<body>
  <div class="app-shell">
    <header>
      <h1>
        ContractLens
        <span class="badge">demo</span>
      </h1>
      <p>Upload a SaaS / Services / Employment contract and get a structured risk snapshot across liability, termination and governing law.</p>
    </header>

    <main>
      <!-- LEFT: Upload + preview + history -->
      <section>
        <div class="card">
          <h2>1. Upload and configure</h2>
          <p class="sub">Choose your contract, tell us what kind of deal it is, and we’ll do the rest.</p>

          <form id="form">
            <div class="field">
              <label>Contract file (PDF/DOCX)</label>
              <input type="file" name="file" id="file-input" required />
            </div>

            <div class="field-row">
              <div class="field">
                <label>Contract type</label>
                <select name="contract_type">
                  <option value="saas">SaaS</option>
                  <option value="services">Services</option>
                  <option value="employment">Employment</option>
                </select>
              </div>
              <div class="field">
                <label>Risk profile</label>
                <select name="risk_profile">
                  <option value="conservative">Conservative</option>
                  <option value="balanced">Balanced</option>
                  <option value="aggressive">Aggressive</option>
                </select>
              </div>
            </div>

            <button type="submit" id="submit-btn">
              <span id="btn-spinner" class="spinner" style="display:none;"></span>
              <span id="btn-text">Analyse contract</span>
            </button>

            <div id="status"></div>
          </form>

          <div class="preview-shell">
            <div class="preview-header">
              <div>
                <div class="muted">Current file</div>
                <div class="preview-name" id="preview-filename">No file selected</div>
              </div>
              <div class="muted" id="preview-note">PDFs get an in-browser preview.</div>
            </div>
            <div class="preview-body" id="preview-body">
              <span class="muted">Pick a PDF to see a quick preview here. DOCX files will still be analysed but cannot be previewed.</span>
            </div>
          </div>

          <div class="history-card">
            <h3>Past uploads (this browser)</h3>
            <p class="muted">We keep a lightweight, local-only log of your recent analyses in this browser.</p>
            <ul id="history" class="history-list"></ul>
          </div>
        </div>
      </section>

      <!-- RIGHT: Analysis -->
      <section>
        <div class="card">
          <h2>2. Analysis</h2>
          <p class="sub">Deal summary, key terms and clause-by-clause risk commentary.</p>
          <div id="output" class="muted">Run an analysis to see results here.</div>
        </div>
      </section>
    </main>

    <footer>
      ContractLens demo.
    </footer>
  </div>

  <script>
    const form = document.getElementById('form');
    const output = document.getElementById('output');
    const statusEl = document.getElementById('status');
    const btn = document.getElementById('submit-btn');
    const btnSpinner = document.getElementById('btn-spinner');
    const btnText = document.getElementById('btn-text');
    const fileInput = document.getElementById('file-input');
    const previewName = document.getElementById('preview-filename');
    const previewBody = document.getElementById('preview-body');
    const previewNote = document.getElementById('preview-note');
    const historyEl = document.getElementById('history');

    let currentFileName = '';
    let history = [];

    // ---------- File preview ----------
    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (!file) {
        currentFileName = '';
        previewName.textContent = 'No file selected';
        previewBody.innerHTML = '<span class="muted">Pick a PDF to see a quick preview here. DOCX files will still be analysed but cannot be previewed.</span>';
        previewNote.textContent = 'PDFs get an in-browser preview.';
        return;
      }

      currentFileName = file.name;
      previewName.textContent = file.name;

      if (file.type === 'application/pdf') {
        const url = URL.createObjectURL(file);
        previewBody.innerHTML = '<embed src="' + url + '#toolbar=0&navpanes=0" type="application/pdf" />';
        previewNote.textContent = 'Inline PDF preview. For large files this may take a moment.';
      } else {
        previewBody.innerHTML = '<span class="muted">Preview is only available for PDFs. Selected file type: ' + escapeHtml(file.name) + '</span>';
        previewNote.textContent = 'DOCX and other formats are analysed but not previewed.';
      }
    });

    // ---------- History handling ----------
    function loadHistory() {
      try {
        const raw = localStorage.getItem('contractlens_history');
        if (raw) {
          history = JSON.parse(raw);
        }
      } catch (e) {
        history = [];
      }
      renderHistory();
    }

    function saveHistory() {
      try {
        localStorage.setItem('contractlens_history', JSON.stringify(history.slice(-20)));
      } catch (e) {
        // ignore storage issues
      }
    }

    function addHistoryEntry(entry) {
      history.push(entry);
      saveHistory();
      renderHistory();
    }

    function renderHistory() {
      if (!history.length) {
        historyEl.innerHTML = '<li class="muted">No uploads yet in this browser.</li>';
        return;
      }

      let html = '';
      const items = history.slice(-10).slice().reverse();
      items.forEach((h) => {
        html += '<li class="history-item">';
        html += '<div class="history-item-title">';
        html += '<span class="name">' + escapeHtml(h.filename) + '</span>';
        html += '<span class="time">' + escapeHtml(h.when) + '</span>';
        html += '</div>';
        if (h.headline_risk) {
          html += '<div class="history-item-line"><span class="risk">Headline risk:</span> ' + escapeHtml(h.headline_risk) + '</div>';
        }
        html += '</li>';
      });
      historyEl.innerHTML = html;
    }

    loadHistory();

    // ---------- Form submit / analysis ----------
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      output.classList.remove('muted');
      output.innerHTML = '';
      setStatus('Analysing contract with server...', false);
      setLoading(true);

      const fd = new FormData(form);

      try {
        const res = await fetch('/analyze', {
          method: 'POST',
          body: fd
        });

        if (!res.ok) {
          const text = await res.text();
          console.error('Server error', text);
          setStatus('Error from server (HTTP ' + res.status + '). Check logs.', true);
          setLoading(false);
          return;
        }

        const data = await res.json();
        setStatus('', false);
        renderResult(data);

        const a = data.analysis || {};
        const entry = {
          filename: currentFileName || 'Unnamed contract',
          when: new Date().toLocaleString(),
          headline_risk: (a.key_terms && a.key_terms.headline_risk) || ''
        };
        addHistoryEntry(entry);

      } catch (err) {
        console.error(err);
        setStatus('Network or client error. Check console.', true);
      } finally {
        setLoading(false);
      }
    });

    function setLoading(isLoading) {
      if (isLoading) {
        btn.disabled = true;
        btnSpinner.style.display = 'inline-block';
        btnText.textContent = 'Analysing...';
      } else {
        btn.disabled = false;
        btnSpinner.style.display = 'none';
        btnText.textContent = 'Analyse contract';
      }
    }

    function setStatus(text, isError) {
      statusEl.textContent = text;
      statusEl.classList.toggle('error', !!isError);
      if (text && !isError) {
        const dot = document.createElement('span');
        dot.textContent = 'Working…';
      }
    }

    function renderKeyTerms(key) {
      if (!key) return '';

      const parties = key.parties || [];
      const governingLaw = key.governing_law || 'Not specified';
      const termMonths = key.term_months != null ? key.term_months + ' months' : 'Not specified';
      const autoRenewal =
        key.auto_renewal === true ? 'Yes'
        : key.auto_renewal === false ? 'No'
        : 'Not specified';
      const headlineRisk = key.headline_risk || 'No major risk highlighted';
      const flags = key.flags || [];

      let html = '<h3>Key terms</h3>';
      html += '<ul>';
      if (parties.length) {
        html += '<li><strong>Parties:</strong> ' + parties.map(escapeHtml).join(' vs ') + '</li>';
      }
      html += '<li><strong>Governing law:</strong> ' + escapeHtml(governingLaw) + '</li>';
      html += '<li><strong>Term:</strong> ' + escapeHtml(termMonths) + '</li>';
      html += '<li><strong>Auto-renewal:</strong> ' + escapeHtml(autoRenewal) + '</li>';
      html += '<li><strong>Headline risk:</strong> ' + escapeHtml(headlineRisk) + '</li>';

      if (flags.length) {
        html += '<li><strong>Flags:</strong><ul>';
        flags.forEach(f => {
          html += '<li>' + escapeHtml(f) + '</li>';
        });
        html += '</ul></li>';
      }

      html += '<details><summary>Raw key_terms JSON</summary><pre>' +
              escapeHtml(JSON.stringify(key, null, 2)) +
              '</pre></details>';

      html += '</ul>';
      return html;
    }

    function renderResult(data) {
      const a = data.analysis || {};
      let html = '';

      html += '<h2>Deal summary</h2>';
      html += '<p>' + escapeHtml(a.summary || '') + '</p>';

      html += renderKeyTerms(a.key_terms);

      html += '<h3>Clause risks</h3>';
      if (!a.clauses || !a.clauses.length) {
        html += '<p class="muted">No limitation of liability, termination or governing law clauses were clearly detected.</p>';
      } else {
        a.clauses.forEach(c => {
          html += '<div class="clause">';
          html += '<strong>' + escapeHtml(c.clause_label) + '</strong> ';
          html += '<span class="badge ' + c.risk_level + '">' + c.risk_level + '</span>';
          html += '<p>' + escapeHtml(c.explanation || '') + '</p>';
          if (c.suggested_text) {
            html += '<details><summary>Suggested wording</summary><pre>' + escapeHtml(c.suggested_text) + '</pre></details>';
          }
          if (c.precedent_snippets && c.precedent_snippets.length) {
            html += '<details><summary>Precedent snippets</summary><ul>';
            c.precedent_snippets.forEach(s => {
              html += '<li><pre>' + escapeHtml(s) + '</pre></li>';
            });
            html += '</ul></details>';
          }
          html += '</div>';
        });
      }

      output.innerHTML = html;
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)

