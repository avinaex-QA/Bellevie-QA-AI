/**
 * AI Test Case Generator — Frontend Application
 * Handles all UI interactions, API calls, state management, rendering,
 * and export history management.
 */
'use strict';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  testCases:     [],
  currentFilter: 'all',
  searchQuery:   '',
  selectedFile:  null,
  isLoading:     false,
  currentView:   'testcases',  // 'testcases' | 'history'
  lastSummary:   null,
  lastSourceType: 'text',
};

// ── DOM refs ───────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const els = {
  generateBtn:    $('generate-btn'),
  btnText:        $('btn-text'),
  btnIcon:        $('btn-icon'),
  jiraId:         $('jira-id'),
  fetchJiraBtn:   $('fetch-jira-btn'),
  jiraPreview:    $('jira-preview'),
  fileInput:      $('file-input'),
  dropzone:       $('dropzone'),
  fileSelected:   $('file-selected'),
  textInput:      $('text-input'),
  charCount:      $('char-count'),
  githubUrl:      $('github-url'),
  additionalCtx:  $('additional-context'),
  // Panels
  emptyState:     $('empty-state'),
  loadingState:   $('loading-state'),
  errorState:     $('error-state'),
  resultsContent: $('results-content'),
  // Loading steps
  ls1: $('ls-1'), ls2: $('ls-2'), ls3: $('ls-3'), ls4: $('ls-4'),
  // Results
  resultsTitle:   $('results-title'),
  resultsHeader:  $('results-header'),
  moduleBadge:    $('module-badge'),
  statHigh:       $('stat-high'),
  statMedium:     $('stat-medium'),
  statLow:        $('stat-low'),
  statTotal:      $('stat-total'),
  statsPanel:     $('stats-panel'),
  tcTbody:        $('tc-tbody'),
  searchInput:    $('search-input'),
  downloadBtn:    $('download-btn'),
  // Error
  errorMessage:   $('error-message'),
  healthDot:      $('health-dot'),
  // Modal
  modalOverlay:   $('modal-overlay'),
  modalId:        $('modal-id'),
  modalPriority:  $('modal-priority'),
  modalTitle:     $('modal-title'),
  modalPre:       $('modal-pre'),
  modalSteps:     $('modal-steps'),
  modalExpected:  $('modal-expected'),
  modalTags:      $('modal-tags'),
  // History
  historyView:    $('history-view'),
  historyTbody:   $('history-tbody'),
  historyLoading: $('history-loading'),
  historyEmpty:   $('history-empty'),
  histTableWrap:  $('history-table-wrap'),
  tabTcCount:     $('tab-tc-count'),
  tabHistCount:   $('tab-hist-count'),
  histCountBadge: $('history-count-badge'),
};

const API_BASE = window.location.origin;

// ── API helpers ────────────────────────────────────────────────────────────
async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Health Check ──────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    await apiGet('/health');
    els.healthDot.classList.add('ok');
    els.healthDot.title = 'API is healthy';
  } catch {
    els.healthDot.classList.add('err');
    els.healthDot.title = 'API unreachable — is the server running?';
  }
}

// ── View switching (Test Cases ↔ Export History) ──────────────────────────
function switchView(view) {
  state.currentView = view;

  document.querySelectorAll('.view-tab').forEach((t) => t.classList.remove('active'));
  $(`tab-${view === 'testcases' ? 'testcases' : 'history'}`).classList.add('active');

  const tcParts = [els.resultsHeader, $('search-bar-wrap'), $('table-wrap'), $('no-filter-msg')];

  if (view === 'history') {
    tcParts.forEach((el) => el && el.classList.add('hidden'));
    els.historyView.classList.remove('hidden');
    loadHistory(false);
  } else {
    tcParts.forEach((el) => el && el.classList.remove('hidden'));
    els.historyView.classList.add('hidden');
  }
}

// Sidebar toggle button
function toggleHistoryPanel() {
  // Switch to results area and show history tab
  showPanel('results');
  switchView('history');
}

// ── Tab Switching (Input Sources) ─────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach((p) => p.classList.add('hidden'));
    btn.classList.add('active');
    $(`tab-${tab}`).classList.remove('hidden');
  });
});

// ── Character Count ───────────────────────────────────────────────────────
els.textInput.addEventListener('input', () => {
  els.charCount.textContent = els.textInput.value.length.toLocaleString();
});

