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
  selectedProjects: [],
  selectedModules: [],
  projectOptions: [],
  moduleOptions: [],
  isLoading:     false,
  currentView:   'testcases',  // 'testcases' | 'history'
  lastSummary:   null,
  lastSourceType: 'text',
  lastSelectedProjects: [],
  lastSelectedModules: [],
  lastSourceInfo: {},
  activeBugTestCaseId: null,
  currentUser: null,
};

const PROJECT_STORAGE_KEY = 'ai-testcase-generator-project-options-v1';
const MODULE_STORAGE_KEY = 'ai-testcase-generator-module-options-v1';
const MAX_MANAGED_OPTIONS = 50;

// ── DOM refs ───────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const els = {
  generateBtn:    $('generate-btn'),
  btnText:        $('btn-text'),
  btnIcon:        $('btn-icon'),
  projectMultiselect: $('project-multiselect'),
  projectToggle:  $('project-toggle'),
  projectMenu:    $('project-menu'),
  projectSearch:  $('project-search'),
  addProjectBtn:  $('add-project-btn'),
  projectOptions: $('project-options'),
  selectedProjects: $('selected-projects'),
  projectHelper:  $('project-helper'),
  clearProjectsBtn: $('clear-projects-btn'),
  moduleMultiselect: $('module-multiselect'),
  moduleToggle:   $('module-toggle'),
  moduleMenu:     $('module-menu'),
  moduleSearch:   $('module-search'),
  addModuleBtn:   $('add-module-btn'),
  moduleOptions:  $('module-options'),
  selectedModules: $('selected-modules'),
  moduleHelper:   $('module-helper'),
  clearModulesBtn: $('clear-modules-btn'),
  jiraId:         $('jira-id'),
  fetchJiraBtn:   $('fetch-jira-btn'),
  jiraPreview:    $('jira-preview'),
  clickupTaskId:  $('clickup-task-id'),
  fetchClickupBtn: $('fetch-clickup-btn'),
  clickupPreview: $('clickup-preview'),
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
  // Bug modal
  bugModalOverlay: $('bug-modal-overlay'),
  bugModalTcId: $('bug-modal-tc-id'),
  bugModalSeverityBadge: $('bug-modal-severity-badge'),
  bugSummary: $('bug-summary'),
  bugDescription: $('bug-description'),
  bugSteps: $('bug-steps'),
  bugActual: $('bug-actual'),
  bugExpected: $('bug-expected'),
  bugSeverity: $('bug-severity'),
  bugEnvironment: $('bug-environment'),
  bugProject: $('bug-project'),
  bugModule: $('bug-module'),
  bugClassification: $('bug-classification'),
  bugType: $('bug-type'),
  bugDeviceType: $('bug-device-type'),
  bugImpacted: $('bug-impacted'),
  bugAppVersion: $('bug-app-version'),
  bugVertical: $('bug-vertical'),
  bugReviewer: $('bug-reviewer'),
  bugSprint: $('bug-sprint'),
  bugAdditionalNotes: $('bug-additional-notes'),
  bugRootCause: $('bug-root-cause'),
  submitBugBtn: $('submit-bug-btn'),
  // History
  historyView:    $('history-view'),
  historyTbody:   $('history-tbody'),
  historyLoading: $('history-loading'),
  historyEmpty:   $('history-empty'),
  histTableWrap:  $('history-table-wrap'),
  tabTcCount:     $('tab-tc-count'),
  tabHistCount:   $('tab-hist-count'),
  histCountBadge: $('history-count-badge'),
  authView: $('auth-view'),
  loginTabBtn: $('login-tab-btn'),
  signupTabBtn: $('signup-tab-btn'),
  loginForm: $('login-form'),
  signupForm: $('signup-form'),
  loginEmail: $('login-email'),
  loginPassword: $('login-password'),
  loginBtn: $('login-btn'),
  signupName: $('signup-name'),
  signupEmail: $('signup-email'),
  signupPassword: $('signup-password'),
  signupConfirmPassword: $('signup-confirm-password'),
  signupError: $('signup-error'),
  signupBtn: $('signup-btn'),
  otpForm: $('otp-form'),
  otpEmailLabel: $('otp-email-label'),
  otpCode: $('otp-code'),
  otpCountdown: $('otp-countdown'),
  otpError: $('otp-error'),
  resendOtpBtn: $('resend-otp-btn'),
  verifyOtpBtn: $('verify-otp-btn'),
  googleLoginBtn: $('google-login-btn'),
  forgotPasswordBtn: $('forgot-password-btn'),
  profileMenuWrap: $('profile-menu-wrap'),
  profileAvatarBtn: $('profile-avatar-btn'),
  profileAvatarLetter: $('profile-avatar-letter'),
  profileDropdown: $('profile-dropdown'),
  profileSettingsItem: $('profile-settings-item'),
  profileLogoutItem: $('profile-logout-item'),
  settingsModal: $('settings-modal'),
  closeSettingsBtn: $('close-settings-btn'),
  integrationStatus: $('integration-status'),
  jiraBaseUrlSetting: $('jira-base-url'),
  jiraEmailSetting: $('jira-email-setting'),
  jiraTokenSetting: $('jira-token-setting'),
  jiraProjectKeySetting: $('jira-project-key-setting'),
  saveJiraIntegration: $('save-jira-integration'),
  clickupTokenSetting: $('clickup-token-setting'),
  clickupBaseSetting: $('clickup-base-setting'),
  saveClickupIntegration: $('save-clickup-integration'),
  connectClickupOauth: $('connect-clickup-oauth'),
  githubTokenSetting: $('github-token-setting'),
  saveGithubIntegration: $('save-github-integration'),
  connectGithubOauth: $('connect-github-oauth'),
  connectJiraOauth: $('connect-jira-oauth'),
  aiProviderSetting: $('ai-provider-setting'),
  aiKeySetting: $('ai-key-setting'),
  saveAiIntegration: $('save-ai-integration'),
};

const API_BASE = window.location.origin;
const SESSION_STORAGE_KEY = 'ai-testcase-generator-session-v2';
let otpTimer = null;
let pendingSignupEmail = '';