// ── File Upload / Dropzone ────────────────────────────────────────────────
els.dropzone.addEventListener('click', (e) => {
  if (e.target.tagName !== 'BUTTON') els.fileInput.click();
});
els.dropzone.addEventListener('dragover',  (e) => { e.preventDefault(); els.dropzone.classList.add('dragover'); });
els.dropzone.addEventListener('dragleave', () => els.dropzone.classList.remove('dragover'));
els.dropzone.addEventListener('drop', (e) => {
  e.preventDefault(); els.dropzone.classList.remove('dragover');
  if (e.dataTransfer.files[0]) handleFileSelected(e.dataTransfer.files[0]);
});
els.fileInput.addEventListener('change', () => {
  if (els.fileInput.files[0]) handleFileSelected(els.fileInput.files[0]);
});

function handleFileSelected(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'docx', 'doc', 'txt', 'md'].includes(ext)) {
    showToast(`Unsupported file type .${ext}. Use PDF, DOCX, or TXT.`, 'error');
    return;
  }
  state.selectedFile = file;
  els.fileSelected.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" width="14" height="14"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    <span>${escapeHtml(file.name)}</span>
    <span style="color:var(--text-muted);font-size:0.7rem;">(${(file.size/1024).toFixed(1)} KB)</span>
    <button class="file-badge-remove" onclick="clearFile()" title="Remove file">✕</button>`;
  els.fileSelected.classList.remove('hidden');
  els.dropzone.querySelector('.dropzone-text').textContent = 'File ready';
}

function clearFile() {
  state.selectedFile = null;
  els.fileInput.value = '';
  els.fileSelected.classList.add('hidden');
  els.dropzone.querySelector('.dropzone-text').textContent = 'Drag & drop your file here';
}

// ── Jira Preview ──────────────────────────────────────────────────────────
els.fetchJiraBtn.addEventListener('click', fetchJiraPreview);
els.jiraId.addEventListener('keydown', (e) => { if (e.key === 'Enter') fetchJiraPreview(); });

async function fetchJiraPreview() {
  const id = els.jiraId.value.trim();
  if (!id) return;
  els.fetchJiraBtn.disabled = true;
  els.jiraPreview.innerHTML = '<span style="color:var(--text-muted)">Fetching ticket...</span>';
  els.jiraPreview.classList.remove('hidden');
  try {
    const ticket = await apiGet(`/api/jira/fetch/${encodeURIComponent(id)}`);
    els.jiraPreview.innerHTML = `
      <div class="preview-id">${escapeHtml(ticket.ticket_id)}</div>
      <div class="preview-title">${escapeHtml(ticket.summary)}</div>
      <div class="preview-meta">${escapeHtml(ticket.issue_type)} · ${escapeHtml(ticket.status||'Unknown')} · Priority: ${escapeHtml(ticket.priority||'Unset')}</div>`;
  } catch (err) {
    els.jiraPreview.innerHTML = `<span style="color:var(--high);font-size:0.75rem;">⚠ ${escapeHtml(err.message)}</span>`;
  } finally {
    els.fetchJiraBtn.disabled = false;
  }
}

// ── Generate Test Cases ───────────────────────────────────────────────────
els.generateBtn.addEventListener('click', handleGenerate);

async function handleGenerate() {
  if (state.isLoading) return;

  const jiraId    = els.jiraId.value.trim();
  const textInput = els.textInput.value.trim();
  const githubUrl = els.githubUrl.value.trim();
  const addCtx    = els.additionalCtx.value.trim();
  const hasFile   = !!state.selectedFile;

  if (!jiraId && !textInput && !githubUrl && !hasFile) {
    showToast('Provide at least one input: Jira ID, document, text, or GitHub PR URL.', 'error');
    return;
  }

  setLoading(true);
  showPanel('loading');
  startLoadingAnimation();

  try {
    const formData = new FormData();
    if (jiraId)    formData.append('jira_id', jiraId);
    if (textInput) formData.append('text_input', textInput);
    if (githubUrl) formData.append('github_pr_url', githubUrl);
    if (addCtx)    formData.append('additional_context', addCtx);
    if (hasFile)   formData.append('file', state.selectedFile);

    const sourceTypes = [];
    if (jiraId)    sourceTypes.push('jira');
    if (hasFile)   sourceTypes.push('document');
    if (textInput) sourceTypes.push('text');
    if (githubUrl) sourceTypes.push('github_pr');
    const sourceType = sourceTypes[0] || 'text';
    formData.append('source_type', sourceType);
    state.lastSourceType = sourceType;

    const res = await fetch(`${API_BASE}/api/generate`, { method: 'POST', body: formData });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errData.detail || `Server error HTTP ${res.status}`);
    }

    const data = await res.json();
    state.testCases  = data.test_cases;
    state.lastSummary = data.summary;

    renderResults(data);
    showPanel('results');
    switchView('testcases');

  } catch (err) {
    console.error('Generation error:', err);
    els.errorMessage.textContent = err.message || 'Unexpected error. Check the server terminal for details.';
    showPanel('error');
  } finally {
    setLoading(false);
    stopLoadingAnimation();
  }
}

// ── Loading animation ─────────────────────────────────────────────────────
let loadTimers = [];

function startLoadingAnimation() {
  const steps = [els.ls1, els.ls2, els.ls3, els.ls4];
  const msgs = [
    ['Parsing input sources…',       'Reading and combining your requirements'],
    ['AI analyzing complexity…',     'Identifying user flows, validations, integrations'],
    ['Generating full coverage…',    'Writing test cases for every scenario found'],
    ['Deduplicating & formatting…',  'Removing duplicates and assigning priorities'],
  ];
  steps.forEach((s) => { s.className = 'load-step'; });
  steps[0].classList.add('active');
  $('loading-title').textContent = msgs[0][0];
  $('loading-sub').textContent   = msgs[0][1];
  const delays = [0, 4000, 12000, 22000];
  delays.forEach((delay, i) => {
    if (i === 0) return;
    const t = setTimeout(() => {
      steps[i-1].className = 'load-step done';
      steps[i].classList.add('active');
      $('loading-title').textContent = msgs[i][0];
      $('loading-sub').textContent   = msgs[i][1];
    }, delay);
    loadTimers.push(t);
  });
}

function stopLoadingAnimation() {
  loadTimers.forEach(clearTimeout);
  loadTimers = [];
}

// ── Render Results ────────────────────────────────────────────────────────
function renderResults(data) {
  const { test_cases, summary } = data;
  els.statHigh.textContent   = summary.high_priority;
  els.statMedium.textContent = summary.medium_priority;
  els.statLow.textContent    = summary.low_priority;
  els.statTotal.textContent  = summary.total;
  els.statsPanel.classList.remove('hidden');
  els.resultsTitle.textContent = `${summary.total} Test Cases`;
  els.moduleBadge.textContent  = summary.module_detected || 'General';
  els.tabTcCount.textContent   = summary.total;
  renderTable(test_cases);
}

function renderTable(cases) {
  const filtered = filterAndSearch(cases);
  els.tcTbody.innerHTML = '';
  $('no-filter-msg').classList.toggle('hidden', filtered.length > 0);
  if (!filtered.length) return;

  const frag = document.createDocumentFragment();
  filtered.forEach((tc) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="tc-id-cell">${escapeHtml(tc.id)}</td>
      <td><span class="priority-badge ${escapeHtml(tc.priority)}">${escapeHtml(tc.priority)}</span></td>
      <td><span class="type-badge">${escapeHtml(tc.test_type)}</span></td>
      <td class="tags-cell">${renderTags(tc.tags)}</td>
      <td style="font-weight:500;">${escapeHtml(tc.title)}</td>
      <td style="color:var(--text-secondary);font-size:0.77rem;">${escapeHtml(tc.preconditions)}</td>
      <td class="steps-cell">${renderStepsInline(tc.steps)}</td>
      <td class="expected-cell">${escapeHtml(tc.expected_result)}</td>
      <td class="actual-cell">${tc.actual_result ? escapeHtml(tc.actual_result) : '—'}</td>`;
    tr.addEventListener('click', () => openModal(tc));
    frag.appendChild(tr);
  });
  els.tcTbody.appendChild(frag);
}

function renderTags(tags) {
  if (!tags || !tags.length) return '—';
  return tags.map((t) => `<span class="tag-pill ${escapeHtml(t)}">${escapeHtml(t)}</span>`).join('');
}

function renderStepsInline(steps) {
  if (!steps || !steps.length) return '—';
  const preview = steps.slice(0, 3)
    .map((s, i) => `<strong>${i+1}.</strong> ${escapeHtml(s)}`).join('<br>');
  const more = steps.length > 3
    ? `<br><span style="color:var(--text-muted);font-size:0.72rem;">+${steps.length-3} more steps…</span>`
    : '';
  return preview + more;
}

// ── Filter & Search ───────────────────────────────────────────────────────
document.querySelectorAll('.filter-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    state.currentFilter = btn.dataset.filter;
    renderTable(state.testCases);
  });
});

els.searchInput.addEventListener('input', () => {
  state.searchQuery = els.searchInput.value.toLowerCase();
  renderTable(state.testCases);
});

function filterAndSearch(cases) {
  let result = cases;
  if (state.currentFilter !== 'all') {
    result = result.filter((tc) => tc.priority === state.currentFilter);
  }
  if (state.searchQuery) {
    result = result.filter((tc) =>
      tc.title.toLowerCase().includes(state.searchQuery) ||
      tc.steps.join(' ').toLowerCase().includes(state.searchQuery) ||
      tc.tags.join(' ').toLowerCase().includes(state.searchQuery) ||
      tc.expected_result.toLowerCase().includes(state.searchQuery) ||
      tc.test_type.toLowerCase().includes(state.searchQuery)
    );
  }
  return result;
}