// ── Auth / Settings listeners ────────────────────────────────────────────
els.loginTabBtn.addEventListener('click', () => switchAuthTab('login'));
els.signupTabBtn.addEventListener('click', () => switchAuthTab('signup'));
els.loginBtn.addEventListener('click', handleLogin);
els.signupBtn.addEventListener('click', handleSignup);
els.verifyOtpBtn.addEventListener('click', handleVerifyOtp);
els.resendOtpBtn.addEventListener('click', handleResendOtp);
els.googleLoginBtn.addEventListener('click', startGoogleLogin);
els.forgotPasswordBtn.addEventListener('click', () => showToast('Password reset email flow is ready for SMTP integration in the next backend step.', 'info'));
els.profileAvatarBtn.addEventListener('click', toggleProfileMenu);
els.profileSettingsItem.addEventListener('click', openSettingsModal);
els.profileLogoutItem.addEventListener('click', handleLogout);
els.closeSettingsBtn.addEventListener('click', () => els.settingsModal.classList.add('hidden'));
els.saveJiraIntegration.addEventListener('click', () => saveIntegration('jira', {
  base_url: els.jiraBaseUrlSetting.value.trim(),
  email: els.jiraEmailSetting.value.trim(),
  api_token: els.jiraTokenSetting.value,
  bug_project_key: els.jiraProjectKeySetting.value.trim(),
}));
els.saveClickupIntegration.addEventListener('click', () => saveIntegration('clickup', {
  api_token: els.clickupTokenSetting.value,
  api_base: els.clickupBaseSetting.value.trim() || 'https://api.clickup.com/api/v2',
}));
els.saveGithubIntegration.addEventListener('click', () => saveIntegration('github', {
  token: els.githubTokenSetting.value,
}));
els.saveAiIntegration.addEventListener('click', () => saveIntegration('ai', {
  provider: els.aiProviderSetting.value,
  api_key: els.aiKeySetting.value,
}));
els.connectGithubOauth.addEventListener('click', () => startOAuth('github'));
els.connectClickupOauth.addEventListener('click', () => startOAuth('clickup'));
els.connectJiraOauth.addEventListener('click', () => startOAuth('jira'));
document.addEventListener('click', (event) => {
  if (!els.profileMenuWrap.contains(event.target)) closeProfileMenu();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeProfileMenu();
  if (event.key === 'ArrowDown' && document.activeElement === els.profileAvatarBtn) {
    event.preventDefault();
    openProfileMenu();
    els.profileSettingsItem.focus();
  }
});

// ── API helpers ────────────────────────────────────────────────────────────
async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiJson(path, payload, method = 'POST') {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    if (res.status === 401) showAuthView();
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function showAuthView() {
  closeProfileMenu();
  els.authView.classList.remove('hidden');
}

function showAppView(user) {
  state.currentUser = user;
  els.authView.classList.add('hidden');
  updateProfileAvatar(user);
}

function getProfileInitial(user) {
  const source = (user?.name || user?.email || 'U').trim();
  return (source[0] || 'U').toUpperCase();
}

function updateProfileAvatar(user) {
  els.profileAvatarLetter.textContent = getProfileInitial(user);
  const label = user?.name || user?.email || 'User';
  els.profileAvatarBtn.setAttribute('aria-label', `Open profile menu for ${label}`);
}

function openSettingsModal() {
  closeProfileMenu();
  els.settingsModal.classList.remove('hidden');
  loadIntegrationStatus();
}

function openProfileMenu() {
  els.profileDropdown.classList.remove('hidden');
  els.profileAvatarBtn.setAttribute('aria-expanded', 'true');
}

function closeProfileMenu() {
  if (!els.profileDropdown) return;
  els.profileDropdown.classList.add('hidden');
  els.profileAvatarBtn?.setAttribute('aria-expanded', 'false');
}

function toggleProfileMenu(event) {
  event.stopPropagation();
  if (els.profileDropdown.classList.contains('hidden')) openProfileMenu();
  else closeProfileMenu();
}

function switchAuthTab(tab) {
  const login = tab === 'login';
  els.loginTabBtn.classList.toggle('active', login);
  els.signupTabBtn.classList.toggle('active', !login);
  els.loginForm.classList.toggle('hidden', !login);
  els.signupForm.classList.toggle('hidden', login);
  els.otpForm.classList.add('hidden');
  clearInlineError(els.signupError);
  clearInlineError(els.otpError);
}

function isValidEmail(email) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
}

function validateSignupPassword(password) {
  return password.length >= 8 && /[A-Z]/.test(password) && /[a-z]/.test(password) && /\d/.test(password) && /[^A-Za-z0-9]/.test(password);
}

function showInlineError(el, message) {
  el.textContent = message;
  el.classList.remove('hidden');
}

function clearInlineError(el) {
  el.textContent = '';
  el.classList.add('hidden');
}

async function requireCurrentUser() {
  try {
    const user = await apiGet('/api/auth/me');
    showAppView(user);
    return user;
  } catch {
    showAuthView();
    return null;
  }
}