function clearFilter() {
  state.currentFilter = 'all';
  document.querySelectorAll('.filter-btn').forEach((b) => b.classList.remove('active'));
  document.querySelector('.filter-btn[data-filter="all"]').classList.add('active');
  renderTable(state.testCases);
}

// ── Excel Download ────────────────────────────────────────────────────────
els.downloadBtn.addEventListener('click', downloadExcel);

async function downloadExcel() {
  if (!state.testCases.length) return;
  els.downloadBtn.innerHTML = '⏳ Exporting…';
  els.downloadBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/export/excel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        test_cases: state.testCases,
        project_name: 'AI Generated Test Cases',
        sheet_title: 'Test Cases',
        source_type: state.lastSourceType || 'text',
        module_detected: state.lastSummary?.module_detected || 'General',
      }),
    });
    if (!res.ok) throw new Error('Export request failed');

    const blob = await res.blob();
    // Extract filename from Content-Disposition header
    const cd = res.headers.get('Content-Disposition') || '';
    const match = cd.match(/filename=(.+)/);
    const filename = match ? match[1] : `test_cases_${Date.now()}.xlsx`;

    const url = URL.createObjectURL(blob);
    const a   = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);

    showToast(`Exported ${state.testCases.length} test cases → ${filename}`, 'success');

    // Refresh history count badge
    await refreshHistoryBadge();

  } catch (err) {
    showToast(`Export failed: ${err.message}`, 'error');
  } finally {
    els.downloadBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" width="16" height="16"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      Export Excel`;
    els.downloadBtn.disabled = false;
  }
}

// ── Export History ────────────────────────────────────────────────────────
async function loadHistory(showSpinner = true) {
  if (showSpinner) {
    els.historyLoading.classList.remove('hidden');
    els.historyEmpty.classList.add('hidden');
    els.histTableWrap.classList.add('hidden');
  }
  try {
    const data = await apiGet('/api/export/history');
    const exports = data.exports || [];

    // Update badges
    els.tabHistCount.textContent = exports.length;
    els.histCountBadge.textContent = exports.length;

    if (!exports.length) {
      els.historyEmpty.classList.remove('hidden');
      els.histTableWrap.classList.add('hidden');
    } else {
      renderHistoryTable(exports);
      els.histTableWrap.classList.remove('hidden');
      els.historyEmpty.classList.add('hidden');
    }
  } catch (err) {
    showToast(`Could not load history: ${err.message}`, 'error');
  } finally {
    els.historyLoading.classList.add('hidden');
  }
}

async function refreshHistoryBadge() {
  try {
    const data = await apiGet('/api/export/history');
    const count = (data.exports || []).length;
    els.histCountBadge.textContent = count;
    els.tabHistCount.textContent   = count;
    if (state.currentView === 'history') renderHistoryTable(data.exports || []);
  } catch { /* non-critical */ }
}

function renderHistoryTable(exports) {
  els.historyTbody.innerHTML = '';
  const frag = document.createDocumentFragment();

  exports.forEach((entry) => {
    const tr = document.createElement('tr');
    const createdAt = new Date(entry.created_at).toLocaleString();
    tr.innerHTML = `
      <td style="font-family:monospace;font-size:0.75rem;color:var(--accent-light);">${escapeHtml(entry.file_name)}</td>
      <td style="font-size:0.78rem;color:var(--text-secondary);">${escapeHtml(createdAt)}</td>
      <td style="text-align:center;font-weight:700;color:var(--accent-light);">${entry.count}</td>
      <td><span class="source-badge">${escapeHtml(entry.source || 'text')}</span></td>
      <td style="font-size:0.78rem;color:var(--text-secondary);">${escapeHtml(entry.module || 'General')}</td>
      <td>
        <div class="hist-actions">
          <button class="hist-btn hist-btn-dl" onclick="downloadHistoryFile('${escapeHtml(entry.file_name)}')">
            ↓ Download
          </button>
          <button class="hist-btn hist-btn-del" onclick="deleteHistoryFile('${escapeHtml(entry.file_name)}', this)">
            Delete
          </button>
        </div>
      </td>`;
    frag.appendChild(tr);
  });
  els.historyTbody.appendChild(frag);
}