async function handleLogin() {
  const email = els.loginEmail.value.trim();
  const password = els.loginPassword.value;
  if (!email) return showToast('Email is required.', 'error');
  if (!isValidEmail(email)) return showToast('Please enter a valid email address.', 'error');
  if (!password) return showToast('Password is required.', 'error');
  if (password.length < 8) return showToast('Password must meet minimum requirements.', 'error');
  try {
    const data = await apiJson('/api/auth/login', {
      email,
      password,
    });
    showAppView(data.user);
    showToast('Logged in successfully.', 'success');
    loadIntegrationStatus();
    loadHistoryCount();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleSignup() {
  const name = els.signupName.value.trim();
  const email = els.signupEmail.value.trim();
  const password = els.signupPassword.value;
  const confirmPassword = els.signupConfirmPassword.value;
  clearInlineError(els.signupError);

  if (!name) return showInlineError(els.signupError, 'Name is required.');
  if (!email) return showInlineError(els.signupError, 'Email is required.');
  if (!isValidEmail(email)) return showInlineError(els.signupError, 'Please enter a valid email address.');
  if (!password) return showInlineError(els.signupError, 'Password is required.');
  if (!validateSignupPassword(password)) return showInlineError(els.signupError, 'Password must contain uppercase, lowercase, number, and special character.');
  if (password !== confirmPassword) return showInlineError(els.signupError, 'Passwords do not match.');

  els.signupBtn.disabled = true;
  try {
    const data = await apiJson('/api/auth/signup/start', {
      name,
      email,
      password,
      confirm_password: confirmPassword,
    });
    pendingSignupEmail = data.email;
    els.otpEmailLabel.textContent = data.email;
    els.signupForm.classList.add('hidden');
    els.otpForm.classList.remove('hidden');
    startOtpCountdown(data.expires_in_seconds || 600);
    showToast('Verification code sent', 'success');
  } catch (err) {
    showInlineError(els.signupError, err.message);
  } finally {
    els.signupBtn.disabled = false;
  }
}

function startOtpCountdown(seconds) {
  if (otpTimer) clearInterval(otpTimer);
  let remaining = seconds;
  const render = () => {
    const mins = String(Math.floor(remaining / 60)).padStart(2, '0');
    const secs = String(remaining % 60).padStart(2, '0');
    els.otpCountdown.textContent = remaining > 0 ? `Code expires in ${mins}:${secs}` : 'Code expired';
  };
  render();
  otpTimer = setInterval(() => {
    remaining -= 1;
    render();
    if (remaining <= 0) clearInterval(otpTimer);
  }, 1000);
}

async function handleVerifyOtp() {
  clearInlineError(els.otpError);
  const otp = els.otpCode.value.trim();
  if (!/^\d{6}$/.test(otp)) return showInlineError(els.otpError, 'Invalid OTP');
  els.verifyOtpBtn.disabled = true;
  try {
    const data = await apiJson('/api/auth/signup/verify', { email: pendingSignupEmail, otp });
    showAppView(data.user);
    showToast('Email verified. Account created.', 'success');
    loadIntegrationStatus();
    loadHistoryCount();
  } catch (err) {
    showInlineError(els.otpError, err.message);
  } finally {
    els.verifyOtpBtn.disabled = false;
  }
}

async function handleResendOtp() {
  clearInlineError(els.otpError);
  try {
    const data = await apiJson('/api/auth/signup/resend', { email: pendingSignupEmail });
    startOtpCountdown(data.expires_in_seconds || 600);
    showToast('OTP resent', 'success');
  } catch (err) {
    showInlineError(els.otpError, err.message);
  }
}

async function handleLogout() {
  closeProfileMenu();
  try {
    await apiJson('/api/auth/logout', {});
  } catch {}
  state.currentUser = null;
  localStorage.removeItem(SESSION_STORAGE_KEY);
  showAuthView();
  showToast('Logged out.', 'success');
}

async function startGoogleLogin() {
  try {
    const data = await apiGet('/api/auth/google/start');
    if (!data.configured) {
      showToast(data.message || 'Google OAuth is not configured locally. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.', 'error');
      return;
    }
    if (!data.authorization_url) {
      showToast('Google sign-in failed. Please try again.', 'error');
      return;
    }
    window.location.href = data.authorization_url;
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function loadIntegrationStatus() {
  if (!state.currentUser) return;
  try {
    const data = await apiGet('/api/integrations');
    els.integrationStatus.innerHTML = (data.integrations || []).map((item) => `
      <div class="integration-card">
        <h4>${escapeHtml(item.provider.toUpperCase())}</h4>
        <span class="status-pill ${item.connected ? '' : 'off'}">${item.connected ? 'Connected' : 'Not Connected'}</span>
        <div class="preview-meta" style="margin-top:6px;">
          ${item.display?.email ? `Connected as: ${escapeHtml(item.display.email)}<br>` : ''}
          ${item.display?.username ? `Connected as: ${escapeHtml(item.display.username)}<br>` : ''}
          ${item.display?.workspace ? `Workspace: ${escapeHtml(item.display.workspace)}<br>` : ''}
          ${item.display?.provider ? `Provider: ${escapeHtml(item.display.provider)}<br>` : ''}
          ${item.auth_type ? `Auth: ${escapeHtml(item.auth_type)}` : ''}
        </div>
        <div class="integration-actions">
          ${item.provider !== 'ai' ? `<button class="btn-secondary" type="button" onclick="startOAuth('${escapeHtml(item.provider)}')">${item.connected ? 'Reconnect' : 'Connect'}</button>` : ''}
          ${item.connected ? `<button class="btn-secondary" type="button" onclick="testIntegration('${escapeHtml(item.provider)}')">Test</button><button class="btn-secondary" type="button" onclick="disconnectIntegration('${escapeHtml(item.provider)}')">Disconnect</button>` : ''}
        </div>
      </div>
    `).join('');
  } catch (err) {
    els.integrationStatus.innerHTML = `<div class="integration-card"><span style="color:var(--high)">${escapeHtml(err.message)}</span></div>`;
  }
}

async function testIntegration(provider) {
  try {
    const data = await apiJson(`/api/integrations/${provider}/test`, {});
    showToast(data.message, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function disconnectIntegration(provider) {
  try {
    const data = await apiJson(`/api/integrations/${provider}`, null, 'DELETE');
    showToast(data.message, 'success');
    loadIntegrationStatus();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function saveIntegration(provider, payload) {
  try {
    const data = await apiJson(`/api/integrations/${provider}`, payload);
    showToast(data.message, 'success');
    loadIntegrationStatus();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function startOAuth(provider) {
  try {
    const data = await apiGet(`/api/integrations/oauth/${provider}/start`);
    if (!data.configured) {
      showToast(`${provider.toUpperCase()} OAuth is not configured locally. Add OAuth client values in .env.`, 'error');
      return;
    }
    window.location.href = data.authorization_url;
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function loadHistoryCount() {
  try {
    const data = await apiGet('/api/export/history');
    const count = (data.exports || []).length;
    if (els.histCountBadge) els.histCountBadge.textContent = count;
    if (els.tabHistCount)   els.tabHistCount.textContent   = count;
  } catch {
    if (els.histCountBadge) els.histCountBadge.textContent = '0';
    if (els.tabHistCount)   els.tabHistCount.textContent   = '0';
  }
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

// ── Project Multiselect ──────────────────────────────────────────────────
function hasRequirementSource() {
  return !!(
    els.jiraId.value.trim() ||
    els.clickupTaskId.value.trim() ||
    els.textInput.value.trim() ||
    els.githubUrl.value.trim() ||
    state.selectedFile
  );
}

function updateGenerateButton() {
  const hasProjects = state.selectedProjects.length > 0;
  const hasModules = state.selectedModules.length > 0;
  const hasSource = hasRequirementSource();
  const canGenerate = hasProjects && hasModules && hasSource && !state.isLoading;

  els.generateBtn.disabled = !canGenerate;
  els.generateBtn.title = canGenerate ? 'Generate test cases' : 'Select project, module, and requirement source';

  if (!hasProjects) {
    els.projectHelper.textContent = 'Select at least one project before generation.';
    els.projectHelper.classList.add('warning');
  } else {
    els.projectHelper.textContent = 'Project context will guide product-specific coverage.';
    els.projectHelper.classList.remove('warning');
  }

  if (!hasModules) {
    els.moduleHelper.textContent = 'Select at least one module before generation.';
    els.moduleHelper.classList.add('warning');
  } else if (!hasSource) {
    els.moduleHelper.textContent = 'Please select Project, Module, and at least one requirement source (Jira, ClickUp, Text, Document, or GitHub PR).';
    els.moduleHelper.classList.add('warning');
  } else {
    els.moduleHelper.textContent = 'Module context will guide feature-specific Bellevie coverage.';
    els.moduleHelper.classList.remove('warning');
  }

  if (hasProjects && !hasSource) {
    els.projectHelper.textContent = 'Please select Project, Module, and at least one requirement source (Jira, ClickUp, Text, Document, or GitHub PR).';
    els.projectHelper.classList.add('warning');
  }
}

function openProjectMenu() {
  els.projectMenu.classList.remove('hidden');
  els.projectMultiselect.classList.add('open');
  els.projectToggle.setAttribute('aria-expanded', 'true');
  els.projectSearch.focus();
}

function closeProjectMenu() {
  els.projectMenu.classList.add('hidden');
  els.projectMultiselect.classList.remove('open');
  els.projectToggle.setAttribute('aria-expanded', 'false');
}

function toggleProjectMenu() {
  if (els.projectMenu.classList.contains('hidden')) openProjectMenu();
  else closeProjectMenu();
}

function normalizeManagedOption(value) {
  return String(value || '').trim().replace(/\s+/g, ' ');
}

function optionKey(value) {
  return normalizeManagedOption(value).toLowerCase();
}

function getManagedOptions(kind) {
  return kind === 'project' ? state.projectOptions : state.moduleOptions;
}

function setManagedOptions(kind, options) {
  if (kind === 'project') state.projectOptions = options;
  else state.moduleOptions = options;
}

function getManagedStorageKey(kind) {
  return kind === 'project' ? PROJECT_STORAGE_KEY : MODULE_STORAGE_KEY;
}

function getManagedSearchEl(kind) {
  return kind === 'project' ? els.projectSearch : els.moduleSearch;
}

function getManagedHelperEl(kind) {
  return kind === 'project' ? els.projectHelper : els.moduleHelper;
}

function getManagedLabel(kind) {
  return kind === 'project' ? 'project' : 'module';
}

function loadManagedOptions(kind) {
  try {
    const stored = JSON.parse(localStorage.getItem(getManagedStorageKey(kind)) || '[]');
    const options = Array.isArray(stored) ? stored : [];
    setManagedOptions(kind, dedupeManagedOptions(options).slice(0, MAX_MANAGED_OPTIONS));
  } catch {
    setManagedOptions(kind, []);
  }
}

function saveManagedOptions(kind) {
  localStorage.setItem(getManagedStorageKey(kind), JSON.stringify(getManagedOptions(kind)));
}

function dedupeManagedOptions(options) {
  const seen = new Set();
  const cleaned = [];
  options.forEach((option) => {
    const value = normalizeManagedOption(option);
    const key = optionKey(value);
    if (!value || seen.has(key)) return;
    seen.add(key);
    cleaned.push(value);
  });
  return cleaned;
}

function setManagedValidation(kind, message) {
  const helper = getManagedHelperEl(kind);
  helper.textContent = message;
  helper.classList.add('warning');
}

function clearManagedValidation(kind) {
  getManagedHelperEl(kind).classList.remove('warning');
  updateGenerateButton();
}

function addManagedOption(kind) {
  const label = getManagedLabel(kind);
  const searchEl = getManagedSearchEl(kind);
  const value = normalizeManagedOption(searchEl.value);
  const options = getManagedOptions(kind);

  if (!value) {
    setManagedValidation(kind, `Enter a ${label} name before adding.`);
    return;
  }
  if (options.length >= MAX_MANAGED_OPTIONS) {
    setManagedValidation(kind, kind === 'project' ? 'Maximum 50 projects allowed' : 'Maximum 50 modules allowed');
    return;
  }
  if (options.some((option) => optionKey(option) === optionKey(value))) {
    setManagedValidation(kind, `This ${label} already exists.`);
    return;
  }

  const nextOptions = [...options, value].sort((a, b) => a.localeCompare(b));
  setManagedOptions(kind, nextOptions);
  saveManagedOptions(kind);
  searchEl.value = '';

  if (kind === 'project') {
    state.selectedProjects = [...state.selectedProjects, value];
    renderProjectSelector();
  } else {
    state.selectedModules = [...state.selectedModules, value];
    renderModuleSelector();
  }
  clearManagedValidation(kind);
}

function deleteManagedOption(kind, value, event) {
  event.stopPropagation();
  const cleanValue = normalizeManagedOption(value);
  const key = optionKey(cleanValue);
  setManagedOptions(kind, getManagedOptions(kind).filter((option) => optionKey(option) !== key));
  saveManagedOptions(kind);

  if (kind === 'project') {
    state.selectedProjects = state.selectedProjects.filter((item) => optionKey(item) !== key);
    renderProjectSelector();
  } else {
    state.selectedModules = state.selectedModules.filter((item) => optionKey(item) !== key);
    renderModuleSelector();
  }
  updateGenerateButton();
}

function toggleProjectSelection(project) {
  const key = optionKey(project);
  if (state.selectedProjects.some((item) => optionKey(item) === key)) {
    state.selectedProjects = state.selectedProjects.filter((item) => optionKey(item) !== key);
  } else {
    state.selectedProjects = [...state.selectedProjects, project];
  }
  renderProjectSelector();
  updateGenerateButton();
}

function removeProject(project, event) {
  event.stopPropagation();
  const key = optionKey(project);
  state.selectedProjects = state.selectedProjects.filter((item) => optionKey(item) !== key);
  renderProjectSelector();
  updateGenerateButton();
}

function clearProjects() {
  state.selectedProjects = [];
  els.projectSearch.value = '';
  renderProjectSelector();
  updateGenerateButton();
}

function renderProjectSelector() {
  if (!state.selectedProjects.length) {
    els.selectedProjects.innerHTML = '<span class="multiselect-placeholder">Search and select project context...</span>';
  } else {
    els.selectedProjects.innerHTML = state.selectedProjects.map((project) => `
      <span class="project-chip" data-project-chip="${escapeHtml(project)}">
        ${escapeHtml(project)}
        <button type="button" class="remove-project-chip" data-project="${escapeHtml(project)}" title="Remove ${escapeHtml(project)}">×</button>
      </span>
    `).join('');
  }

  const query = els.projectSearch.value.trim().toLowerCase();
  const options = state.projectOptions.filter((project) => project.toLowerCase().includes(query));
  els.projectOptions.innerHTML = options.length
    ? options.map((project) => {
        const selected = state.selectedProjects.some((item) => optionKey(item) === optionKey(project));
        return `
          <div class="project-option ${selected ? 'selected' : ''}" role="button" tabindex="0" data-project="${escapeHtml(project)}">
            <span>${escapeHtml(project)}</span>
            <span class="project-option-actions">
              <span class="option-check">${selected ? '✓' : ''}</span>
              <button class="delete-option-btn" type="button" data-delete-project="${escapeHtml(project)}" aria-label="Delete ${escapeHtml(project)}">×</button>
            </span>
          </div>`;
      }).join('')
    : `<div class="managed-empty-state">${query ? 'No matching projects. Add it to use it.' : 'No projects yet. Type a project name and add it.'}</div>`;

  els.clearProjectsBtn.classList.toggle('hidden', state.selectedProjects.length === 0);
}

els.projectToggle.addEventListener('click', toggleProjectMenu);
els.projectSearch.addEventListener('input', () => {
  clearManagedValidation('project');
  renderProjectSelector();
});
els.projectSearch.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    addManagedOption('project');
  }
});
els.addProjectBtn.addEventListener('click', () => addManagedOption('project'));
els.clearProjectsBtn.addEventListener('click', clearProjects);
els.selectedProjects.addEventListener('click', (event) => {
  const removeBtn = event.target.closest('.remove-project-chip[data-project]');
  if (removeBtn) removeProject(removeBtn.dataset.project, event);
});
els.projectOptions.addEventListener('click', (event) => {
  const deleteBtn = event.target.closest('[data-delete-project]');
  if (deleteBtn) {
    deleteManagedOption('project', deleteBtn.dataset.deleteProject, event);
    return;
  }
  const option = event.target.closest('.project-option[data-project]');
  if (option) toggleProjectSelection(option.dataset.project);
});
els.projectOptions.addEventListener('keydown', (event) => {
  if (!['Enter', ' '].includes(event.key)) return;
  const option = event.target.closest('.project-option[data-project]');
  if (!option || event.target.closest('[data-delete-project]')) return;
  event.preventDefault();
  toggleProjectSelection(option.dataset.project);
});
document.addEventListener('click', (event) => {
  if (!els.projectMultiselect.contains(event.target)) closeProjectMenu();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeProjectMenu();
});

function openModuleMenu() {
  els.moduleMenu.classList.remove('hidden');
  els.moduleMultiselect.classList.add('open');
  els.moduleToggle.setAttribute('aria-expanded', 'true');
  els.moduleSearch.focus();
}

function closeModuleMenu() {
  els.moduleMenu.classList.add('hidden');
  els.moduleMultiselect.classList.remove('open');
  els.moduleToggle.setAttribute('aria-expanded', 'false');
}

function toggleModuleMenu() {
  if (els.moduleMenu.classList.contains('hidden')) openModuleMenu();
  else closeModuleMenu();
}

function toggleModuleSelection(moduleName) {
  const key = optionKey(moduleName);
  if (state.selectedModules.some((item) => optionKey(item) === key)) {
    state.selectedModules = state.selectedModules.filter((item) => optionKey(item) !== key);
  } else {
    state.selectedModules = [...state.selectedModules, moduleName];
  }
  renderModuleSelector();
  updateGenerateButton();
}

function removeModule(moduleName, event) {
  event.stopPropagation();
  const key = optionKey(moduleName);
  state.selectedModules = state.selectedModules.filter((item) => optionKey(item) !== key);
  renderModuleSelector();
  updateGenerateButton();
}

function clearModules() {
  state.selectedModules = [];
  els.moduleSearch.value = '';
  renderModuleSelector();
  updateGenerateButton();
}

function renderModuleSelector() {
  if (!state.selectedModules.length) {
    els.selectedModules.innerHTML = '<span class="multiselect-placeholder">Search and select module context...</span>';
  } else {
    els.selectedModules.innerHTML = state.selectedModules.map((moduleName) => `
      <span class="project-chip" data-module-chip="${escapeHtml(moduleName)}">
        ${escapeHtml(moduleName)}
        <button type="button" class="remove-module-chip" data-module="${escapeHtml(moduleName)}" title="Remove ${escapeHtml(moduleName)}">×</button>
      </span>
    `).join('');
  }

  const query = els.moduleSearch.value.trim().toLowerCase();
  const options = state.moduleOptions.filter((moduleName) => moduleName.toLowerCase().includes(query));
  els.moduleOptions.innerHTML = options.length
    ? options.map((moduleName) => {
        const selected = state.selectedModules.some((item) => optionKey(item) === optionKey(moduleName));
        return `
          <div class="project-option ${selected ? 'selected' : ''}" role="button" tabindex="0" data-module="${escapeHtml(moduleName)}">
            <span>${escapeHtml(moduleName)}</span>
            <span class="project-option-actions">
              <span class="option-check">${selected ? '✓' : ''}</span>
              <button class="delete-option-btn" type="button" data-delete-module="${escapeHtml(moduleName)}" aria-label="Delete ${escapeHtml(moduleName)}">×</button>
            </span>
          </div>`;
      }).join('')
    : `<div class="managed-empty-state">${query ? 'No matching modules. Add it to use it.' : 'No modules yet. Type a module name and add it.'}</div>`;

  els.clearModulesBtn.classList.toggle('hidden', state.selectedModules.length === 0);
}

els.moduleToggle.addEventListener('click', toggleModuleMenu);
els.moduleSearch.addEventListener('input', () => {
  clearManagedValidation('module');
  renderModuleSelector();
});
els.moduleSearch.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    addManagedOption('module');
  }
});
els.addModuleBtn.addEventListener('click', () => addManagedOption('module'));
els.clearModulesBtn.addEventListener('click', clearModules);
els.selectedModules.addEventListener('click', (event) => {
  const removeBtn = event.target.closest('.remove-module-chip[data-module]');
  if (removeBtn) removeModule(removeBtn.dataset.module, event);
});
els.moduleOptions.addEventListener('click', (event) => {
  const deleteBtn = event.target.closest('[data-delete-module]');
  if (deleteBtn) {
    deleteManagedOption('module', deleteBtn.dataset.deleteModule, event);
    return;
  }
  const option = event.target.closest('.project-option[data-module]');
  if (option) toggleModuleSelection(option.dataset.module);
});
els.moduleOptions.addEventListener('keydown', (event) => {
  if (!['Enter', ' '].includes(event.key)) return;
  const option = event.target.closest('.project-option[data-module]');
  if (!option || event.target.closest('[data-delete-module]')) return;
  event.preventDefault();
  toggleModuleSelection(option.dataset.module);
});
document.addEventListener('click', (event) => {
  if (!els.moduleMultiselect.contains(event.target)) closeModuleMenu();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeModuleMenu();
});

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
  updateGenerateButton();
});
els.jiraId.addEventListener('input', updateGenerateButton);
els.clickupTaskId.addEventListener('input', updateGenerateButton);
els.githubUrl.addEventListener('input', updateGenerateButton);
els.additionalCtx.addEventListener('input', updateGenerateButton);

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
  updateGenerateButton();
}

function clearFile() {
  state.selectedFile = null;
  els.fileInput.value = '';
  els.fileSelected.classList.add('hidden');
  els.dropzone.querySelector('.dropzone-text').textContent = 'Drag & drop your file here';
  updateGenerateButton();
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

// ── ClickUp Preview ───────────────────────────────────────────────────────
els.fetchClickupBtn.addEventListener('click', fetchClickUpPreview);
els.clickupTaskId.addEventListener('keydown', (e) => { if (e.key === 'Enter') fetchClickUpPreview(); });

async function fetchClickUpPreview() {
  const id = els.clickupTaskId.value.trim();
  if (!id) return;
  els.fetchClickupBtn.disabled = true;
  els.clickupPreview.innerHTML = '<span style="color:var(--text-muted)">Fetching ClickUp task...</span>';
  els.clickupPreview.classList.remove('hidden');
  try {
    const task = await apiGet(`/api/clickup/task/${encodeURIComponent(id)}`);
    const tags = Array.isArray(task.tags) && task.tags.length ? ` · Tags: ${task.tags.map(escapeHtml).join(', ')}` : '';
    const description = task.description ? escapeHtml(task.description).slice(0, 180) : 'No description provided';
    els.clickupPreview.innerHTML = `
      <div class="preview-id">${escapeHtml(task.task_id)}</div>
      <div class="preview-title">${escapeHtml(task.title)}</div>
      <div class="preview-meta">${escapeHtml(task.status || 'Unknown')} · Priority: ${escapeHtml(task.priority || 'Unset')} · ${escapeHtml(task.assignee || 'Unassigned')}${tags}</div>
      <div class="preview-meta" style="margin-top:6px;line-height:1.4;">${description}${task.description && task.description.length > 180 ? '...' : ''}</div>`;
  } catch (err) {
    els.clickupPreview.innerHTML = `<span style="color:var(--high);font-size:0.75rem;">⚠ ${escapeHtml(err.message)}</span>`;
  } finally {
    els.fetchClickupBtn.disabled = false;
  }
}

// ── Generate Test Cases ───────────────────────────────────────────────────
els.generateBtn.addEventListener('click', handleGenerate);

async function handleGenerate() {
  if (state.isLoading) return;

  const jiraId    = els.jiraId.value.trim();
  const clickupTaskId = els.clickupTaskId.value.trim();
  const textInput = els.textInput.value.trim();
  const githubUrl = els.githubUrl.value.trim();
  const addCtx    = els.additionalCtx.value.trim();
  const hasFile   = !!state.selectedFile;

  if (!state.selectedProjects.length) {
    showToast('Please select at least one project.', 'error');
    updateGenerateButton();
    return;
  }

  if (!state.selectedModules.length) {
    showToast('Please select at least one module.', 'error');
    updateGenerateButton();
    return;
  }

  if (!jiraId && !clickupTaskId && !textInput && !githubUrl && !hasFile) {
    showToast('Please select Project, Module, and at least one requirement source (Jira, ClickUp, Text, Document, or GitHub PR).', 'error');
    updateGenerateButton();
    return;
  }

  setLoading(true);
  showPanel('loading');
  startLoadingAnimation();

  try {
    const formData = new FormData();
    state.selectedProjects.forEach((project) => formData.append('selected_projects', project));
    state.selectedModules.forEach((moduleName) => formData.append('selected_modules', moduleName));
    if (jiraId)    formData.append('jira_id', jiraId);
    if (clickupTaskId) formData.append('clickup_task_id', clickupTaskId);
    if (textInput) formData.append('text_input', textInput);
    if (githubUrl) formData.append('github_pr_url', githubUrl);
    if (addCtx)    formData.append('additional_context', addCtx);
    if (hasFile)   formData.append('file', state.selectedFile);

    const sourceTypes = [];
    if (jiraId)    sourceTypes.push('jira');
    if (clickupTaskId) sourceTypes.push('clickup');
    if (hasFile)   sourceTypes.push('document');
    if (textInput) sourceTypes.push('text');
    if (githubUrl) sourceTypes.push('github_pr');
    const sourceType = sourceTypes[0] || 'text';
    formData.append('source_type', sourceType);
    state.lastSourceType = sourceType;
    state.lastSelectedProjects = [...state.selectedProjects];
    state.lastSelectedModules = [...state.selectedModules];

    const res = await fetch(`${API_BASE}/api/generate`, { method: 'POST', body: formData });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errData.detail || `Server error HTTP ${res.status}`);
    }

    const data = await res.json();
    state.testCases  = data.test_cases.map(normalizeExecutionState);
    state.lastSummary = data.summary;
    state.lastSourceInfo = data.source_info || {};
    state.lastSelectedProjects = data.source_info?.selected_projects || [...state.selectedProjects];
    state.lastSelectedModules = data.source_info?.selected_modules || [...state.selectedModules];

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
  saveExecutionSession();
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
      <td>${renderExecutionControls(tc)}</td>
      <td><span class="priority-badge ${escapeHtml(tc.priority)}">${escapeHtml(tc.priority)}</span></td>
      <td><span class="type-badge">${escapeHtml(tc.test_type)}</span></td>
      <td class="tags-cell">${renderTags(tc.tags)}</td>
      <td style="font-weight:500;">${escapeHtml(tc.title)}</td>
      <td style="color:var(--text-secondary);font-size:0.77rem;">${escapeHtml(tc.preconditions)}</td>
      <td class="steps-cell">${renderStepsInline(tc.steps)}</td>
      <td class="expected-cell">${escapeHtml(tc.expected_result)}</td>
      <td class="actual-cell">${tc.actual_result ? escapeHtml(tc.actual_result) : '—'}</td>
      <td class="bug-action-cell">${renderBugAction(tc)}</td>`;
    tr.addEventListener('click', () => openModal(tc));
    frag.appendChild(tr);
  });
  els.tcTbody.appendChild(frag);
}

function normalizeExecutionState(tc) {
  return {
    ...tc,
    status: tc.status || 'Not Executed',
    execution_notes: tc.execution_notes || '',
    tester_comments: tc.tester_comments || '',
    jira_bug_id: tc.jira_bug_id || '',
    jira_bug_url: tc.jira_bug_url || '',
  };
}

function renderExecutionControls(tc) {
  const statuses = ['Not Executed', 'Passed', 'Failed', 'Blocked', 'Skipped'];
  return `
    <div class="execution-controls" onclick="event.stopPropagation()">
      <select class="status-select" onchange="updateTestStatus('${escapeHtml(tc.id)}', this.value)">
        ${statuses.map((status) => `<option value="${status}" ${tc.status === status ? 'selected' : ''}>${status}</option>`).join('')}
      </select>
      <textarea class="execution-notes" placeholder="Execution notes..." oninput="updateExecutionNotes('${escapeHtml(tc.id)}', this.value)">${escapeHtml(tc.execution_notes || '')}</textarea>
    </div>`;
}

function renderBugAction(tc) {
  if (tc.jira_bug_id) {
    const href = tc.jira_bug_url || '#';
    return `<a class="linked-bug" href="${escapeHtml(href)}" target="_blank" onclick="event.stopPropagation()">Linked Bug: ${escapeHtml(tc.jira_bug_id)}</a>`;
  }
  if (tc.status === 'Failed') {
    return `<button class="btn-raise-bug" onclick="event.stopPropagation(); openBugModal('${escapeHtml(tc.id)}')">Raise Bug</button>`;
  }
  return `<span class="status-pill ${escapeHtml(tc.status || 'Not Executed')}">${escapeHtml(tc.status || 'Not Executed')}</span>`;
}

function findTestCase(id) {
  return state.testCases.find((tc) => tc.id === id);
}

function updateTestStatus(id, status) {
  const tc = findTestCase(id);
  if (!tc) return;
  tc.status = status;
  if (status !== 'Failed') {
    tc.execution_notes = tc.execution_notes || '';
  }
  saveExecutionSession();
  renderTable(state.testCases);
}

function updateExecutionNotes(id, notes) {
  const tc = findTestCase(id);
  if (tc) {
    tc.execution_notes = notes;
    saveExecutionSession();
  }
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
        selected_projects: state.lastSelectedProjects,
        selected_modules: state.lastSelectedModules,
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
      <td><div class="history-projects">${renderHistoryProjects(entry.selected_projects)}</div></td>
      <td><div class="history-projects">${renderHistoryProjects(entry.selected_modules)}</div></td>
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

function renderHistoryProjects(projects) {
  if (!projects || !projects.length) return '<span style="color:var(--text-muted);">—</span>';
  return projects.map((project) => `<span class="history-project-pill">${escapeHtml(project)}</span>`).join('');
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

function getSourceIssueKey() {
  return state.lastSourceInfo?.jira?.ticket_id || els.jiraId.value.trim().toUpperCase() || null;
}

function setBugModalLoading(loading) {
  els.submitBugBtn.disabled = loading;
  els.submitBugBtn.textContent = loading ? 'Creating…' : 'Create Jira Bug';
}

function fillBugModal(draft) {
  els.bugSummary.value = draft.bug_summary || '';
  els.bugDescription.value = draft.description || '';
  els.bugSteps.value = Array.isArray(draft.steps_to_reproduce)
    ? draft.steps_to_reproduce.map((step, index) => `${index + 1}. ${step}`).join('\n')
    : (draft.steps_to_reproduce || '');
  els.bugActual.value = draft.actual_result || '';
  els.bugExpected.value = draft.expected_result || '';
  els.bugSeverity.value = draft.severity || 'Medium';
  els.bugEnvironment.value = draft.environment || 'QA';
  els.bugProject.value = draft.project || state.lastSelectedProjects.join(', ');
  els.bugModule.value = draft.module || state.lastSelectedModules.join(', ');
  els.bugClassification.value = draft.classification || 'Functionality';
  els.bugType.value = draft.type || 'Frontend';
  els.bugDeviceType.value = draft.device_type || 'Web';
  els.bugImpacted.value = draft.impacted_areas || '';
  els.bugAppVersion.value = draft.app_version || '';
  els.bugVertical.value = draft.vertical || '';
  els.bugReviewer.value = draft.reviewer || '';
  els.bugSprint.value = draft.sprint || '';
  els.bugAdditionalNotes.value = draft.additional_notes || '';
  els.bugRootCause.value = draft.likely_root_cause || '';
  els.bugModalSeverityBadge.textContent = els.bugSeverity.value;
  els.bugModalSeverityBadge.className = `modal-priority-badge priority-badge ${els.bugSeverity.value === 'Critical' ? 'High' : els.bugSeverity.value}`;
}

async function openBugModal(testCaseId) {
  const tc = findTestCase(testCaseId);
  if (!tc) return;
  if (tc.jira_bug_id) {
    showToast('Bug already raised for this test case.', 'info');
    return;
  }
  if (tc.status !== 'Failed') {
    showToast('Bug can be raised only for failed test cases.', 'error');
    return;
  }

  state.activeBugTestCaseId = testCaseId;
  els.bugModalTcId.textContent = testCaseId;
  els.bugModalOverlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  setBugModalLoading(false);
  fillBugModal({
    bug_summary: tc.title,
    description: `Failure observed while executing ${tc.id}.`,
    steps_to_reproduce: tc.steps,
    actual_result: tc.execution_notes || tc.actual_result || '',
    expected_result: tc.expected_result,
    severity: 'Medium',
    environment: 'QA',
    project: state.lastSelectedProjects.join(', '),
    module: state.lastSelectedModules.join(', '),
    classification: 'Functionality',
    type: inferBugType(tc),
    device_type: inferDeviceType(),
    impacted_areas: state.lastSelectedModules.join(', '),
    vertical: inferVertical(),
  });

  try {
    const res = await fetch(`${API_BASE}/api/jira/bug-draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        test_case: tc,
        selected_projects: state.lastSelectedProjects,
        selected_modules: state.lastSelectedModules,
        execution_notes: tc.execution_notes || '',
        tester_notes: tc.tester_comments || '',
        source_info: state.lastSourceInfo || {},
      }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Could not generate bug draft');
    fillBugModal(await res.json());
  } catch (err) {
    showToast(`Using local bug draft: ${err.message}`, 'info');
  }
}

function closeBugModal() {
  els.bugModalOverlay.classList.add('hidden');
  state.activeBugTestCaseId = null;
  document.body.style.overflow = '';
}

function parseBugSteps() {
  return els.bugSteps.value
    .split(/\n+/)
    .map((line) => line.replace(/^\s*\d+\.\s*/, '').trim())
    .filter(Boolean);
}

function inferBugType(tc) {
  const text = [tc.title, tc.test_type, ...(tc.tags || []), ...state.lastSelectedProjects, ...state.lastSelectedModules].join(' ').toLowerCase();
  if (text.includes('api')) return 'API';
  if (text.includes('backend')) return 'Backend';
  if (text.includes('app') || text.includes('mobile')) return 'Mobile';
  return 'Frontend';
}

function inferDeviceType() {
  return state.lastSelectedProjects.join(' ').toLowerCase().includes('app') ? 'Mobile' : 'Web';
}

function inferVertical() {
  return state.lastSelectedProjects.join(' ').toLowerCase().includes('marketplace') ? 'Marketplace' : 'Residential';
}

async function submitJiraBug() {
  const tc = findTestCase(state.activeBugTestCaseId);
  if (!tc) return;
  if (tc.jira_bug_id) {
    showToast('Bug already raised for this test case.', 'info');
    closeBugModal();
    return;
  }

  const required = [
    [els.bugSummary.value.trim(), 'Bug Summary'],
    [els.bugDescription.value.trim(), 'Description'],
    [els.bugActual.value.trim(), 'Actual Result'],
    [els.bugExpected.value.trim(), 'Expected Result'],
  ];
  const missing = required.find(([value]) => !value);
  if (missing) {
    showToast(`${missing[1]} is required.`, 'error');
    return;
  }

  setBugModalLoading(true);
  try {
    const res = await fetch(`${API_BASE}/api/jira/create-bug`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        test_case_id: tc.id,
        source_issue_key: getSourceIssueKey(),
        bug_summary: els.bugSummary.value.trim(),
        description: els.bugDescription.value.trim(),
        steps_to_reproduce: parseBugSteps(),
        actual_result: els.bugActual.value.trim(),
        expected_result: els.bugExpected.value.trim(),
        severity: els.bugSeverity.value,
        environment: els.bugEnvironment.value.trim(),
        project: els.bugProject.value.trim(),
        module: els.bugModule.value.trim(),
        classification: els.bugClassification.value.trim(),
        type: els.bugType.value,
        device_type: els.bugDeviceType.value,
        impacted_areas: els.bugImpacted.value.trim(),
        app_version: els.bugAppVersion.value.trim(),
        vertical: els.bugVertical.value.trim(),
        reviewer: els.bugReviewer.value.trim(),
        sprint: els.bugSprint.value.trim(),
        additional_notes: els.bugAdditionalNotes.value.trim(),
        likely_root_cause: els.bugRootCause.value.trim(),
        attachments: [],
      }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Jira bug creation failed');
    const data = await res.json();
    tc.jira_bug_id = data.issue_key;
    tc.jira_bug_url = data.issue_url;
    saveExecutionSession();
    closeBugModal();
    renderTable(state.testCases);
    showToast(`Bug created successfully: ${data.issue_key}`, 'success');
  } catch (err) {
    showToast(err.message || 'Could not create Jira bug.', 'error');
  } finally {
    setBugModalLoading(false);
  }
}

els.bugSeverity.addEventListener('change', () => {
  els.bugModalSeverityBadge.textContent = els.bugSeverity.value;
  els.bugModalSeverityBadge.className = `modal-priority-badge priority-badge ${els.bugSeverity.value === 'Critical' ? 'High' : els.bugSeverity.value}`;
});

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
  state.lastSummary = null;
  state.lastSourceInfo = {};
  state.lastSelectedProjects = [];
  state.lastSelectedModules = [];
  localStorage.removeItem(SESSION_STORAGE_KEY);
  clearProjects();
  clearModules();
  els.jiraId.value = '';
  els.clickupTaskId.value = '';
  els.clickupPreview.classList.add('hidden');
  els.jiraPreview.classList.add('hidden');
  els.statsPanel.classList.add('hidden');
  updateGenerateButton();
}

function saveExecutionSession() {
  if (!state.testCases.length) return;
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({
    testCases: state.testCases,
    lastSummary: state.lastSummary,
    lastSourceType: state.lastSourceType,
    lastSelectedProjects: state.lastSelectedProjects,
    lastSelectedModules: state.lastSelectedModules,
    lastSourceInfo: state.lastSourceInfo,
  }));
}

function restoreExecutionSession() {
  const raw = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!raw) return false;
  try {
    const saved = JSON.parse(raw);
    if (!Array.isArray(saved.testCases) || !saved.testCases.length) return false;
    state.testCases = saved.testCases.map(normalizeExecutionState);
    state.lastSummary = saved.lastSummary;
    state.lastSourceType = saved.lastSourceType || 'text';
    state.lastSelectedProjects = saved.lastSelectedProjects || [];
    state.lastSelectedModules = saved.lastSelectedModules || [];
    state.lastSourceInfo = saved.lastSourceInfo || {};
    renderResults({ test_cases: state.testCases, summary: state.lastSummary || { total: state.testCases.length, high_priority: 0, medium_priority: 0, low_priority: 0, module_detected: 'Restored' } });
    showPanel('results');
    switchView('testcases');
    return true;
  } catch {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    return false;
  }
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
    updateGenerateButton();
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
(async function init() {
  showPanel('empty');
  loadManagedOptions('project');
  loadManagedOptions('module');
  renderModuleSelector();
  renderProjectSelector();
  updateGenerateButton();
  checkHealth();
  const user = await requireCurrentUser();
  if (user) {
    restoreExecutionSession();
    loadIntegrationStatus();
    loadHistoryCount();
  }
})();