async function downloadHistoryFile(filename) {
  try {
    const url = `${API_BASE}/api/export/download/${encodeURIComponent(filename)}`;
    const a   = document.createElement('a');
    a.href = url; a.download = filename; a.click();
  } catch (err) {
    showToast(`Download failed: ${err.message}`, 'error');
  }
}

async function deleteHistoryFile(filename, btnEl) {
  if (!confirm(`Delete "${filename}" permanently?`)) return;
  btnEl.disabled = true;
  btnEl.textContent = '…';
  try {
    const res = await fetch(`${API_BASE}/api/export/${encodeURIComponent(filename)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error((await res.json()).detail || 'Delete failed');
    showToast(`Deleted ${filename}`, 'success');
    await loadHistory(false);
  } catch (err) {
    showToast(`Delete failed: ${err.message}`, 'error');
    btnEl.disabled = false;
    btnEl.textContent = 'Delete';
  }
}

// ── Modal ─────────────────────────────────────────────────────────────────
function openModal(tc) {
  els.modalId.textContent     = tc.id;
  els.modalPriority.textContent = tc.priority;
  els.modalPriority.className = `modal-priority-badge priority-badge ${tc.priority}`;
  els.modalTitle.textContent  = tc.title;
  els.modalPre.textContent    = tc.preconditions || '—';
  els.modalExpected.textContent = tc.expected_result || '—';
  els.modalSteps.innerHTML    = '';
  (tc.steps || []).forEach((step) => {
    const li = document.createElement('li');
    li.textContent = step;
    els.modalSteps.appendChild(li);
  });
  els.modalTags.innerHTML = renderTags(tc.tags);
  els.modalOverlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  els.modalOverlay.classList.add('hidden');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

// ── Panel switching ───────────────────────────────────────────────────────
function showPanel(name) {
  els.emptyState.classList.add('hidden');
  els.loadingState.classList.add('hidden');
  els.errorState.classList.add('hidden');
  els.resultsContent.classList.add('hidden');

  if (name === 'empty')   els.emptyState.classList.remove('hidden');
  if (name === 'loading') els.loadingState.classList.remove('hidden');
  if (name === 'error')   els.errorState.classList.remove('hidden');
  if (name === 'results') els.resultsContent.classList.remove('hidden');
}

function resetToEmpty() {
  showPanel('empty');
  state.testCases = [];
  els.statsPanel.classList.add('hidden');
}

// ── Loading state ─────────────────────────────────────────────────────────
function setLoading(loading) {
  state.isLoading = loading;
  els.generateBtn.disabled = loading;
  if (loading) {
    els.btnText.textContent = 'Generating…';
  } else {
    els.btnIcon.innerHTML = `<path d="M13 10V3L4 14h7v7l9-11h-7z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
    els.btnText.textContent = 'Generate Test Cases';
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.className = 'toast';
  const colors = {
    error:   { bg: '#2d1b1b', border: 'rgba(248,81,73,0.5)',   text: 'var(--high)' },
    success: { bg: '#1b2d1e', border: 'rgba(63,185,80,0.5)',   text: 'var(--low)' },
    info:    { bg: '#1b1d2d', border: 'rgba(124,58,237,0.5)',  text: 'var(--accent-light)' },
  };
  const c = colors[type] || colors.info;
  toast.style.cssText = `
    position:fixed;bottom:1.5rem;right:1.5rem;z-index:999;
    background:${c.bg};border:1px solid ${c.border};color:${c.text};
    padding:0.75rem 1.25rem;border-radius:8px;font-size:0.83rem;max-width:400px;
    box-shadow:0 8px 24px rgba(0,0,0,0.4);animation:slideUp 0.25s ease;`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}

// ── Utilities ─────────────────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

// ── Init ──────────────────────────────────────────────────────────────────
(function init() {
  showPanel('empty');
  checkHealth();
  // Load initial history count for the badge
  apiGet('/api/export/history').then((data) => {
    const count = (data.exports || []).length;
    if (els.histCountBadge) els.histCountBadge.textContent = count;
    if (els.tabHistCount)   els.tabHistCount.textContent   = count;
  }).catch(() => {});
})();
