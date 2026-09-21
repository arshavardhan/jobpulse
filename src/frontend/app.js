/**
 * JobPulse - Real jobs. Live opportunities. One place.
 * High-performance Frontend Application Engine
 */

// ============================================================================
// GLOBAL APPLICATION STATE
// ============================================================================
let currentUser = null;
let currentToken = localStorage.getItem('jobcopilot_token') || null;
let activeView = 'discover';

// Cached Data Collections
let allLiveJobs = [];
let indiaJobsCache = [];
let remoteJobsCache = [];
let freshersJobsCache = [];
let savedJobsCache = [];
let companiesCache = [];

// Filter States
let currentDiscoverScope = 'all';
let currentIndiaCity = 'all';
let currentIndiaFresherOnly = false;
let currentSearchQuery = '';
let currentLocationQuery = '';
let currentWorkplace = 'all';
let currentExperience = 'all';
let currentSource = 'all';
let currentSortBy = 'recent';
let currentDomain = 'all';

// Active Modals & Audit State
let currentDetailJob = null;
let lastTailoredBullets = [];

// ============================================================================
// INITIALIZATION & LIFECYCLE
// ============================================================================
document.addEventListener('DOMContentLoaded', async () => {
  // 1. Check Auth
  if (currentToken) {
    await fetchCurrentUser();
  } else {
    updateAuthNavUI();
  }

  // 2. Fetch System Summary for Hero Stats
  fetchSystemMetrics();

  // 3. Routing (Default to Home Landing Page)
  const initialHash = window.location.hash.replace('#', '') || 'home';
  switchView(initialHash, false);

  window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '') || 'home';
    switchView(hash, false);
  });

  // 4. Close dropdown on outside click
  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('user-dropdown-menu');
    const userPill = document.getElementById('auth-logged-in-state');
    if (dropdown && userPill && !userPill.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });
});

// Toast Notifications
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const bg = type === 'success' ? 'bg-emerald-950/90 border-emerald-500/40 text-emerald-300' :
             type === 'error' ? 'bg-rose-950/90 border-rose-500/40 text-rose-300' :
             'bg-indigo-950/90 border-indigo-500/40 text-indigo-300';

  const icon = type === 'success' ? 'fa-circle-check' :
               type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-info';

  toast.className = `flex items-center space-x-2.5 px-4 py-2.5 rounded-xl border shadow-xl backdrop-blur-md text-xs pointer-events-auto transition transform translate-y-2 opacity-0 duration-200 ${bg}`;
  toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// Auth Headers Helper
function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (currentToken) {
    headers['Authorization'] = `Bearer ${currentToken}`;
  }
  return headers;
}

// Copy to Clipboard Helper
function copyToClipboard(text, successMsg = 'Copied to clipboard!') {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => showToast(successMsg, 'success'));
  } else {
    const tempInput = document.createElement('textarea');
    tempInput.value = text;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);
    showToast(successMsg, 'success');
  }
}

// Format Date Helper
function formatDate(dateStr) {
  if (!dateStr) return 'Recently';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return 'Recently';
    const now = new Date();
    const diffHours = Math.round((now - d) / (1000 * 60 * 60));
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.round(diffHours / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch (e) {
    return 'Recently';
  }
}

// Format Percent
function fmtPct(val) {
  if (val == null || isNaN(val)) return '--%';
  const num = Number(val);
  if (num > 1) {
    return `${Math.min(100, Math.round(num))}%`;
  }
  return `${Math.min(100, Math.round(num * 100))}%`;
}

// ============================================================================
// ROUTING & NAVIGATION
// ============================================================================
function scrollToHomeBot() {
  switchView('home');
  setTimeout(() => {
    const el = document.getElementById('home-bot-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, 100);
}

function switchView(viewId, updateHash = true) {
  const validViews = [
    'home', 'agent', 'discover', 'india', 'remote', 'freshers', 'companies',
    'ats', 'sources', 'about', 'contact', 'support', 'saved', 'profile', 'tracker'
  ];
  if (viewId === 'outreach') {
    openRecruiterOutreach();
    return;
  }
  if (!validViews.includes(viewId)) {
    viewId = 'home';
  }
  activeView = viewId;

  if (updateHash) {
    window.location.hash = viewId;
  }

  if (viewId === 'about' || viewId === 'support' || viewId === 'contact') {
    scrollToBottomSection(viewId);
    return;
  }

  // Update Nav Button Active Classes
  document.querySelectorAll('nav button').forEach(btn => {
    btn.classList.remove('nav-btn-active');
  });
  const activeNavBtn = document.getElementById(`nav-btn-${viewId}`);
  if (activeNavBtn) {
    activeNavBtn.classList.add('nav-btn-active');
  }

  // Hide all view sections and display active one
  document.querySelectorAll('main > section').forEach(sec => {
    sec.classList.add('hidden');
  });
  const activeSec = document.getElementById(`view-${viewId}`);
  if (activeSec) {
    activeSec.classList.remove('hidden');
  }

  // Close Mobile Drawer if open
  const drawerPanel = document.getElementById('mobile-drawer-panel');
  const drawerBackdrop = document.getElementById('mobile-drawer-backdrop');
  if (drawerPanel && !drawerPanel.classList.contains('drawer-hidden')) {
    toggleMobileMenu();
  }

  // Trigger View Loaders
  if (viewId === 'home') {
    fetchSystemMetrics();
  } else if (viewId === 'agent') {
    loadAgentView();
  } else if (viewId === 'discover') {
    loadDiscoverJobs();
  } else if (viewId === 'india') {
    loadIndiaJobs();
  } else if (viewId === 'remote') {
    loadRemoteJobs();
  } else if (viewId === 'freshers') {
    loadFreshersJobs();
  } else if (viewId === 'companies') {
    loadCompaniesDirectory();
  } else if (viewId === 'sources') {
    loadSourceHealthData();
  } else if (viewId === 'saved') {
    loadSavedJobs();
  } else if (viewId === 'profile') {
    loadUserProfile();
  } else if (viewId === 'tracker') {
    loadTrackerBoard();
  }
}

function scrollToBottomSection(sectionKey) {
  const el = document.getElementById(`section-${sectionKey}`);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function toggleMobileMenu() {
  const panel = document.getElementById('mobile-drawer-panel');
  const backdrop = document.getElementById('mobile-drawer-backdrop');
  if (panel && backdrop) {
    panel.classList.toggle('drawer-hidden');
    backdrop.classList.toggle('hidden');
  }
}

// ============================================================================
// SYSTEM METRICS & SUMMARY
// ============================================================================
async function fetchSystemMetrics() {
  try {
    const res = await fetch('/api/system/status');
    if (res.ok) {
      const data = await res.json();
      const count = data.jobs_in_database || 71;
      const homeActive = document.getElementById('home-stat-active-jobs');
      if (homeActive) {
        homeActive.textContent = `${count}+`;
      }
      const homeSources = document.getElementById('home-stat-sources');
      if (homeSources) {
        const srcCount = (data.available_sources || []).length || 35;
        homeSources.textContent = `${srcCount}+`;
      }
    }
  } catch (err) {
    console.warn('System status fetch deferred:', err);
  }
}

// ============================================================================
// AUTHENTICATION WORKFLOW
// ============================================================================
async function fetchCurrentUser() {
  if (!currentToken) return;
  try {
    const res = await fetch('/api/auth/me', { headers: getAuthHeaders() });
    if (res.ok) {
      currentUser = await res.json();
      updateAuthNavUI();
      updateSavedBadge(currentUser.saved_jobs_count || 0);
    } else {
      handleLogout(false);
    }
  } catch (err) {
    console.error('Failed to retrieve user profile:', err);
  }
}

function updateAuthNavUI() {
  const loggedOut = document.getElementById('auth-logged-out-state');
  const loggedIn = document.getElementById('auth-logged-in-state');

  if (currentUser) {
    if (loggedOut) loggedOut.classList.add('hidden');
    if (loggedIn) loggedIn.classList.remove('hidden');

    const nameEl = document.getElementById('nav-user-name');
    const avatarEl = document.getElementById('nav-user-avatar');
    const dropNameEl = document.getElementById('dropdown-user-fullname');
    const dropEmailEl = document.getElementById('dropdown-user-email');

    if (nameEl) nameEl.textContent = currentUser.full_name || 'Candidate';
    if (dropNameEl) dropNameEl.textContent = currentUser.full_name || 'Candidate';
    if (dropEmailEl) dropEmailEl.textContent = currentUser.email || '';
    if (avatarEl) {
      avatarEl.textContent = (currentUser.full_name || 'C').trim().charAt(0).toUpperCase();
    }
  } else {
    if (loggedOut) loggedOut.classList.remove('hidden');
    if (loggedIn) loggedIn.classList.add('hidden');
  }
}

function updateSavedBadge(count) {
  const badge = document.getElementById('nav-saved-count-badge');
  if (badge) {
    badge.textContent = count;
    if (count > 0) {
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  }
}

function toggleUserDropdown() {
  const menu = document.getElementById('user-dropdown-menu');
  if (menu) menu.classList.toggle('hidden');
}

function closeUserDropdown() {
  const menu = document.getElementById('user-dropdown-menu');
  if (menu) menu.classList.add('hidden');
}

function openAuthModal(tab = 'login') {
  switchAuthTab(tab);
  document.getElementById('auth-modal').classList.remove('hidden');
}

function closeAuthModal() {
  document.getElementById('auth-modal').classList.add('hidden');
}

function switchAuthTab(tab) {
  const isLogin = tab === 'login';
  const tabLogin = document.getElementById('tab-btn-login');
  const tabReg = document.getElementById('tab-btn-register');
  const formLogin = document.getElementById('auth-login-form');
  const formReg = document.getElementById('auth-register-form');

  if (isLogin) {
    tabLogin.className = 'py-1.5 text-xs font-semibold rounded-lg text-white bg-indigo-600 transition';
    tabReg.className = 'py-1.5 text-xs font-semibold rounded-lg text-slate-400 transition';
    formLogin.classList.remove('hidden');
    formReg.classList.add('hidden');
  } else {
    tabReg.className = 'py-1.5 text-xs font-semibold rounded-lg text-white bg-indigo-600 transition';
    tabLogin.className = 'py-1.5 text-xs font-semibold rounded-lg text-slate-400 transition';
    formReg.classList.remove('hidden');
    formLogin.classList.add('hidden');
  }
}

async function handleAuthLogin(event) {
  event.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || 'Authentication failed', 'error');
      return;
    }

    currentToken = data.access_token;
    localStorage.setItem('jobcopilot_token', currentToken);
    currentUser = data.user;
    updateAuthNavUI();
    updateSavedBadge(currentUser.saved_jobs_count || 0);
    closeAuthModal();
    showToast(`Welcome back, ${currentUser.full_name || 'Candidate'}!`, 'success');
  } catch (err) {
    showToast('Network error during login', 'error');
  }
}

async function handleAuthRegister(event) {
  event.preventDefault();
  const full_name = document.getElementById('reg-name').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const preferred_role = document.getElementById('reg-role').value.trim();

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name, email, password, preferred_role })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || 'Registration failed', 'error');
      return;
    }

    currentToken = data.access_token;
    localStorage.setItem('jobcopilot_token', currentToken);
    currentUser = data.user;
    updateAuthNavUI();
    closeAuthModal();
    showToast(`Account registered successfully! Welcome to JobPulse.`, 'success');
  } catch (err) {
    showToast('Network error during registration', 'error');
  }
}

function handleLogout(showNotification = true) {
  currentToken = null;
  currentUser = null;
  localStorage.removeItem('jobcopilot_token');
  updateAuthNavUI();
  updateSavedBadge(0);
  closeUserDropdown();
  if (showNotification) {
    showToast('You have signed out.', 'info');
  }
  if (activeView === 'saved' || activeView === 'profile') {
    switchView('discover');
  }
}

// ============================================================================
// JOB CARD COMPONENT BUILDER
// ============================================================================
function buildCanonicalBadge(job) {
  const src = (job.canonical_source || job.source || '').toLowerCase();
  if (src.includes('lever') || src.includes('greenhouse') || src.includes('ashby') || src.includes('workable')) {
    return `<span class="badge-direct-ats"><i class="fa-solid fa-shield-check text-emerald-400"></i>Direct Employer ATS</span>`;
  }
  if (src.includes('hasjob')) {
    return `<span class="badge-direct-ats"><i class="fa-solid fa-check-circle text-amber-400"></i>Hasjob India</span>`;
  }
  return `<span class="badge-verified-live"><i class="fa-solid fa-bolt text-emerald-400"></i>${job.source_name || job.source}</span>`;
}

function renderJobCard(job, isSavedView = false) {
  const isSaved = job.is_saved || savedJobsCache.some(sj => sj.id === job.id);
  const bookmarkIcon = isSaved ? 'fa-solid text-amber-400' : 'fa-regular text-slate-400 hover:text-amber-400';
  const canonicalBadge = buildCanonicalBadge(job);

  const skillsList = (job.skills || job.skills_required || []).slice(0, 4);
  const skillsHtml = skillsList.length > 0
    ? skillsList.map(s => `<span class="px-2 py-0.5 rounded bg-[#1e293b] text-slate-300 text-[10px] font-medium">${s}</span>`).join('')
    : `<span class="text-[10px] text-slate-500">Verified Technical Role</span>`;

  const fresherBadge = job.is_fresher
    ? `<span class="px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/30 text-emerald-300 text-[10px] font-bold">🎓 Fresher (0-2 Yrs)</span>`
    : '';

  const remoteBadge = job.remote || job.is_remote
    ? `<span class="px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/30 text-cyan-300 text-[10px] font-semibold">🌐 Remote</span>`
    : `<span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">🏢 ${job.city || job.location || 'Onsite'}</span>`;

  const domainIcons = {
    'Product': 'fa-solid fa-bullseye text-amber-400',
    'Design': 'fa-solid fa-wand-magic-sparkles text-pink-400',
    'Data & AI': 'fa-solid fa-brain text-purple-400',
    'Marketing': 'fa-solid fa-chart-line text-blue-400',
    'Sales': 'fa-solid fa-briefcase text-emerald-400',
    'Operations & HR': 'fa-solid fa-users text-teal-400',
    'Finance': 'fa-solid fa-coins text-yellow-400',
    'Customer Support': 'fa-solid fa-headset text-cyan-400',
    'QA': 'fa-solid fa-vial text-rose-400',
    'Engineering': 'fa-solid fa-code text-cyan-400'
  };
  const domName = job.role_domain || 'Engineering';
  const domIcon = domainIcons[domName] || 'fa-solid fa-layer-group text-slate-400';
  const domainBadge = `<span class="px-2 py-0.5 rounded bg-[#06080d] border border-[#223048] text-slate-300 text-[10px] font-medium"><i class="${domIcon} mr-1"></i>${domName}</span>`;

  return `
    <div class="job-card" id="job-card-${job.id}">
      <div>
        <div class="flex items-start justify-between gap-2 mb-2">
          <div>
            <div class="flex items-center space-x-2 flex-wrap gap-y-1 mb-1">
              <span class="text-xs font-bold text-white">${job.company}</span>
              ${canonicalBadge}
            </div>
            <h4 class="text-sm sm:text-base font-bold text-white hover:text-indigo-300 cursor-pointer transition line-clamp-1" onclick="openJobDetailsModal('${job.id}')">
              ${job.title}
            </h4>
          </div>
          <button onclick="toggleSaveJob(event, '${job.id}')" class="p-1.5 rounded-lg text-sm transition" title="${isSaved ? 'Remove from saved' : 'Save job'}">
            <i class="${bookmarkIcon} fa-bookmark"></i>
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-1.5 mb-3 text-xs">
          ${remoteBadge}
          ${fresherBadge}
          ${domainBadge}
          <span class="text-[10px] text-slate-500 ml-auto font-medium">${formatDate(job.published_at || job.first_seen_at)}</span>
        </div>

        <div class="flex flex-wrap gap-1 mb-4">
          ${skillsHtml}
        </div>
      </div>

      <div class="pt-3 border-t border-[#1e293b] flex items-center justify-between gap-2">
        <button onclick="openJobDetailsModal('${job.id}')" class="text-xs text-slate-400 hover:text-white font-medium flex items-center space-x-1 transition">
          <span>Details</span>
          <i class="fa-solid fa-chevron-right text-[10px]"></i>
        </button>

        <div class="flex items-center space-x-1.5">
          <button onclick="openLatexResumeModal('${job.id}')" class="px-2 py-1 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center space-x-1 transition" title="Generate ATS Overleaf / LaTeX Resume">
            <i class="fa-solid fa-file-code text-[11px]"></i>
            <span>LaTeX</span>
          </button>
          <button onclick="openCopilotModal('${job.id}')" class="px-2.5 py-1 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 text-cyan-300 text-xs font-semibold flex items-center space-x-1 transition" title="1-Click Auto-Apply Copilot">
            <i class="fa-solid fa-bolt text-yellow-400 text-[11px]"></i>
            <span>Auto-Apply</span>
          </button>
          <a href="${job.apply_url}" target="_blank" rel="noopener noreferrer" class="link-direct-apply">
            <span>Apply Direct</span>
            <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
          </a>
        </div>
      </div>
    </div>
  `;
}

// ============================================================================
// VIEW 1: DISCOVER LIVE JOBS
// ============================================================================
async function loadDiscoverJobs(forceHunt = false) {
  const loading = document.getElementById('discover-loading');
  const grid = document.getElementById('discover-jobs-grid');
  const empty = document.getElementById('discover-empty-state');
  const countEl = document.getElementById('discover-job-count');

  if (loading) loading.classList.remove('hidden');
  if (grid) grid.innerHTML = '';
  if (empty) empty.classList.add('hidden');

  try {
    let url = '/api/jobs?limit=350';
    if (forceHunt) {
      url += '&hunt=true';
    }

    const res = await fetch(url, { headers: getAuthHeaders() });
    if (res.ok) {
      allLiveJobs = await res.json();
      applyAndRenderDiscoverJobs();
    } else {
      showToast('Failed to load live jobs', 'error');
    }
  } catch (err) {
    showToast('Network error loading jobs', 'error');
  } finally {
    if (loading) loading.classList.add('hidden');
  }
}

function applyAndRenderDiscoverJobs() {
  const grid = document.getElementById('discover-jobs-grid');
  const empty = document.getElementById('discover-empty-state');
  const countEl = document.getElementById('discover-job-count');
  if (!grid) return;

  let filtered = [...allLiveJobs];

  // 0. Role Domain Filter
  if (currentDomain && currentDomain !== 'all') {
    const target = currentDomain.toLowerCase();
    filtered = filtered.filter(j => {
      const d = (j.role_domain || '').toLowerCase();
      const t = (j.title || '').toLowerCase();
      return d.includes(target) || t.includes(target);
    });
  }

  // 1. Scope Filter
  if (currentDiscoverScope === 'india') {
    filtered = filtered.filter(j => (j.region === 'India') || (j.country === 'India') || ((j.city || '').length > 0));
  } else if (currentDiscoverScope === 'remote') {
    filtered = filtered.filter(j => j.remote || j.is_remote);
  } else if (currentDiscoverScope === 'fresher') {
    filtered = filtered.filter(j => j.is_fresher);
  }

  // 2. Search Query Filter
  if (currentSearchQuery) {
    const q = currentSearchQuery.toLowerCase();
    filtered = filtered.filter(j =>
      (j.title || '').toLowerCase().includes(q) ||
      (j.company || '').toLowerCase().includes(q) ||
      (j.skills || []).some(s => s.toLowerCase().includes(q))
    );
  }

  // 3. Location Query Filter
  if (currentLocationQuery) {
    const loc = currentLocationQuery.toLowerCase();
    filtered = filtered.filter(j =>
      (j.location || '').toLowerCase().includes(loc) ||
      (j.city || '').toLowerCase().includes(loc) ||
      (j.country || '').toLowerCase().includes(loc)
    );
  }

  // 4. Workplace Arrangement
  if (currentWorkplace === 'remote') {
    filtered = filtered.filter(j => j.remote || j.is_remote);
  } else if (currentWorkplace === 'onsite') {
    filtered = filtered.filter(j => !(j.remote || j.is_remote));
  }

  // 5. Seniority
  if (currentExperience === 'fresher') {
    filtered = filtered.filter(j => j.is_fresher);
  } else if (currentExperience === 'mid') {
    filtered = filtered.filter(j => (j.experience_level || '').toLowerCase().includes('mid'));
  } else if (currentExperience === 'senior') {
    filtered = filtered.filter(j => (j.experience_level || '').toLowerCase().includes('senior'));
  }

  // 6. Source Filter
  if (currentSource === 'direct_ats') {
    filtered = filtered.filter(j => {
      const s = (j.canonical_source || j.source || '').toLowerCase();
      return s.includes('lever') || s.includes('greenhouse') || s.includes('ashby') || s.includes('workable');
    });
  } else if (currentSource !== 'all') {
    filtered = filtered.filter(j => (j.source || '').toLowerCase().includes(currentSource.toLowerCase()));
  }

  // 7. Sort
  if (currentSortBy === 'company') {
    filtered.sort((a, b) => (a.company || '').localeCompare(b.company || ''));
  } else if (currentSortBy === 'title') {
    filtered.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
  } else {
    // recent
    filtered.sort((a, b) => new Date(b.published_at || b.first_seen_at || 0) - new Date(a.published_at || a.first_seen_at || 0));
  }

  if (countEl) countEl.textContent = filtered.length;

  if (filtered.length === 0) {
    grid.innerHTML = '';
    if (empty) empty.classList.remove('hidden');
  } else {
    if (empty) empty.classList.add('hidden');
    grid.innerHTML = filtered.map(job => renderJobCard(job)).join('');
  }
}

function setDiscoverScope(scope) {
  currentDiscoverScope = scope;
  ['all', 'india', 'remote', 'fresher'].forEach(s => {
    const btn = document.getElementById(`scope-btn-${s}`);
    if (btn) {
      if (s === scope) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
  });
  applyAndRenderDiscoverJobs();
}

function applyQuickDomain(domain) {
  currentDomain = domain;
  document.querySelectorAll('[id^="domain-pill-"]').forEach(pill => {
    pill.classList.remove('active');
  });
  const safeId = domain.replace(/[\s&]+/g, '-');
  const activePill = document.getElementById(`domain-pill-${safeId}`) || document.getElementById(`domain-pill-${domain}`);
  if (activePill) activePill.classList.add('active');

  const sel = document.getElementById('filter-domain');
  if (sel) sel.value = domain;

  applyAndRenderDiscoverJobs();
}

function applySidebarFilters() {
  const wp = document.getElementById('filter-workplace');
  const exp = document.getElementById('filter-experience');
  const src = document.getElementById('filter-source');
  const dom = document.getElementById('filter-domain');

  if (wp) currentWorkplace = wp.value;
  if (exp) currentExperience = exp.value;
  if (src) currentSource = src.value;
  if (dom) {
    currentDomain = dom.value;
    document.querySelectorAll('[id^="domain-pill-"]').forEach(pill => {
      pill.classList.remove('active');
    });
    const safeId = dom.value.replace(/[\s&]+/g, '-');
    const activePill = document.getElementById(`domain-pill-${safeId}`) || document.getElementById(`domain-pill-${dom.value}`);
    if (activePill) activePill.classList.add('active');
  }

  applyAndRenderDiscoverJobs();
}

function handleJobSortChange() {
  const sortSel = document.getElementById('sort-jobs-select');
  if (sortSel) {
    currentSortBy = sortSel.value;
    applyAndRenderDiscoverJobs();
  }
}

function resetAllFilters() {
  currentDiscoverScope = 'all';
  currentDomain = 'all';
  currentSearchQuery = '';
  currentLocationQuery = '';
  currentWorkplace = 'all';
  currentExperience = 'all';
  currentSource = 'all';
  currentSortBy = 'recent';

  const heroSearch = document.getElementById('hero-search-input');
  const heroLoc = document.getElementById('hero-location-input');
  const wp = document.getElementById('filter-workplace');
  const exp = document.getElementById('filter-experience');
  const src = document.getElementById('filter-source');
  const dom = document.getElementById('filter-domain');
  const sortSel = document.getElementById('sort-jobs-select');

  if (heroSearch) heroSearch.value = '';
  if (heroLoc) heroLoc.value = '';
  if (wp) wp.value = 'all';
  if (exp) exp.value = 'all';
  if (src) src.value = 'all';
  if (dom) dom.value = 'all';
  if (sortSel) sortSel.value = 'recent';

  document.querySelectorAll('[id^="domain-pill-"]').forEach(pill => {
    pill.classList.remove('active');
  });
  const allPill = document.getElementById('domain-pill-all');
  if (allPill) allPill.classList.add('active');

  setDiscoverScope('all');
  applyAndRenderDiscoverJobs();
}

function executeHeroSearch() {
  const heroSearch = document.getElementById('hero-search-input');
  const heroLoc = document.getElementById('hero-location-input');

  currentSearchQuery = heroSearch ? heroSearch.value.trim() : '';
  currentLocationQuery = heroLoc ? heroLoc.value.trim() : '';

  if (activeView !== 'discover') {
    switchView('discover');
  } else {
    applyAndRenderDiscoverJobs();
  }
}

function applyQuickRole(role) {
  const heroSearch = document.getElementById('hero-search-input');
  if (heroSearch) {
    heroSearch.value = role;
    executeHeroSearch();
  }
}

async function triggerLiveDiscoveryHunt() {
  showToast('Connecting to genuine external live job feeds...', 'info');
  await loadDiscoverJobs(true);
  showToast('Live discovery hunt complete! Verified listings refreshed.', 'success');
}

// ============================================================================
// VIEW 2: INDIA TECHNOLOGY HUB
// ============================================================================
async function loadIndiaJobs() {
  const grid = document.getElementById('india-jobs-grid');
  if (!grid) return;
  grid.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400"><i class="fa-solid fa-circle-notch animate-spin mr-2"></i>Loading India openings...</div>';

  try {
    const res = await fetch('/api/jobs?region=India&limit=80', { headers: getAuthHeaders() });
    if (res.ok) {
      indiaJobsCache = await res.json();
      renderIndiaJobs();
    }
  } catch (err) {
    grid.innerHTML = '<div class="col-span-full py-12 text-center text-rose-400">Failed to load India opportunities.</div>';
  }
}

function renderIndiaJobs() {
  const grid = document.getElementById('india-jobs-grid');
  if (!grid) return;

  let filtered = [...indiaJobsCache];
  if (currentIndiaCity !== 'all') {
    filtered = filtered.filter(j => (j.city || j.location || '').toLowerCase().includes(currentIndiaCity.toLowerCase()));
  }
  if (currentIndiaFresherOnly) {
    filtered = filtered.filter(j => j.is_fresher);
  }

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full py-12 text-center bg-[#0f172a] rounded-2xl border border-[#1e293b]">
        <p class="text-xs text-slate-400">No jobs matching city "${currentIndiaCity}". Try switching to All India.</p>
      </div>`;
    return;
  }

  grid.innerHTML = filtered.map(job => renderJobCard(job)).join('');
}

function filterIndiaByCity(city) {
  currentIndiaCity = city;
  document.querySelectorAll('.india-city-pill').forEach(btn => {
    if (btn.getAttribute('data-city') === city) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  renderIndiaJobs();
}

function toggleIndiaFresherOnly() {
  currentIndiaFresherOnly = !currentIndiaFresherOnly;
  const toggleBtn = document.getElementById('india-fresher-toggle');
  if (toggleBtn) {
    if (currentIndiaFresherOnly) {
      toggleBtn.classList.add('active');
    } else {
      toggleBtn.classList.remove('active');
    }
  }
  renderIndiaJobs();
}

// ============================================================================
// VIEW 3: REMOTE OPPORTUNITIES
// ============================================================================
async function loadRemoteJobs() {
  const grid = document.getElementById('remote-jobs-grid');
  if (!grid) return;
  grid.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400"><i class="fa-solid fa-circle-notch animate-spin mr-2"></i>Loading remote opportunities...</div>';

  try {
    const res = await fetch('/api/jobs?remote=true&limit=80', { headers: getAuthHeaders() });
    if (res.ok) {
      remoteJobsCache = await res.json();
      grid.innerHTML = remoteJobsCache.map(job => renderJobCard(job)).join('');
    }
  } catch (err) {
    grid.innerHTML = '<div class="col-span-full py-12 text-center text-rose-400">Failed to load remote jobs.</div>';
  }
}

// ============================================================================
// VIEW 4: FRESHERS & EARLY CAREER
// ============================================================================
async function loadFreshersJobs() {
  const grid = document.getElementById('freshers-jobs-grid');
  if (!grid) return;
  grid.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400"><i class="fa-solid fa-circle-notch animate-spin mr-2"></i>Loading entry-level & fresher roles...</div>';

  try {
    const res = await fetch('/api/jobs?is_fresher=true&limit=80', { headers: getAuthHeaders() });
    if (res.ok) {
      freshersJobsCache = await res.json();
      grid.innerHTML = freshersJobsCache.map(job => renderJobCard(job)).join('');
    }
  } catch (err) {
    grid.innerHTML = '<div class="col-span-full py-12 text-center text-rose-400">Failed to load fresher jobs.</div>';
  }
}

// ============================================================================
// VIEW 5: COMPANIES DIRECTORY
// ============================================================================
async function loadCompaniesDirectory() {
  const grid = document.getElementById('companies-grid');
  if (!grid) return;
  grid.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400"><i class="fa-solid fa-circle-notch animate-spin mr-2"></i>Loading tracked companies directory...</div>';

  try {
    const res = await fetch('/api/companies');
    if (res.ok) {
      companiesCache = await res.json();
      renderCompaniesCards(companiesCache);
    } else {
      grid.innerHTML = '<div class="col-span-full py-12 text-center text-rose-400">Failed to load companies.</div>';
    }
  } catch (err) {
    grid.innerHTML = '<div class="col-span-full py-12 text-center text-rose-400">Network error loading companies.</div>';
  }
}

function renderCompaniesCards(companies) {
  const grid = document.getElementById('companies-grid');
  if (!grid) return;

  if (companies.length === 0) {
    grid.innerHTML = '<div class="col-span-full py-12 text-center text-slate-500">No companies found.</div>';
    return;
  }

  grid.innerHTML = companies.map(comp => {
    const locations = (comp.primary_locations || []).slice(0, 3).join(', ') || 'Global';
    const skills = (comp.top_skills || []).slice(0, 4).map(s => `<span class="px-2 py-0.5 rounded bg-[#1e293b] text-slate-300 text-[10px]">${s}</span>`).join('');
    const sampleRoles = (comp.sample_roles || []).slice(0, 2).map(r => `<span class="text-[11px] text-slate-400 block truncate">&bull; ${r}</span>`).join('');

    return `
      <div class="bg-[#0f172a] rounded-2xl border border-[#1e293b] p-5 flex flex-col justify-between hover:border-slate-600 transition">
        <div>
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-base font-bold text-white">${comp.company_name}</h4>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              ${comp.job_count} Live Openings
            </span>
          </div>

          <p class="text-xs text-slate-400 mb-3 flex items-center">
            <i class="fa-solid fa-location-dot text-[10px] mr-1.5 text-slate-500"></i>
            <span>${locations}</span>
          </p>

          ${sampleRoles ? `<div class="mb-3 space-y-0.5 bg-[#090d16] p-2 rounded-xl border border-[#1e293b]">${sampleRoles}</div>` : ''}

          <div class="flex flex-wrap gap-1 mb-4">
            ${skills}
          </div>
        </div>

        <button onclick="filterByCompany('${comp.company_name}')" class="w-full btn-outline-indigo text-xs py-2">
          <span>View ${comp.company_name} Openings</span>
          <i class="fa-solid fa-arrow-right text-[10px] ml-1"></i>
        </button>
      </div>
    `;
  }).join('');
}

function filterCompaniesList() {
  const query = (document.getElementById('companies-filter-input')?.value || '').toLowerCase();
  const filtered = companiesCache.filter(c =>
    (c.company_name || '').toLowerCase().includes(query) ||
    (c.top_skills || []).some(s => s.toLowerCase().includes(query))
  );
  renderCompaniesCards(filtered);
}

function filterByCompany(companyName) {
  currentSearchQuery = companyName;
  const heroSearch = document.getElementById('hero-search-input');
  if (heroSearch) heroSearch.value = companyName;
  switchView('discover');
}

// ============================================================================
// VIEW 6: ATS AUDIT & RESUME OPTIMIZER
// ============================================================================
function initAtsView() {
  // Pre-fill profile resume text if available
  if (currentUser && currentUser.summary) {
    const resumeInput = document.getElementById('ats-resume-input');
    if (resumeInput && !resumeInput.value.trim()) {
      resumeInput.value = currentUser.summary;
    }
  }
}

async function handleATSResumeFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const indicator = document.getElementById('pdf-parsing-indicator');
  if (indicator) indicator.classList.remove('hidden');

  try {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch('/api/resume/parse', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Could not extract clean text from document', 'error');
      return;
    }

    const data = await res.json();
    const resumeInput = document.getElementById('ats-resume-input');
    if (resumeInput) {
      resumeInput.value = data.clean_text || '';
    }

    // Auto-update experience level if detected
    if (data.skills && data.skills.length > 0) {
      const expLevelEl = document.getElementById('ats-experience-level');
      if (expLevelEl && data.years_of_experience != null) {
        if (data.years_of_experience < 2) {
          expLevelEl.value = 'Fresher / Entry';
        } else if (data.years_of_experience >= 5) {
          expLevelEl.value = 'Senior';
        } else {
          expLevelEl.value = 'Mid-Level';
        }
      }
    }

    const skillsCount = (data.skills || []).length;
    showToast(`Denoised & parsed ${file.name} cleanly! (${skillsCount} skills detected)`, 'success');
  } catch (err) {
    showToast('Network error parsing uploaded document', 'error');
  } finally {
    if (indicator) indicator.classList.add('hidden');
    event.target.value = '';
  }
}

async function runATSCheck() {
  const resumeText = document.getElementById('ats-resume-input')?.value.trim();
  const targetRole = document.getElementById('ats-target-role')?.value.trim();
  const experienceLevel = document.getElementById('ats-experience-level')?.value;
  const jobDesc = document.getElementById('ats-job-desc-input')?.value.trim();
  const btn = document.getElementById('btn-run-ats');

  if (!resumeText) {
    showToast('Please paste or upload your resume text to begin audit.', 'error');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch animate-spin mr-1.5"></i>Analyzing ATS Compliance...';
  }

  try {
    const payload = {
      resume_text: resumeText,
      target_role: targetRole || 'Software Engineer',
      experience_level: experienceLevel || 'Mid-Level',
      job_description: jobDesc || null
    };

    const res = await fetch('/api/ats-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'ATS audit failed', 'error');
      return;
    }

    const data = await res.json();
    renderATSResults(data);
    showToast('ATS diagnostic audit completed successfully!', 'success');
  } catch (err) {
    showToast('Network error analyzing ATS compliance', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles mr-1.5"></i>Analyze ATS Compliance &amp; Generate Tailored Bullets';
    }
  }
}

function renderATSResults(data) {
  const statusBadge = document.getElementById('ats-status-badge');
  if (statusBadge) {
    statusBadge.textContent = 'Diagnostic Complete';
    statusBadge.className = 'text-[10px] text-emerald-400 font-bold uppercase';
  }

  // Scores
  document.getElementById('score-overall').textContent = fmtPct(data.overall_score);
  document.getElementById('score-keyword').textContent = fmtPct(data.keyword_match_score);
  document.getElementById('score-semantic').textContent = fmtPct(data.semantic_relevance_score);
  document.getElementById('score-experience').textContent = fmtPct(data.experience_alignment_score);

  // Matched Skills
  const matchedContainer = document.getElementById('ats-matched-skills');
  if (matchedContainer) {
    if (data.matched_skills && data.matched_skills.length > 0) {
      matchedContainer.innerHTML = data.matched_skills.map(s =>
        `<span class="px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">${s}</span>`
      ).join('');
    } else {
      matchedContainer.innerHTML = `<span class="text-xs text-slate-500">No exact keyword matches found. Consider adding target role skills.</span>`;
    }
  }

  // Missing Skills
  const missingContainer = document.getElementById('ats-missing-skills');
  if (missingContainer) {
    if (data.missing_critical_skills && data.missing_critical_skills.length > 0) {
      missingContainer.innerHTML = data.missing_critical_skills.map(s =>
        `<span class="px-2 py-0.5 rounded-full bg-rose-950/80 border border-rose-500/30 text-rose-300 text-xs font-semibold">+ ${s}</span>`
      ).join('');
    } else {
      missingContainer.innerHTML = `<span class="text-xs text-emerald-400"><i class="fa-solid fa-check mr-1"></i>All critical target skills identified in resume!</span>`;
    }
  }

  // Detected Errors
  const errorsContainer = document.getElementById('ats-errors-list');
  if (errorsContainer) {
    if (data.detected_errors && data.detected_errors.length > 0) {
      errorsContainer.innerHTML = data.detected_errors.map(err => `
        <div class="p-3 bg-[#090d16] rounded-xl border border-rose-500/20 text-xs">
          <div class="flex items-center space-x-2 text-rose-300 font-bold mb-1">
            <i class="fa-solid fa-triangle-exclamation text-[10px]"></i>
            <span>${err.issue}</span>
          </div>
          <p class="text-slate-400 text-[11px] mb-1">${err.explanation}</p>
          <p class="text-emerald-400 text-[11px] font-semibold"><i class="fa-solid fa-wrench mr-1"></i>Fix: ${err.fix}</p>
        </div>
      `).join('');
    } else {
      errorsContainer.innerHTML = `
        <div class="p-3 bg-[#090d16] rounded-xl border border-emerald-500/20 text-xs text-emerald-300 flex items-center space-x-2">
          <i class="fa-solid fa-circle-check"></i>
          <span>Resume format passed all automated ATS structural compliance checks.</span>
        </div>`;
    }
  }

  // Google XYZ Tailored Bullets
  lastTailoredBullets = data.tailored_resume_bullet_fixes || [];
  const bulletsContainer = document.getElementById('ats-bullets-container');
  if (bulletsContainer) {
    if (lastTailoredBullets.length > 0) {
      bulletsContainer.innerHTML = lastTailoredBullets.map((bullet, idx) => `
        <div class="p-2.5 bg-[#090d16] rounded-xl border border-[#1e293b] flex items-start justify-between gap-2">
          <p class="text-xs text-slate-200 leading-relaxed font-mono">${bullet}</p>
          <button onclick="copyToClipboard('${bullet.replace(/'/g, "\\'")}', 'Bullet copied!')" class="text-slate-400 hover:text-white p-1" title="Copy bullet">
            <i class="fa-regular fa-copy text-xs"></i>
          </button>
        </div>
      `).join('');
    } else {
      bulletsContainer.innerHTML = `<span class="text-xs text-slate-500">No bullets generated.</span>`;
    }
  }
}

function copyAllTailoredBullets() {
  if (!lastTailoredBullets || lastTailoredBullets.length === 0) {
    showToast('No tailored bullets available to copy.', 'info');
    return;
  }
  copyToClipboard(lastTailoredBullets.join('\n\n'), 'All tailored bullets copied to clipboard!');
}

// ============================================================================
// VIEW 7: SOURCE REGISTRY & HEALTH DASHBOARD
// ============================================================================
async function loadSourceHealthData() {
  const tbody = document.getElementById('sources-health-tbody');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="6" class="py-8 text-center text-slate-400"><i class="fa-solid fa-circle-notch animate-spin mr-2"></i>Checking live adapter health...</td></tr>';

  try {
    const res = await fetch('/api/sources/health');
    if (!res.ok) {
      tbody.innerHTML = '<tr><td colspan="6" class="py-6 text-center text-rose-400">Failed to fetch source health.</td></tr>';
      return;
    }

    const sources = await res.json();
    tbody.innerHTML = sources.map(s => {
      const isAuthReq = s.status === 'AUTHORIZATION_REQUIRED' || s.requires_auth;
      const statusBadge = isAuthReq
        ? `<span class="badge-auth-req"><i class="fa-solid fa-lock text-amber-400"></i>AUTH REQUIRED</span>`
        : (s.status === 'SUCCESS' || s.status === 'ACTIVE'
            ? `<span class="badge-verified-live"><i class="fa-solid fa-circle-check text-emerald-400"></i>ACTIVE</span>`
            : `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">READY</span>`);

      const latency = s.latency_ms ? `${s.latency_ms}ms` : '--';
      const jobsCount = s.jobs_accepted != null ? s.jobs_accepted : (s.jobs_found || 0);

      const desc = isAuthReq
        ? `<span class="text-amber-300/80 font-mono text-[10px]">Official partner API credentials required. Zero scraping circumvention.</span>`
        : `<span class="text-slate-400 text-[11px]">${s.description || 'Verified live direct employer adapter.'}</span>`;

      return `
        <tr class="hover:bg-[#141f36]/60 transition">
          <td class="py-3 px-4 font-bold text-white">${s.source_name || s.source}</td>
          <td class="py-3 px-4 text-[11px] text-slate-400 uppercase font-mono">${s.type || 'direct'}</td>
          <td class="py-3 px-4">${statusBadge}</td>
          <td class="py-3 px-4 font-mono text-slate-400">${latency}</td>
          <td class="py-3 px-4 font-bold text-white">${jobsCount}</td>
          <td class="py-3 px-4">${desc}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" class="py-6 text-center text-rose-400">Network error retrieving health data.</td></tr>';
  }
}

// ============================================================================
// VIEW 8: CONTACT FORM SUBMISSION
// ============================================================================
async function submitContactForm(event) {
  event.preventDefault();
  const name = document.getElementById('contact-name').value.trim();
  const email = document.getElementById('contact-email').value.trim();
  const category = document.getElementById('contact-category').value;
  const subject = document.getElementById('contact-subject').value.trim();
  const message = document.getElementById('contact-message').value.trim();
  const btn = document.getElementById('btn-submit-contact');
  const banner = document.getElementById('contact-success-banner');

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch animate-spin mr-1.5"></i>Submitting...';
  }

  try {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, category, subject, message })
    });

    if (res.ok) {
      document.getElementById('contact-form').reset();
      if (banner) banner.classList.remove('hidden');
      showToast('Contact message transmitted successfully!', 'success');
    } else {
      const err = await res.json();
      showToast(err.detail || 'Failed to submit contact message', 'error');
    }
  } catch (err) {
    showToast('Network error submitting inquiry', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-paper-plane mr-1.5"></i>Send Message';
    }
  }
}

// ============================================================================
// VIEW 9: SAVED OPPORTUNITIES
// ============================================================================
async function loadSavedJobs() {
  if (!currentToken) {
    openAuthModal('login');
    return;
  }

  const grid = document.getElementById('saved-jobs-grid');
  const empty = document.getElementById('saved-empty-state');
  const totalCountEl = document.getElementById('saved-total-count');

  if (grid) grid.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400"><i class="fa-solid fa-circle-notch animate-spin mr-2"></i>Loading your saved opportunities...</div>';
  if (empty) empty.classList.add('hidden');

  try {
    const res = await fetch('/api/jobs/saved', { headers: getAuthHeaders() });
    if (res.ok) {
      savedJobsCache = await res.json();
      if (totalCountEl) totalCountEl.textContent = `${savedJobsCache.length} Saved`;
      updateSavedBadge(savedJobsCache.length);

      if (savedJobsCache.length === 0) {
        grid.innerHTML = '';
        if (empty) empty.classList.remove('hidden');
      } else {
        grid.innerHTML = savedJobsCache.map(job => renderJobCard(job, true)).join('');
      }
    } else {
      showToast('Failed to load saved jobs', 'error');
    }
  } catch (err) {
    showToast('Network error loading saved jobs', 'error');
  }
}

async function toggleSaveJob(event, jobId) {
  if (event) event.stopPropagation();

  if (!currentToken) {
    openAuthModal('login');
    return;
  }

  const isCurrentlySaved = savedJobsCache.some(j => j.id === jobId);

  try {
    const method = isCurrentlySaved ? 'DELETE' : 'POST';
    const res = await fetch(`/api/jobs/${jobId}/save`, {
      method,
      headers: getAuthHeaders()
    });

    if (res.ok) {
      if (isCurrentlySaved) {
        savedJobsCache = savedJobsCache.filter(j => j.id !== jobId);
        showToast('Removed from saved opportunities', 'info');
      } else {
        const found = allLiveJobs.find(j => j.id === jobId) || { id: jobId, is_saved: true };
        savedJobsCache.push(found);
        showToast('Saved to your opportunities!', 'success');
      }

      updateSavedBadge(savedJobsCache.length);

      // Re-render affected view
      if (activeView === 'saved') {
        loadSavedJobs();
      } else if (activeView === 'discover') {
        applyAndRenderDiscoverJobs();
      }
    }
  } catch (err) {
    showToast('Failed to update saved job status', 'error');
  }
}

// ============================================================================
// VIEW 10: USER PROFILE
// ============================================================================
async function loadUserProfile() {
  if (!currentToken) {
    openAuthModal('login');
    return;
  }

  try {
    const res = await fetch('/api/auth/me', { headers: getAuthHeaders() });
    if (res.ok) {
      currentUser = await res.json();
      document.getElementById('profile-fullname').value = currentUser.full_name || '';
      document.getElementById('profile-target-role').value = currentUser.preferred_role || '';
      document.getElementById('profile-experience').value = currentUser.years_of_experience || 2.0;
      document.getElementById('profile-preferred-location').value = currentUser.preferred_location || '';
      document.getElementById('profile-skills-input').value = (currentUser.skills || []).join(', ');
      document.getElementById('profile-summary-input').value = currentUser.summary || '';
    }
  } catch (err) {
    showToast('Failed to load profile details', 'error');
  }
}

async function saveUserProfile(event) {
  event.preventDefault();
  if (!currentToken) return;

  const full_name = document.getElementById('profile-fullname').value.trim();
  const preferred_role = document.getElementById('profile-target-role').value.trim();
  const years_of_experience = parseFloat(document.getElementById('profile-experience').value) || 2.0;
  const preferred_location = document.getElementById('profile-preferred-location').value.trim();
  const skillsRaw = document.getElementById('profile-skills-input').value;
  const summary = document.getElementById('profile-summary-input').value.trim();

  const skills = skillsRaw.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);

  try {
    const res = await fetch('/api/auth/profile', {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        full_name,
        preferred_role,
        years_of_experience,
        preferred_location,
        skills,
        summary
      })
    });

    if (res.ok) {
      currentUser = await res.json();
      updateAuthNavUI();
      showToast('Profile updated successfully!', 'success');
    } else {
      showToast('Failed to save profile', 'error');
    }
  } catch (err) {
    showToast('Network error saving profile', 'error');
  }
}

// ============================================================================
// ============================================================================
// VIEW 11: APPLICATION & PIPELINE TRACKER
// ============================================================================
let currentTrackerApplications = [];
let trackerActiveViewMode = 'table'; // Default format: 'table' or 'kanban'

function setTrackerViewMode(mode) {
  trackerActiveViewMode = mode;
  const tableView = document.getElementById('tracker-view-table');
  const kanbanView = document.getElementById('tracker-view-kanban');
  const btnTable = document.getElementById('tracker-toggle-table');
  const btnKanban = document.getElementById('tracker-toggle-kanban');

  if (mode === 'table') {
    if (tableView) tableView.classList.remove('hidden');
    if (kanbanView) kanbanView.classList.add('hidden');
    if (btnTable) {
      btnTable.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-2 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm';
    }
    if (btnKanban) {
      btnKanban.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition flex items-center space-x-2';
    }
  } else {
    if (tableView) tableView.classList.add('hidden');
    if (kanbanView) kanbanView.classList.remove('hidden');
    if (btnKanban) {
      btnKanban.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-2 bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm';
    }
    if (btnTable) {
      btnTable.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition flex items-center space-x-2';
    }
  }
}

async function loadTrackerBoard() {
  const tableBody = document.getElementById('tracker-table-body');
  if (tableBody) {
    tableBody.innerHTML = `<tr><td colspan="6" class="text-center py-12 text-slate-500"><i class="fa-solid fa-spinner animate-spin mr-2"></i>Loading applications...</td></tr>`;
  }

  const cols = ['shortlisted', 'applied', 'interview', 'offer'];
  cols.forEach(c => {
    const el = document.getElementById(`kanban-col-${c}`);
    if (el) el.innerHTML = '<p class="text-[11px] text-slate-500 text-center py-6">Loading...</p>';
  });

  try {
    const [appsRes, funnelRes] = await Promise.all([
      fetch('/api/applications', { headers: getAuthHeaders() }),
      fetch('/api/applications/funnel', { headers: getAuthHeaders() })
    ]);

    if (appsRes.ok) {
      currentTrackerApplications = await appsRes.json();
    }

    if (funnelRes.ok) {
      const funnel = await funnelRes.json();
      updateTrackerFunnelStats(funnel, currentTrackerApplications.length);
    } else {
      updateTrackerStatsFallback(currentTrackerApplications);
    }

    populateTrackerPortalFilter(currentTrackerApplications);
    filterTrackerApplications();
  } catch (err) {
    showToast('Failed to load tracked applications', 'error');
  }
}

function updateTrackerFunnelStats(funnel, totalCount) {
  const totalEl = document.getElementById('tracker-stat-total');
  const appliedEl = document.getElementById('tracker-stat-applied');
  const intEl = document.getElementById('tracker-stat-interviewing');
  const offerEl = document.getElementById('tracker-stat-offers');
  const rateEl = document.getElementById('tracker-stat-rate');

  if (totalEl) totalEl.textContent = (funnel.total_tracked || totalCount || 0).toLocaleString();
  if (appliedEl) appliedEl.textContent = ((funnel.counts && funnel.counts.APPLIED) || 0).toLocaleString();
  if (intEl) intEl.textContent = ((funnel.counts && (funnel.counts.INTERVIEWING || funnel.counts.INTERVIEW)) || 0).toLocaleString();
  if (offerEl) offerEl.textContent = ((funnel.counts && funnel.counts.OFFER) || 0).toLocaleString();
  if (rateEl) rateEl.textContent = `${funnel.interview_rate_pct || 0}%`;
}

function updateTrackerStatsFallback(apps) {
  const total = apps.length;
  let applied = 0, interview = 0, offer = 0;
  apps.forEach(a => {
    const s = (a.status || '').toUpperCase();
    if (s === 'APPLIED') applied++;
    else if (s === 'INTERVIEW' || s === 'INTERVIEWING') interview++;
    else if (s === 'OFFER' || s === 'ACCEPTED') offer++;
  });
  const rate = total > 0 ? Math.round(((interview + offer) / Math.max(applied + interview + offer, 1)) * 100) : 0;

  const totalEl = document.getElementById('tracker-stat-total');
  const appliedEl = document.getElementById('tracker-stat-applied');
  const intEl = document.getElementById('tracker-stat-interviewing');
  const offerEl = document.getElementById('tracker-stat-offers');
  const rateEl = document.getElementById('tracker-stat-rate');

  if (totalEl) totalEl.textContent = total.toLocaleString();
  if (appliedEl) appliedEl.textContent = applied.toLocaleString();
  if (intEl) intEl.textContent = interview.toLocaleString();
  if (offerEl) offerEl.textContent = offer.toLocaleString();
  if (rateEl) rateEl.textContent = `${rate}%`;
}

function populateTrackerPortalFilter(apps) {
  const select = document.getElementById('tracker-filter-portal');
  if (!select) return;
  const currentVal = select.value;
  const portals = new Set();
  apps.forEach(a => {
    if (a.source || a.portal) portals.add((a.source || a.portal).trim());
  });

  let options = `<option value="ALL">All Portals (${apps.length})</option>`;
  Array.from(portals).sort().forEach(p => {
    const count = apps.filter(a => (a.source || a.portal || '').trim().toLowerCase() === p.toLowerCase()).length;
    options += `<option value="${escapeHtml(p)}" ${currentVal === p ? 'selected' : ''}>${escapeHtml(p)} (${count})</option>`;
  });
  select.innerHTML = options;
}

function filterTrackerApplications() {
  const searchInput = document.getElementById('tracker-search-input');
  const stageSelect = document.getElementById('tracker-filter-stage');
  const portalSelect = document.getElementById('tracker-filter-portal');

  const q = searchInput ? searchInput.value.toLowerCase().trim() : '';
  const stage = stageSelect ? stageSelect.value.toUpperCase() : 'ALL';
  const portal = portalSelect ? portalSelect.value.toLowerCase() : 'all';

  const filtered = currentTrackerApplications.filter(app => {
    const company = (app.company || '').toLowerCase();
    const role = (app.job_title || app.title || app.role || '').toLowerCase();
    const src = (app.source || app.portal || '').toLowerCase();
    const st = (app.status || 'SHORTLISTED').toUpperCase();

    // Query filter
    if (q && !company.includes(q) && !role.includes(q) && !src.includes(q)) {
      return false;
    }

    // Stage filter
    if (stage !== 'ALL') {
      if (stage === 'INTERVIEW' && !(st === 'INTERVIEW' || st === 'INTERVIEWING')) return false;
      if (stage === 'OFFER' && !(st === 'OFFER' || st === 'ACCEPTED')) return false;
      if (stage !== 'INTERVIEW' && stage !== 'OFFER' && st !== stage) return false;
    }

    // Portal filter
    if (portal !== 'all' && src !== portal) {
      return false;
    }

    return true;
  });

  renderTrackerTable(filtered);
  renderKanbanColumns(filtered);
}

function getPortalBadgeStyle(portal) {
  const p = (portal || '').toLowerCase();
  if (p.includes('linkedin')) return 'bg-blue-950/70 text-blue-300 border-blue-800/60';
  if (p.includes('naukri')) return 'bg-sky-950/70 text-sky-300 border-sky-800/60';
  if (p.includes('indeed')) return 'bg-indigo-950/70 text-indigo-300 border-indigo-800/60';
  if (p.includes('hirist')) return 'bg-purple-950/70 text-purple-300 border-purple-800/60';
  if (p.includes('wellfound')) return 'bg-rose-950/70 text-rose-300 border-rose-800/60';
  if (p.includes('cutshort')) return 'bg-teal-950/70 text-teal-300 border-teal-800/60';
  if (p.includes('instahyre')) return 'bg-amber-950/70 text-amber-300 border-amber-800/60';
  return 'bg-slate-800 text-slate-300 border-slate-700';
}

function getStatusBadgeStyle(status) {
  const s = (status || '').toUpperCase();
  if (s === 'APPLIED') return 'bg-cyan-950/70 text-cyan-300 border-cyan-800/60';
  if (s === 'INTERVIEW' || s === 'INTERVIEWING') return 'bg-purple-950/70 text-purple-300 border-purple-800/60';
  if (s === 'OFFER' || s === 'ACCEPTED') return 'bg-emerald-950/70 text-emerald-300 border-emerald-800/60';
  if (s === 'REJECTED') return 'bg-rose-950/70 text-rose-300 border-rose-800/60';
  return 'bg-slate-800 text-slate-300 border-slate-700';
}

function renderTrackerTable(apps) {
  const tbody = document.getElementById('tracker-table-body');
  if (!tbody) return;

  if (apps.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="py-16 text-center">
          <div class="max-w-md mx-auto space-y-3">
            <div class="w-12 h-12 rounded-2xl bg-[#06080d] border border-[#1a2336] flex items-center justify-center mx-auto text-slate-500">
              <i class="fa-solid fa-inbox text-xl"></i>
            </div>
            <h4 class="text-sm font-bold text-white">No applications match your filter</h4>
            <p class="text-xs text-slate-400">Applications dispatched by the Autonomous Agent or LazyApply Copilot will automatically display here in real time.</p>
            <div class="pt-2 flex justify-center gap-2">
              <button onclick="switchView('discover')" class="btn-secondary text-xs py-1.5 px-3">Browse Live Jobs</button>
              <button onclick="switchView('agent')" class="btn-primary text-xs py-1.5 px-3">Run Autonomous Cycle</button>
            </div>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = apps.map(app => {
    const roleTitle = app.job_title || app.title || app.role || 'Software Engineer';
    const company = app.company || 'Enterprise Employer';
    const portal = app.source || app.portal || 'Direct ATS';
    const location = app.location || 'Remote / India';
    const match = app.match_score ? Math.round(app.match_score) : 95;
    const dateStr = formatDate(app.created_at || app.updated_at);
    const status = (app.status || 'SHORTLISTED').toUpperCase();

    // Match score color badge
    let scoreColor = 'from-emerald-500/20 to-emerald-400/10 text-emerald-300 border-emerald-500/30';
    if (match < 80) scoreColor = 'from-amber-500/20 to-amber-400/10 text-amber-300 border-amber-500/30';
    if (match < 60) scoreColor = 'from-slate-500/20 to-slate-400/10 text-slate-300 border-slate-500/30';

    return `
      <tr class="hover:bg-[#06080d]/60 transition group">
        <!-- 1. Company & Location -->
        <td class="py-3 px-4">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-[#1a2336] to-[#0f172a] border border-[#223048] flex items-center justify-center text-xs font-black text-cyan-400 shrink-0">
              ${company.charAt(0).toUpperCase()}
            </div>
            <div class="min-w-0">
              <span class="text-xs font-bold text-white block truncate">${escapeHtml(company)}</span>
              <span class="text-[11px] text-slate-400 flex items-center space-x-1 truncate mt-0.5">
                <i class="fa-solid fa-location-dot text-[9px] text-slate-500 mr-1"></i>
                ${escapeHtml(location)}
              </span>
            </div>
          </div>
        </td>

        <!-- 2. Role & Source -->
        <td class="py-3 px-4">
          <div class="min-w-0 space-y-1">
            <a href="${app.url || '#'}" target="_blank" rel="noopener noreferrer" class="text-xs font-semibold text-cyan-300 hover:text-cyan-200 block truncate transition">
              ${escapeHtml(roleTitle)}
              <i class="fa-solid fa-arrow-up-right-from-square text-[9px] text-slate-500 ml-1"></i>
            </a>
            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${getPortalBadgeStyle(portal)}">
              ${escapeHtml(portal)}
            </span>
          </div>
        </td>

        <!-- 3. ATS Match Score -->
        <td class="py-3 px-4 text-center">
          <span class="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[11px] font-extrabold border bg-gradient-to-r ${scoreColor}">
            <i class="fa-solid fa-bolt text-[9px]"></i>
            <span>${match}% Fit</span>
          </span>
        </td>

        <!-- 4. Date Applied -->
        <td class="py-3 px-4 whitespace-nowrap">
          <span class="text-xs text-slate-300 block font-medium">${dateStr}</span>
          <span class="text-[10px] text-slate-500">Autonomous Copilot</span>
        </td>

        <!-- 5. Stage / Status Selector -->
        <td class="py-3 px-4">
          <select onchange="updateApplicationStatus(${app.id}, this.value)" class="bg-[#06080d] text-xs font-bold border border-[#1e293b] rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 transition cursor-pointer ${getStatusBadgeStyle(status)}">
            <option value="SHORTLISTED" ${status === 'SHORTLISTED' ? 'selected' : ''}>Shortlisted</option>
            <option value="APPLIED" ${status === 'APPLIED' ? 'selected' : ''}>Applied</option>
            <option value="INTERVIEW" ${(status === 'INTERVIEW' || status === 'INTERVIEWING') ? 'selected' : ''}>Interviewing</option>
            <option value="OFFER" ${(status === 'OFFER' || status === 'ACCEPTED') ? 'selected' : ''}>Offer Received</option>
            <option value="REJECTED" ${status === 'REJECTED' ? 'selected' : ''}>Rejected</option>
          </select>
        </td>

        <!-- 6. Actions -->
        <td class="py-3 px-4 text-right">
          <div class="flex items-center justify-end space-x-1.5">
            <button onclick="openTrackerNotesModal(${app.id})" title="View Dossier &amp; Cover Letter" class="p-1.5 text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded-lg transition">
              <i class="fa-solid fa-file-lines text-xs"></i>
            </button>
            <a href="${app.url || '#'}" target="_blank" title="Open Job Portal" class="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition">
              <i class="fa-solid fa-external-link text-xs"></i>
            </a>
            <button onclick="deleteTrackedApplication(${app.id})" title="Remove from Tracker" class="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition">
              <i class="fa-solid fa-trash text-xs"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderKanbanColumns(apps) {
  const groups = {
    SHORTLISTED: [],
    APPLIED: [],
    INTERVIEW: [],
    OFFER: []
  };

  apps.forEach(app => {
    const st = (app.status || 'SHORTLISTED').toUpperCase();
    if (st === 'INTERVIEWING') {
      groups.INTERVIEW.push(app);
    } else if (st === 'ACCEPTED') {
      groups.OFFER.push(app);
    } else if (groups[st]) {
      groups[st].push(app);
    } else {
      groups.SHORTLISTED.push(app);
    }
  });

  renderSingleKanbanCol('shortlisted', groups.SHORTLISTED, 'SHORTLISTED');
  renderSingleKanbanCol('applied', groups.APPLIED, 'APPLIED');
  renderSingleKanbanCol('interview', groups.INTERVIEW, 'INTERVIEW');
  renderSingleKanbanCol('offer', groups.OFFER, 'OFFER');
}

function renderSingleKanbanCol(colKey, items, statusVal) {
  const colEl = document.getElementById(`kanban-col-${colKey}`);
  const countEl = document.getElementById(`kanban-count-${colKey}`);
  if (countEl) countEl.textContent = items.length;
  if (!colEl) return;

  if (items.length === 0) {
    colEl.innerHTML = `<div class="text-center py-10 text-slate-600 text-xs border border-dashed border-[#1e293b] rounded-2xl flex flex-col items-center justify-center space-y-1"><i class="fa-solid fa-box-open text-base opacity-40"></i><span>No applications</span></div>`;
    return;
  }

  colEl.innerHTML = items.map(app => {
    const roleTitle = app.job_title || app.title || app.role || 'Software Engineer';
    const company = app.company || 'Enterprise Employer';
    const portal = app.source || app.portal || 'Direct ATS';
    const match = app.match_score ? Math.round(app.match_score) : 95;
    const dateStr = formatDate(app.created_at || app.updated_at);

    return `
      <div class="p-3.5 bg-[#090d16] rounded-2xl border border-[#1e293b] space-y-2.5 shadow-md hover:border-cyan-500/40 transition">
        <div class="flex items-start justify-between gap-2">
          <div class="flex items-center space-x-2 min-w-0">
            <div class="w-6 h-6 rounded-lg bg-[#1a2336] text-[10px] font-black text-cyan-400 flex items-center justify-center shrink-0">
              ${company.charAt(0).toUpperCase()}
            </div>
            <span class="text-xs font-bold text-white truncate block">${escapeHtml(company)}</span>
          </div>
          <button onclick="deleteTrackedApplication(${app.id})" title="Remove" class="text-slate-500 hover:text-rose-400 text-xs p-1 shrink-0 transition">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>

        <a href="${app.url || '#'}" target="_blank" class="text-xs font-semibold text-cyan-300 hover:text-cyan-200 block truncate transition">
          ${escapeHtml(roleTitle)}
        </a>

        <div class="flex items-center justify-between gap-1 pt-1">
          <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold border ${getPortalBadgeStyle(portal)}">
            ${escapeHtml(portal)}
          </span>
          <span class="text-[10px] font-extrabold text-emerald-400 flex items-center space-x-1">
            <i class="fa-solid fa-bolt text-[8px]"></i>
            <span>${match}%</span>
          </span>
        </div>
        
        <div class="flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-[#1e293b]">
          <span>${dateStr}</span>
          <select onchange="updateApplicationStatus(${app.id}, this.value)" class="bg-[#0f172a] text-slate-300 border border-[#334155] rounded-lg px-2 py-1 text-[10px] font-semibold focus:outline-none focus:border-cyan-500">
            <option value="SHORTLISTED" ${statusVal === 'SHORTLISTED' ? 'selected' : ''}>Shortlist</option>
            <option value="APPLIED" ${statusVal === 'APPLIED' ? 'selected' : ''}>Applied</option>
            <option value="INTERVIEW" ${statusVal === 'INTERVIEW' ? 'selected' : ''}>Interview</option>
            <option value="OFFER" ${statusVal === 'OFFER' ? 'selected' : ''}>Offer</option>
          </select>
        </div>
      </div>
    `;
  }).join('');
}

function openTrackerNotesModal(appId) {
  const app = currentTrackerApplications.find(a => a.id === appId);
  if (!app) return;

  const modal = document.getElementById('tracker-notes-modal');
  const title = document.getElementById('tracker-notes-title');
  const body = document.getElementById('tracker-notes-body');

  if (title) {
    title.textContent = `${app.company || 'Application'} - ${app.job_title || app.title || 'Role'} Dossier`;
  }
  if (body) {
    let content = '';
    if (app.notes) {
      content += `=== APPLICATION NOTES ===\n${app.notes}\n\n`;
    }
    if (app.tailored_cover_letter) {
      content += `=== TAILORED COVER LETTER ===\n${app.tailored_cover_letter}\n\n`;
    }
    if (!content) {
      content = `Application dispatched via autonomous career engine.\nPortal: ${app.source || app.portal || 'Direct'}\nStatus: ${app.status}\nSubmitted at: ${app.created_at || 'Recent'}`;
    }
    body.textContent = content;
  }

  if (modal) modal.classList.remove('hidden');
}

function closeTrackerNotesModal() {
  const modal = document.getElementById('tracker-notes-modal');
  if (modal) modal.classList.add('hidden');
}

async function updateApplicationStatus(appId, newStatus) {
  try {
    const res = await fetch(`/api/applications/${appId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      showToast(`Stage updated to ${newStatus}`, 'success');
      loadTrackerBoard();
    }
  } catch (err) {
    showToast('Failed to update status', 'error');
  }
}

async function deleteTrackedApplication(appId) {
  try {
    const res = await fetch(`/api/applications/${appId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (res.ok) {
      showToast('Application removed from tracker', 'info');
      loadTrackerBoard();
    }
  } catch (err) {
    showToast('Failed to remove application', 'error');
  }
}

// ============================================================================
// JOB DETAILS MODAL & REPORTING
// ============================================================================
async function openJobDetailsModal(jobId) {
  currentDetailJob = allLiveJobs.find(j => j.id === jobId) ||
                     indiaJobsCache.find(j => j.id === jobId) ||
                     remoteJobsCache.find(j => j.id === jobId) ||
                     freshersJobsCache.find(j => j.id === jobId) ||
                     savedJobsCache.find(j => j.id === jobId);

  if (!currentDetailJob) {
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      if (res.ok) {
        currentDetailJob = await res.json();
      }
    } catch (err) {
      showToast('Unable to load job details', 'error');
      return;
    }
  }

  if (!currentDetailJob) return;

  // Populate Modal Fields
  document.getElementById('modal-job-company').textContent = currentDetailJob.company || 'Company';
  document.getElementById('modal-job-title').textContent = currentDetailJob.title || 'Role';
  document.getElementById('modal-job-location').textContent = currentDetailJob.city || currentDetailJob.location || 'Remote';
  document.getElementById('modal-job-canonical').innerHTML = buildCanonicalBadge(currentDetailJob);

  document.getElementById('modal-job-workplace').textContent = currentDetailJob.remote ? '🌐 100% Remote' : '🏢 Onsite / Hybrid';
  document.getElementById('modal-job-experience').textContent = currentDetailJob.is_fresher ? '🎓 Fresher (0-2 Yrs)' : (currentDetailJob.experience_level || 'Mid-Level');
  document.getElementById('modal-job-published').textContent = `Verified ${formatDate(currentDetailJob.published_at || currentDetailJob.first_seen_at)}`;

  // Skills
  const skills = currentDetailJob.skills || currentDetailJob.skills_required || [];
  const skillsContainer = document.getElementById('modal-job-skills');
  if (skillsContainer) {
    skillsContainer.innerHTML = skills.length > 0
      ? skills.map(s => `<span class="px-2.5 py-1 rounded-lg bg-[#1e293b] text-indigo-300 text-xs font-semibold">${s}</span>`).join('')
      : `<span class="text-xs text-slate-500">Verified Technical Role</span>`;
  }

  // Description
  const descEl = document.getElementById('modal-job-description');
  if (descEl) {
    descEl.textContent = currentDetailJob.description || `${currentDetailJob.title} opening at ${currentDetailJob.company}.`;
  }

  // Direct Apply Button
  const applyBtn = document.getElementById('modal-apply-btn');
  if (applyBtn) {
    applyBtn.href = currentDetailJob.apply_url || '#';
  }

  // Save Button
  updateModalSaveButtonState();

  document.getElementById('job-details-modal').classList.remove('hidden');
}

function closeJobDetailsModal() {
  document.getElementById('job-details-modal').classList.add('hidden');
}

function updateModalSaveButtonState() {
  const saveBtn = document.getElementById('modal-save-btn');
  if (!saveBtn || !currentDetailJob) return;
  const isSaved = savedJobsCache.some(j => j.id === currentDetailJob.id);
  saveBtn.innerHTML = isSaved
    ? '<i class="fa-solid fa-bookmark text-amber-400"></i>'
    : '<i class="fa-regular fa-bookmark"></i>';
}

function toggleSaveCurrentModalJob() {
  if (!currentDetailJob) return;
  toggleSaveJob(null, currentDetailJob.id);
  updateModalSaveButtonState();
}

// Job Report Modal
function openJobReportModal() {
  if (!currentDetailJob) return;
  document.getElementById('job-report-modal').classList.remove('hidden');
}

function closeJobReportModal() {
  document.getElementById('job-report-modal').classList.add('hidden');
}

async function handleJobReportSubmit(event) {
  event.preventDefault();
  if (!currentDetailJob) return;

  const reason = document.getElementById('report-reason').value;
  const details = document.getElementById('report-details').value.trim();
  const reporter_email = document.getElementById('report-email').value.trim();

  try {
    const res = await fetch(`/api/jobs/${currentDetailJob.id}/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason, details, reporter_email })
    });

    if (res.ok) {
      closeJobReportModal();
      document.getElementById('job-report-form').reset();
      showToast('Thank you! Our automated lifecycle engine will re-verify the application link.', 'success');
    } else {
      const err = await res.json();
      showToast(err.detail || 'Failed to submit report', 'error');
    }
  } catch (err) {
    showToast('Network error submitting job report', 'error');
  }
}

// ============================================================================
// AUTO-APPLY BOT ENGINE & COPILOT MODAL (LazyApply / JobPilot Style)
// ============================================================================
let currentCopilotJobId = null;
let currentCopilotData = null;

async function runHomeAutoApplyBot() {
  const btn = document.getElementById('btn-start-home-bot');
  const termBody = document.getElementById('home-bot-terminal-body');
  const resultsContainer = document.getElementById('home-bot-results');
  const appliedList = document.getElementById('home-bot-applied-list');

  const role = document.getElementById('home-bot-role')?.value || '';
  const scope = document.getElementById('home-bot-scope')?.value || 'all';
  const count = parseInt(document.getElementById('home-bot-count')?.value || '5');
  const minScore = parseFloat(document.getElementById('home-bot-min-score')?.value || '60');

  const region = (scope === 'india') ? 'India' : (scope === 'remote' ? 'Remote' : null);
  const fresher_only = (scope === 'fresher');

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i><span>Bot Executing Applications...</span>';
  }

  if (termBody) {
    const timeStr = new Date().toLocaleTimeString();
    termBody.innerHTML = `
      <p class="text-cyan-400">[${timeStr}] ⚡ JobPulse Auto-Apply Daemon initialized.</p>
      <p class="text-slate-400">[${timeStr}] 🎯 Target: "${role || 'All Technical Roles'}" | Scope: ${scope.toUpperCase()} | Min Match: ${minScore}%</p>
      <p class="text-yellow-400">[${timeStr}] 🔍 Scanning active enterprise portals & matching ATS credentials...</p>
    `;
    termBody.scrollTop = termBody.scrollHeight;
  }

  try {
    const params = new URLSearchParams();
    params.append('count', count);
    if (role) params.append('role_query', role);
    if (region) params.append('region', region);
    if (fresher_only) params.append('fresher_only', 'true');
    if (minScore) params.append('min_match_score', minScore);

    const res = await fetch(`/api/copilot/auto-apply-batch?${params.toString()}`, {
      method: 'POST',
      headers: getAuthHeaders()
    });

    if (res.ok) {
      const data = await res.json();
      const logs = data.execution_logs || [];

      // Stream logs sequentially for interactive bot feel
      let delay = 0;
      logs.forEach((logLine) => {
        setTimeout(() => {
          if (termBody) {
            const p = document.createElement('p');
            p.className = 'terminal-log-line ' + (logLine.includes('✓') ? 'text-emerald-400' : (logLine.includes('Navigating') ? 'text-cyan-300' : 'text-slate-300'));
            p.textContent = logLine;
            termBody.appendChild(p);
            termBody.scrollTop = termBody.scrollHeight;
          }
        }, delay);
        delay += 140;
      });

      setTimeout(() => {
        if (data.status === 'SUCCESS' && data.applied_jobs && data.applied_jobs.length > 0) {
          if (resultsContainer) resultsContainer.classList.remove('hidden');
          if (appliedList) {
            appliedList.innerHTML = data.applied_jobs.map(j => `
              <div class="p-2.5 rounded-xl bg-[#0b101b] border border-cyan-500/20 flex items-center justify-between">
                <div>
                  <span class="font-bold text-white block line-clamp-1">${j.title}</span>
                  <span class="text-[10px] text-slate-400">${j.company} &bull; ${j.location}</span>
                </div>
                <div class="text-right flex flex-col items-end">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    ${Math.round(j.match_score || 85)}% Match
                  </span>
                  <a href="${j.apply_url}" target="_blank" class="text-[10px] text-cyan-400 hover:underline mt-0.5">Direct Link</a>
                </div>
              </div>
            `).join('');
          }
          showToast(`Autonomous Bot applied to ${data.applied_count} positions successfully!`, 'success');
        } else {
          showToast(data.message || 'No jobs matched criteria for application', 'info');
        }

        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<i class="fa-solid fa-bolt text-yellow-300"></i><span>Start Auto-Apply Bot</span>';
        }
      }, delay + 200);

    } else {
      const err = await res.json();
      if (termBody) {
        termBody.innerHTML += `<p class="text-rose-400">[ERROR] Execution failed: ${err.detail || 'Server error'}</p>`;
      }
      showToast(err.detail || 'Auto-apply bot error', 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-bolt text-yellow-300"></i><span>Start Auto-Apply Bot</span>';
      }
    }
  } catch (err) {
    if (termBody) {
      termBody.innerHTML += `<p class="text-rose-400">[ERROR] Network communication failure.</p>`;
    }
    showToast('Network error running auto-apply bot', 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-bolt text-yellow-300"></i><span>Start Auto-Apply Bot</span>';
    }
  }
}

// 1-Click Copilot Modal
async function openCopilotModal(jobId) {
  const modal = document.getElementById('copilot-modal');
  if (!modal) return;

  currentCopilotJobId = jobId;
  modal.classList.remove('hidden');

  const titleEl = document.getElementById('copilot-modal-subtitle');
  const scoreEl = document.getElementById('copilot-modal-score');
  const screenerList = document.getElementById('copilot-screener-list');
  const coverLetterEl = document.getElementById('copilot-cover-letter');
  const extUrl = document.getElementById('copilot-external-url');
  const btnSubmit = document.getElementById('btn-copilot-submit');

  if (titleEl) titleEl.textContent = 'Loading job and candidate dossier...';
  if (screenerList) screenerList.innerHTML = '<p class="text-slate-400 text-xs">Synthesizing tailored screening answers...</p>';
  if (btnSubmit) {
    btnSubmit.disabled = false;
    btnSubmit.innerHTML = '<i class="fa-solid fa-bolt text-yellow-300"></i><span>Submit 1-Click Auto-Apply</span>';
  }

  try {
    const res = await fetch(`/api/copilot/autofill/${jobId}`, {
      headers: getAuthHeaders()
    });

    if (res.ok) {
      const data = await res.json();
      currentCopilotData = data;

      if (titleEl) titleEl.textContent = `${data.job_title} at ${data.company} (${data.location})`;
      if (scoreEl) scoreEl.textContent = `${Math.round(data.match_score || 85)}% Match`;

      const dossier = data.dossier || {};
      const nameInput = document.getElementById('copilot-dossier-name');
      const emailInput = document.getElementById('copilot-dossier-email');
      const salaryInput = document.getElementById('copilot-dossier-salary');
      const noticeInput = document.getElementById('copilot-dossier-notice');

      if (nameInput) nameInput.value = dossier.full_name || '';
      if (emailInput) emailInput.value = dossier.email || '';
      if (salaryInput) salaryInput.value = dossier.expected_salary || '$120k - $140k';
      if (noticeInput) noticeInput.value = dossier.notice_period || 'Immediate / 15 Days';

      // Screener Q&A
      const qaList = data.screening_qa || [];
      if (screenerList) {
        screenerList.innerHTML = qaList.map(item => `
          <div class="p-2.5 rounded-xl bg-[#0b101b] border border-[#1a2336] space-y-1">
            <p class="text-[11px] font-bold text-slate-200 flex items-center">
              <i class="fa-solid fa-circle-question text-cyan-400 mr-1.5 text-xs"></i>
              ${item.question}
            </p>
            <p class="text-xs text-slate-300 pl-3 border-l-2 border-cyan-500/40 font-normal">
              ${item.answer}
            </p>
          </div>
        `).join('');
      }

      // Tailored Cover Letter
      if (coverLetterEl) {
        coverLetterEl.value = (
          `Dear ${data.company} Hiring Team,\n\n` +
          `I am writing to express my enthusiastic interest in the ${data.job_title} position. ` +
          `My technical background directly aligns with your requirements, particularly in scalable software architecture, modular API development, and distributed systems.\n\n` +
          `Thank you for your consideration.\n\n` +
          `Sincerely,\n${dossier.full_name || 'Candidate'}`
        );
      }

      if (extUrl) {
        const matchJob = allLiveJobs.find(j => j.id === jobId);
        extUrl.href = matchJob ? matchJob.apply_url : '#';
      }

    } else {
      showToast('Could not load Copilot details', 'error');
    }
  } catch (err) {
    showToast('Network error loading Copilot dossier', 'error');
  }
}

function closeCopilotModal() {
  const modal = document.getElementById('copilot-modal');
  if (modal) modal.classList.add('hidden');
}

async function executeModalCopilotApply() {
  if (!currentCopilotJobId) return;
  const btn = document.getElementById('btn-copilot-submit');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i><span>Dispatching Application...</span>';
  }

  try {
    const res = await fetch(`/api/copilot/apply-one/${currentCopilotJobId}`, {
      method: 'POST',
      headers: getAuthHeaders()
    });

    if (res.ok) {
      if (btn) {
        btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i><span>Application Submitted!</span>';
      }
      showToast(`Successfully auto-applied to ${currentCopilotData?.company || 'Employer'}!`, 'success');
      setTimeout(() => {
        closeCopilotModal();
      }, 1200);
    } else {
      const err = await res.json();
      showToast(err.detail || 'Failed to submit application', 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-bolt text-yellow-300"></i><span>Submit 1-Click Auto-Apply</span>';
      }
    }
  } catch (err) {
    showToast('Network error submitting auto-application', 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-bolt text-yellow-300"></i><span>Submit 1-Click Auto-Apply</span>';
    }
  }
}

function copyCopilotJson() {
  if (!currentCopilotData || !currentCopilotData.dossier) return;
  navigator.clipboard.writeText(JSON.stringify(currentCopilotData.dossier, null, 2))
    .then(() => showToast('Copilot form JSON copied to clipboard!', 'success'))
    .catch(() => showToast('Failed to copy JSON', 'error'));
}

function copyCopilotCoverLetter() {
  const el = document.getElementById('copilot-cover-letter');
  if (!el) return;
  navigator.clipboard.writeText(el.value)
    .then(() => showToast('Tailored cover letter copied to clipboard!', 'success'))
    .catch(() => showToast('Failed to copy cover letter', 'error'));
}



// ============================================================================
// AUTONOMOUS AGENT HUB & CONTINUOUS COPILOT (MODULES 1 - 4)
// ============================================================================

let currentAgentTab = 'dashboard';
let currentAgentPreferences = null;
let currentAgentMetrics = null;
let currentPortalList = [];
let currentTimelineEvents = [];
let currentLatexResume = { code: '', app_id: null, job_id: null, overleaf_url: '' };
let currentSimEmails = [];

function switchAgentTab(tabId) {
  const tabs = ['dashboard', 'timeline', 'approvals', 'preferences', 'portals', 'outreach', 'kb'];
  if (!tabs.includes(tabId)) tabId = 'dashboard';
  currentAgentTab = tabId;

  tabs.forEach(t => {
    const btn = document.getElementById(`agent-tab-${t}`);
    const sec = document.getElementById(`agent-subview-${t}`);
    if (btn) {
      if (t === tabId) {
        btn.classList.add('agent-tab-active');
      } else {
        btn.classList.remove('agent-tab-active');
      }
    }
    if (sec) {
      if (t === tabId) {
        sec.classList.remove('hidden');
      } else {
        sec.classList.add('hidden');
      }
    }
  });

  // Trigger Subview Loaders
  if (tabId === 'dashboard') {
    loadAgentDashboard();
  } else if (tabId === 'timeline') {
    loadAgentTimeline();
  } else if (tabId === 'approvals') {
    loadAgentApprovals();
  } else if (tabId === 'preferences') {
    loadAgentPreferences();
  } else if (tabId === 'portals') {
    loadPortalPermissions();
  } else if (tabId === 'outreach') {
    loadAgentOutreach();
  } else if (tabId === 'kb') {
    loadAgentKnowledgeBase();
  }
}

async function loadAgentView() {
  await loadAgentPreferences(false);
  loadPendingApprovalsCount();
  switchAgentTab(currentAgentTab || 'dashboard');
}

async function loadPendingApprovalsCount() {
  try {
    const [resApps, resQs] = await Promise.all([
      fetch('/api/agent/approvals', { headers: getAuthHeaders() }),
      fetch('/api/learner/pending-questions', { headers: getAuthHeaders() })
    ]);
    let count = 0;
    if (resApps.ok) {
      const data = await resApps.json();
      count += (data.pending_applications || []).length + (data.pending_emails || []).length;
    }
    if (resQs.ok) {
      const qData = await resQs.json();
      count += (qData || []).length;
    }
    const badge = document.getElementById('badge-pending-approvals');
    if (badge) {
      badge.textContent = count;
      if (count > 0) {
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    }
  } catch (err) {
    console.warn('Failed to load pending approvals count:', err);
  }
}

// ----------------------------------------------------------------------------
// 1. Operating Mode & Autonomous Execution Controls
// ----------------------------------------------------------------------------
async function setOperatingMode(mode) {
  try {
    const res = await fetch('/api/agent/preferences', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ operating_mode: mode })
    });
    if (res.ok) {
      const data = await res.json();
      currentAgentPreferences = data.preferences;
      updateOperatingModeUI(mode);
      showToast(`Operating mode updated to ${formatModeName(mode)}`, 'success');
    } else {
      showToast('Failed to change operating mode', 'error');
    }
  } catch (err) {
    showToast('Network error updating operating mode', 'error');
  }
}

function formatModeName(mode) {
  if (mode === 'FULLY_AUTONOMOUS') return 'Fully Autonomous';
  if (mode === 'APPROVAL_MODE') return 'Approval Mode';
  if (mode === 'ASSISTED') return 'Assisted Mode';
  return mode;
}

function updateOperatingModeUI(mode) {
  const badge = document.getElementById('agent-active-mode-badge');
  if (badge) {
    badge.textContent = formatModeName(mode);
  }

  const modes = ['autonomous', 'approval', 'assisted'];
  const modeKeyMap = {
    'FULLY_AUTONOMOUS': 'autonomous',
    'APPROVAL_MODE': 'approval',
    'ASSISTED': 'assisted'
  };
  const activeKey = modeKeyMap[mode] || 'autonomous';

  modes.forEach(m => {
    const btn = document.getElementById(`mode-btn-${m}`);
    const check = document.getElementById(`mode-check-${m}`);
    if (btn) {
      if (m === activeKey) {
        btn.classList.add('border-cyan-500/40', 'bg-cyan-950/20');
        btn.classList.remove('border-[#1a2336]', 'bg-[#06080d]');
      } else {
        btn.classList.remove('border-cyan-500/40', 'bg-cyan-950/20');
        btn.classList.add('border-[#1a2336]', 'bg-[#06080d]');
      }
    }
    if (check) {
      if (m === activeKey) {
        check.classList.remove('hidden', 'text-slate-600');
        check.classList.add('text-cyan-400');
      } else {
        check.classList.add('hidden');
      }
    }
  });

  const select = document.getElementById('pref-operating-mode');
  if (select) select.value = mode;
}

async function triggerAutonomousCycle() {
  const btn = document.getElementById('btn-run-agent-cycle');
  const batchSelect = document.getElementById('agent-cycle-batch-size');
  const rawVal = batchSelect ? parseInt(batchSelect.value) : 0;
  // 0 means "All Suitable Jobs" — send a very large limit so backend processes everything
  const limit = rawVal === 0 ? 9999 : (rawVal || 9999);

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i><span>Executing Cycle...</span>';
  }

  try {
    const res = await fetch(`/api/agent/run-cycle?limit=${limit}`, {
      method: 'POST',
      headers: getAuthHeaders()
    });

    if (res.ok) {
      const data = await res.json();
      showToast(`Autonomous cycle finished! ${data.jobs_processed || 0} jobs processed, ${data.applications_created || 0} applications created.`, 'success');
      loadAgentDashboard();
      loadPendingApprovalsCount();
      if (currentAgentTab === 'timeline') loadAgentTimeline();
      if (currentAgentTab === 'approvals') loadAgentApprovals();
      if (currentAgentTab === 'outreach') loadAgentOutreach();
    } else {
      const err = await res.json();
      showToast(err.detail || 'Autonomous cycle failed', 'error');
    }
  } catch (err) {
    showToast('Network error triggering autonomous cycle', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-bolt text-yellow-300"></i><span>Run Autonomous Cycle</span>';
    }
  }
}

// ----------------------------------------------------------------------------
// 2. Overview Dashboard Loader
// ----------------------------------------------------------------------------
async function loadAgentDashboard() {
  try {
    const res = await fetch('/api/analytics/agent-dashboard', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const d = await res.json();
    currentAgentMetrics = d;

    // Update Hero & Stat Counters
    const statJobs = document.getElementById('stat-agent-total-jobs');
    const statResumes = document.getElementById('stat-agent-resumes');
    const statApps = document.getElementById('stat-agent-applications');
    const statReplies = document.getElementById('stat-agent-replies');
    const statRate = document.getElementById('stat-agent-response-rate');

    if (statJobs) statJobs.textContent = (d.jobs?.total_live_jobs || 1001).toLocaleString();
    if (statResumes) statResumes.textContent = (d.applications?.resumes_synthesized || 0).toLocaleString();
    if (statApps) statApps.textContent = (d.applications?.total_applications || 0).toLocaleString();
    if (statReplies) statReplies.textContent = (d.outreach?.recruiter_replies || 0).toLocaleString();
    if (statRate) statRate.textContent = `${d.outreach?.positive_response_rate || 0}% Positive`;

    // Quota Gauge
    const appliedToday = d.limits?.applications_today || 0;
    const maxDaily = d.limits?.max_daily_applications || 25;
    const remaining = d.limits?.remaining_today !== undefined ? d.limits.remaining_today : Math.max(0, maxDaily - appliedToday);
    const portalCap = d.limits?.max_portal_applications || 10;

    const quotaCount = document.getElementById('agent-quota-count');
    const quotaMax = document.getElementById('agent-quota-max');
    const quotaRemaining = document.getElementById('agent-quota-remaining');
    const quotaPortalCap = document.getElementById('agent-portal-cap');
    const quotaBar = document.getElementById('agent-quota-progress-bar');

    if (quotaCount) quotaCount.textContent = appliedToday;
    if (quotaMax) quotaMax.textContent = maxDaily;
    if (quotaRemaining) quotaRemaining.textContent = `${remaining} left`;
    if (quotaPortalCap) quotaPortalCap.textContent = portalCap;
    if (quotaBar) {
      const pct = Math.min(100, Math.round((appliedToday / Math.max(1, maxDaily)) * 100));
      quotaBar.style.width = `${pct}%`;
    }

    // Operating mode badge
    if (d.limits?.operating_mode) {
      updateOperatingModeUI(d.limits.operating_mode);
    }

    // Render Portal Breakdown
    const portalsContainer = document.getElementById('agent-dashboard-portals-summary');
    if (portalsContainer && d.portals) {
      const portalEntries = Object.entries(d.portals);
      if (portalEntries.length === 0) {
        portalsContainer.innerHTML = '<p class="text-slate-500 text-center py-4">No portals recorded.</p>';
      } else {
        portalsContainer.innerHTML = portalEntries.map(([name, p]) => {
          const statusClass = p.enabled ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/30' : 'text-slate-500 bg-slate-900 border-slate-700';
          const statusText = p.enabled ? 'ACTIVE' : 'OFF';
          return `
            <div class="p-2 rounded-xl bg-[#06080d] border border-[#1a2336] flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full ${p.enabled ? 'bg-emerald-400' : 'bg-slate-600'}"></span>
                <span class="font-bold text-white text-xs">${name}</span>
                <span class="text-[10px] text-slate-500 uppercase">(${p.source_type || 'Feed'})</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="text-[11px] text-slate-300 font-semibold">${p.active_jobs || 0} jobs</span>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-bold border ${statusClass}">${statusText}</span>
              </div>
            </div>
          `;
        }).join('');
      }
    }

    // Render Recruiter Sentiment Breakdown
    const sentimentContainer = document.getElementById('agent-dashboard-sentiment-summary');
    if (sentimentContainer && d.sentiment_breakdown) {
      const sentimentColors = {
        'INTERVIEW': 'stage-outcome-interview',
        'POSITIVE': 'stage-job-analyzed',
        'NEUTRAL': 'stage-pill text-slate-300 bg-slate-800',
        'FOLLOWUP_REQUIRED': 'stage-email-sent',
        'ACTION_REQUIRED': 'stage-hr-found',
        'NEGATIVE': 'stage-pill text-amber-400 bg-amber-950/60',
        'REJECTION': 'stage-outcome-rejection'
      };
      const items = Object.entries(d.sentiment_breakdown);
      sentimentContainer.innerHTML = items.map(([category, count]) => {
        const cls = sentimentColors[category] || 'stage-job-found';
        return `
          <div class="p-2 rounded-xl bg-[#06080d] border border-[#1a2336] flex items-center justify-between">
            <span class="stage-pill ${cls}">${category}</span>
            <span class="font-bold text-white text-xs">${count} replies</span>
          </div>
        `;
      }).join('');
    }

    // Render Weights & Learning Insights
    const weightsContainer = document.getElementById('agent-dashboard-weights-summary');
    if (weightsContainer && d.learning_insights) {
      const weights = d.learning_insights.current_weights || {};
      const wItems = [
        { key: 'skills_weight', label: 'Technical Skills Match' },
        { key: 'semantic_weight', label: 'Semantic TF-IDF Fit' },
        { key: 'title_weight', label: 'Job Title Alignment' },
        { key: 'experience_weight', label: 'Experience Level Alignment' },
        { key: 'location_weight', label: 'Location & Work Mode' }
      ];
      weightsContainer.innerHTML = wItems.map(item => {
        const val = weights[item.key] !== undefined ? Math.round(weights[item.key] * 100) : 20;
        return `
          <div>
            <div class="flex items-center justify-between text-[11px] mb-1">
              <span class="text-slate-300">${item.label}</span>
              <strong class="text-cyan-400">${val}%</strong>
            </div>
            <div class="w-full bg-[#111827] h-1.5 rounded-full overflow-hidden">
              <div class="bg-gradient-to-r from-pink-500 to-indigo-500 h-full rounded-full" style="width: ${val * 2}%;"></div>
            </div>
          </div>
        `;
      }).join('');
    }

  } catch (err) {
    console.error('Failed to load agent dashboard data:', err);
  }
}

// ----------------------------------------------------------------------------
// 3. 9-Stage Activity Timeline
// ----------------------------------------------------------------------------
async function loadAgentTimeline() {
  const container = document.getElementById('agent-timeline-stream');
  if (container) container.innerHTML = '<div class="text-slate-500 text-center py-6 text-xs"><i class="fa-solid fa-spinner animate-spin mr-2"></i>Loading timeline events...</div>';

  try {
    const res = await fetch('/api/agent/timeline?limit=60', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const events = await res.json();
    currentTimelineEvents = events;
    renderTimelineItems(events);
  } catch (err) {
    if (container) container.innerHTML = '<p class="text-rose-400 text-center py-6 text-xs">Failed to load timeline events.</p>';
  }
}

function filterTimelineEvents() {
  const select = document.getElementById('timeline-stage-filter');
  const stage = select ? select.value : '';
  if (!stage) {
    renderTimelineItems(currentTimelineEvents);
  } else {
    const filtered = currentTimelineEvents.filter(e => e.stage === stage);
    renderTimelineItems(filtered);
  }
}

function renderTimelineItems(events) {
  const container = document.getElementById('agent-timeline-stream');
  if (!container) return;

  if (!events || events.length === 0) {
    container.innerHTML = `
      <div class="text-center py-10 text-xs text-slate-500 space-y-2">
        <i class="fa-solid fa-timeline text-2xl text-slate-700"></i>
        <p>No activity events recorded for this selection.</p>
        <p class="text-[11px] text-slate-600">Run an autonomous cycle to observe the 9-stage progression.</p>
      </div>
    `;
    return;
  }

  const stageIcons = {
    'JOB_FOUND': 'fa-solid fa-compass text-cyan-400',
    'JOB_ANALYZED': 'fa-solid fa-brain text-indigo-400',
    'RESUME_CUSTOMIZED': 'fa-solid fa-file-code text-emerald-400',
    'APPLICATION_SUBMITTED': 'fa-solid fa-paper-plane text-sky-400',
    'HR_CONTACT_FOUND': 'fa-solid fa-id-badge text-purple-400',
    'COLD_EMAIL_SENT': 'fa-solid fa-envelope-open-text text-amber-400',
    'RECRUITER_RESPONSE_RECEIVED': 'fa-solid fa-reply text-blue-400',
    'RESPONSE_ANALYZED': 'fa-solid fa-microscope text-pink-400',
    'OUTCOME_INTERVIEW': 'fa-solid fa-trophy text-emerald-400',
    'OUTCOME_REJECTION': 'fa-solid fa-flag text-rose-400',
    'OUTCOME_FOLLOWUP': 'fa-solid fa-clock-rotate-left text-amber-400'
  };

  const stageClassMap = {
    'JOB_FOUND': 'stage-job-found',
    'JOB_ANALYZED': 'stage-job-analyzed',
    'RESUME_CUSTOMIZED': 'stage-resume-customized',
    'APPLICATION_SUBMITTED': 'stage-app-submitted',
    'HR_CONTACT_FOUND': 'stage-hr-found',
    'COLD_EMAIL_SENT': 'stage-email-sent',
    'RECRUITER_RESPONSE_RECEIVED': 'stage-recruiter-replied',
    'RESPONSE_ANALYZED': 'stage-response-analyzed',
    'OUTCOME_INTERVIEW': 'stage-outcome-interview',
    'OUTCOME_REJECTION': 'stage-outcome-rejection',
    'OUTCOME_FOLLOWUP': 'stage-email-sent'
  };

  container.innerHTML = events.map(ev => {
    const icon = stageIcons[ev.stage] || 'fa-solid fa-circle-dot text-slate-400';
    const pillClass = stageClassMap[ev.stage] || 'stage-job-found';
    const timeStr = formatDate(ev.created_at);

    let extraAction = '';
    if (ev.application_id) {
      extraAction = `
        <button onclick="openLatexResumeModal(null, '${ev.application_id}')" class="text-[10px] text-emerald-400 hover:text-emerald-300 font-semibold flex items-center space-x-1">
          <i class="fa-solid fa-file-code"></i>
          <span>View LaTeX Resume</span>
        </button>
      `;
    }

    return `
      <div class="timeline-item">
        <div class="timeline-line"></div>
        <div class="timeline-dot">
          <i class="${icon} text-[10px]"></i>
        </div>
        
        <div class="p-3.5 rounded-xl bg-[#06080d] border border-[#1a2336] hover:border-[#223048] transition space-y-1.5">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center space-x-2">
              <span class="stage-pill ${pillClass}">${ev.stage.replace(/_/g, ' ')}</span>
              <strong class="text-white text-xs">${ev.company || 'Direct Employer'}</strong>
              ${ev.job_title ? `<span class="text-slate-400 text-xs">&bull; ${ev.job_title}</span>` : ''}
            </div>
            <span class="text-[10px] text-slate-500">${timeStr}</span>
          </div>

          <p class="text-xs text-slate-300 leading-relaxed">${ev.details || ''}</p>

          ${extraAction ? `<div class="pt-1 flex items-center space-x-3">${extraAction}</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

// ----------------------------------------------------------------------------
// 4. Approval Queue Loader & Actions
// ----------------------------------------------------------------------------
async function loadAgentApprovals() {
  const appsList = document.getElementById('approval-applications-list');
  const emailsList = document.getElementById('approval-emails-list');
  const questionsList = document.getElementById('approval-questions-list');

  try {
    const [resApprovals, resQuestions] = await Promise.all([
      fetch('/api/agent/approvals', { headers: getAuthHeaders() }),
      fetch('/api/learner/pending-questions', { headers: getAuthHeaders() })
    ]);

    let totalPending = 0;

    // Applications & Emails
    if (resApprovals.ok) {
      const d = await resApprovals.json();
      const apps = d.pending_applications || [];
      const emails = d.pending_emails || [];
      totalPending += apps.length + emails.length;

      // Render Applications
      if (appsList) {
        if (apps.length === 0) {
          appsList.innerHTML = '<div class="p-4 rounded-xl bg-[#06080d] border border-[#1a2336] text-center text-xs text-slate-500 col-span-full">No pending applications awaiting approval.</div>';
        } else {
          appsList.innerHTML = apps.map(app => `
            <div class="p-4 rounded-xl bg-[#06080d] border border-[#1a2336] flex flex-col justify-between space-y-3">
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-bold text-cyan-400">${app.company}</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-950 text-indigo-300 border border-indigo-500/30">${Math.round((app.match_score || 0.8) * 100)}% Match</span>
                </div>
                <h4 class="text-sm font-bold text-white mb-1">${app.job_title}</h4>
                <p class="text-xs text-slate-400">Portal: <strong class="text-slate-300">${app.portal || 'Direct ATS'}</strong></p>
              </div>

              <div class="pt-2 border-t border-[#1a2336] flex items-center justify-between gap-2">
                <button onclick="openLatexResumeModal(null, '${app.id}')" class="text-xs text-emerald-400 hover:text-emerald-300 flex items-center space-x-1">
                  <i class="fa-solid fa-file-code"></i>
                  <span>LaTeX Resume</span>
                </button>
                <div class="flex items-center space-x-2">
                  <button onclick="rejectApplication('${app.id}')" class="p-2 rounded-lg bg-rose-950/40 text-rose-400 hover:bg-rose-900/50 text-xs" title="Dismiss">
                    <i class="fa-solid fa-xmark"></i>
                  </button>
                  <button onclick="approveApplication('${app.id}')" class="btn-primary py-1.5 px-3 text-xs font-bold rounded-lg flex items-center space-x-1">
                    <i class="fa-solid fa-check"></i>
                    <span>Approve &amp; Submit</span>
                  </button>
                </div>
              </div>
            </div>
          `).join('');
        }
      }

      // Render Cold Emails
      if (emailsList) {
        if (emails.length === 0) {
          emailsList.innerHTML = '<div class="p-4 rounded-xl bg-[#06080d] border border-[#1a2336] text-center text-xs text-slate-500 col-span-full">No pending cold email outreach drafts.</div>';
        } else {
          emailsList.innerHTML = emails.map(em => `
            <div class="p-4 rounded-xl bg-[#06080d] border border-[#1a2336] flex flex-col justify-between space-y-3">
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-bold text-amber-400">${em.company}</span>
                  <span class="text-[10px] text-slate-400">${em.recipient_email}</span>
                </div>
                <h4 class="text-xs font-bold text-white mb-1.5">${em.subject}</h4>
                <div class="p-2.5 rounded-lg bg-[#0b101b] border border-[#1a2336] text-[11px] text-slate-300 max-h-24 overflow-y-auto whitespace-pre-line font-sans">
                  ${em.body}
                </div>
              </div>

              <div class="pt-2 border-t border-[#1a2336] flex items-center justify-end space-x-2">
                <button onclick="rejectEmail('${em.id}')" class="p-2 rounded-lg bg-rose-950/40 text-rose-400 hover:bg-rose-900/50 text-xs" title="Dismiss">
                  <i class="fa-solid fa-xmark"></i>
                </button>
                <button onclick="approveEmail('${em.id}')" class="btn-primary py-1.5 px-3 text-xs font-bold rounded-lg flex items-center space-x-1">
                  <i class="fa-solid fa-paper-plane"></i>
                  <span>Approve &amp; Send</span>
                </button>
              </div>
            </div>
          `).join('');
        }
      }
    }

    // Render Sensitive Questions Awaiting Confirmation
    if (resQuestions.ok && questionsList) {
      const questions = await resQuestions.json();
      totalPending += questions.length;

      if (questions.length === 0) {
        questionsList.innerHTML = '<div class="p-4 rounded-xl bg-[#06080d] border border-[#1a2336] text-center text-xs text-slate-500">All questions verified. No pending sensitive inquiries.</div>';
      } else {
        questionsList.innerHTML = questions.map(q => `
          <div class="p-4 rounded-xl bg-[#06080d] border border-[#1a2336] space-y-3" id="pending-q-card-${q.id}">
            <div class="flex items-start justify-between gap-2">
              <div>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-pink-950 text-pink-300 border border-pink-500/30 uppercase mr-2">
                  ${q.category || 'Sensitive Screener'}
                </span>
                <span class="text-xs font-bold text-white">${q.question_text}</span>
              </div>
              <span class="text-[10px] text-slate-500">${formatDate(q.created_at)}</span>
            </div>

            ${q.context ? `<p class="text-[11px] text-slate-400 italic">Context: ${q.context}</p>` : ''}

            <div class="space-y-2">
              <input type="text" id="pending-q-input-${q.id}" placeholder="Type your definitive answer here..." class="w-full bg-[#0b101b] border border-[#223048] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500" />
              
              <div class="flex items-center justify-between">
                <label class="flex items-center space-x-2 text-[11px] text-slate-400 cursor-pointer">
                  <input type="checkbox" id="pending-q-save-${q.id}" checked class="rounded border-[#223048] bg-[#0b101b] text-cyan-500" />
                  <span>Save answer to Candidate Knowledge Base for future portals</span>
                </label>

                <button onclick="confirmPendingQuestion('${q.id}')" class="btn-primary py-1.5 px-4 text-xs font-bold rounded-xl flex items-center space-x-1.5">
                  <i class="fa-solid fa-check"></i>
                  <span>Confirm &amp; Answer</span>
                </button>
              </div>
            </div>
          </div>
        `).join('');
      }
    }

    // Update Badge
    const badge = document.getElementById('badge-pending-approvals');
    if (badge) {
      badge.textContent = totalPending;
      if (totalPending > 0) {
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    }

  } catch (err) {
    console.error('Failed to load approvals:', err);
  }
}

async function approveApplication(appId) {
  try {
    const res = await fetch(`/api/agent/approvals/application/${appId}/approve`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (res.ok) {
      showToast('Application approved and submitted successfully!', 'success');
      loadAgentApprovals();
      loadAgentDashboard();
    } else {
      showToast('Failed to approve application', 'error');
    }
  } catch (err) {
    showToast('Network error approving application', 'error');
  }
}

async function rejectApplication(appId) {
  try {
    const res = await fetch(`/api/agent/approvals/application/${appId}/reject`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (res.ok) {
      showToast('Application dismissed from queue', 'info');
      loadAgentApprovals();
    }
  } catch (err) {
    showToast('Network error', 'error');
  }
}

async function approveEmail(emailId) {
  try {
    const res = await fetch(`/api/agent/approvals/email/${emailId}/approve`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (res.ok) {
      showToast('Cold email approved and transmitted to recruiter!', 'success');
      loadAgentApprovals();
      loadAgentDashboard();
    } else {
      showToast('Failed to approve email', 'error');
    }
  } catch (err) {
    showToast('Network error approving email', 'error');
  }
}

async function rejectEmail(emailId) {
  try {
    const res = await fetch(`/api/agent/approvals/email/${emailId}/reject`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (res.ok) {
      showToast('Outreach email dismissed', 'info');
      loadAgentApprovals();
    }
  } catch (err) {
    showToast('Network error', 'error');
  }
}

async function confirmPendingQuestion(qId) {
  const input = document.getElementById(`pending-q-input-${qId}`);
  const saveCheck = document.getElementById(`pending-q-save-${qId}`);
  if (!input || !input.value.trim()) {
    showToast('Please enter an answer to confirm', 'warning');
    return;
  }

  const answer = input.value.trim();
  const saveKb = saveCheck ? saveCheck.checked : true;

  try {
    const res = await fetch(`/api/learner/confirm-question/${qId}`, {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer: answer, save_to_knowledge_base: saveKb })
    });

    if (res.ok) {
      showToast('Question confirmed and saved!', 'success');
      loadAgentApprovals();
      if (currentAgentTab === 'kb') loadAgentKnowledgeBase();
    } else {
      showToast('Failed to confirm question', 'error');
    }
  } catch (err) {
    showToast('Network error confirming question', 'error');
  }
}

// ----------------------------------------------------------------------------
// 5. Candidate Preferences & Master Resume
// ----------------------------------------------------------------------------
async function loadAgentPreferences(populateForm = true) {
  try {
    const res = await fetch('/api/agent/preferences', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    currentAgentPreferences = data.preferences || {};

    if (populateForm) {
      const titles = (currentAgentPreferences.target_job_titles || []).join(', ');
      const locs = (currentAgentPreferences.preferred_locations || []).join(', ');

      const titlesEl = document.getElementById('pref-target-titles');
      const locsEl = document.getElementById('pref-locations');
      const workEl = document.getElementById('pref-work-pref');
      const expEl = document.getElementById('pref-exp-level');
      const minSalEl = document.getElementById('pref-min-salary');
      const currEl = document.getElementById('pref-salary-curr');
      const maxDailyEl = document.getElementById('pref-max-daily');
      const maxPortalEl = document.getElementById('pref-max-portal');
      const resumeEl = document.getElementById('pref-master-resume-text');

      if (titlesEl) titlesEl.value = titles;
      if (locsEl) locsEl.value = locs;
      if (workEl) workEl.value = currentAgentPreferences.work_preference || 'ANY';
      if (expEl) expEl.value = currentAgentPreferences.experience_level || 'MID';
      if (minSalEl && currentAgentPreferences.min_salary) minSalEl.value = currentAgentPreferences.min_salary;
      if (currEl) currEl.value = currentAgentPreferences.salary_currency || 'INR';
      if (maxDailyEl) maxDailyEl.value = currentAgentPreferences.max_daily_applications || 25;
      if (maxPortalEl) maxPortalEl.value = currentAgentPreferences.max_portal_applications || 10;
      if (resumeEl && currentAgentPreferences.master_resume_text) resumeEl.value = currentAgentPreferences.master_resume_text;
    }

    if (currentAgentPreferences.operating_mode) {
      updateOperatingModeUI(currentAgentPreferences.operating_mode);
    }

  } catch (err) {
    console.error('Failed to load agent preferences:', err);
  }
}

async function handleSavePreferences(event) {
  event.preventDefault();
  const btn = document.getElementById('btn-save-preferences');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i><span>Saving...</span>';
  }

  const titles = (document.getElementById('pref-target-titles')?.value || '')
    .split(',')
    .map(t => t.trim())
    .filter(Boolean)
    .slice(0, 3);

  const locs = (document.getElementById('pref-locations')?.value || '')
    .split(',')
    .map(l => l.trim())
    .filter(Boolean);

  const payload = {
    target_job_titles: titles,
    preferred_locations: locs,
    work_preference: document.getElementById('pref-work-pref')?.value || 'ANY',
    experience_level: document.getElementById('pref-exp-level')?.value || 'MID',
    min_salary: parseFloat(document.getElementById('pref-min-salary')?.value) || null,
    salary_currency: document.getElementById('pref-salary-curr')?.value || 'INR',
    max_daily_applications: parseInt(document.getElementById('pref-max-daily')?.value) || 25,
    max_portal_applications: parseInt(document.getElementById('pref-max-portal')?.value) || 10,
    master_resume_text: document.getElementById('pref-master-resume-text')?.value || ''
  };

  try {
    const res = await fetch('/api/agent/preferences', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const d = await res.json();
      currentAgentPreferences = d.preferences;
      showToast('Agent preferences & Master Resume saved successfully!', 'success');
      loadAgentDashboard();
    } else {
      const err = await res.json();
      showToast(err.detail || 'Failed to save preferences', 'error');
    }
  } catch (err) {
    showToast('Network error saving preferences', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-floppy-disk mr-1.5"></i><span>Save Agent Configuration</span>';
    }
  }
}

function handleResumeFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(e) {
    const text = e.target?.result;
    if (text) {
      const resumeEl = document.getElementById('pref-master-resume-text');
      if (resumeEl) {
        resumeEl.value = text;
        showToast(`Extracted resume text from "${file.name}"!`, 'success');
      }
    }
  };
  reader.onerror = function() {
    showToast('Failed to read resume file', 'error');
  };
  reader.readAsText(file);
}

// ----------------------------------------------------------------------------
// 6. Portal Permissions
// ----------------------------------------------------------------------------
async function loadPortalPermissions() {
  const tbody = document.getElementById('portal-permissions-body');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="py-6 text-center text-slate-500"><i class="fa-solid fa-spinner animate-spin mr-2"></i>Loading portal registry...</td></tr>';

  try {
    const res = await fetch('/api/agent/portals', { headers: getAuthHeaders() });
    if (!res.ok) return;
    const portals = await res.json();
    currentPortalList = portals;
    renderPortalsTable(portals);
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="6" class="py-6 text-center text-rose-400">Failed to load portal permissions.</td></tr>';
  }
}

function filterPortalsList() {
  const q = (document.getElementById('portal-filter-search')?.value || '').toLowerCase().trim();
  if (!q) {
    renderPortalsTable(currentPortalList);
  } else {
    const filtered = currentPortalList.filter(p => p.portal_name.toLowerCase().includes(q) || (p.source_type || '').toLowerCase().includes(q));
    renderPortalsTable(filtered);
  }
}

function renderPortalsTable(portals) {
  const tbody = document.getElementById('portal-permissions-body');
  if (!tbody) return;

  if (portals.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="py-6 text-center text-slate-500">No matching portals found.</td></tr>';
    return;
  }

  tbody.innerHTML = portals.map(p => {
    const isChecked = p.enabled ? 'checked' : '';
    const safePortalName = p.portal_name.replace(/'/g, "\'");
    return `
      <tr class="hover:bg-[#111827]/40 transition">
        <td class="py-3 px-3">
          <div class="flex items-center space-x-2">
            <div class="w-6 h-6 rounded bg-[#111827] flex items-center justify-center text-xs font-bold text-cyan-400">
              <i class="fa-solid fa-network-wired"></i>
            </div>
            <div>
              <span class="font-bold text-white block">${p.portal_name}</span>
              ${p.authorization_required ? '<span class="text-[10px] text-amber-400">Authorized Boundary</span>' : ''}
            </div>
          </div>
        </td>
        <td class="py-3 px-3">
          <span class="px-2 py-0.5 rounded bg-[#111827] border border-[#223048] text-[10px] font-medium text-slate-300">
            ${p.source_type || 'Direct Ingestion'}
          </span>
        </td>
        <td class="py-3 px-3">
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" ${isChecked} onchange="togglePortalPermission('${safePortalName}', this.checked)" class="sr-only peer">
            <div class="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
          </label>
        </td>
        <td class="py-3 px-3">
          <div class="flex items-center space-x-1.5">
            <input type="number" min="1" max="50" value="${p.max_daily_applications || 10}" id="portal-limit-${p.portal_name.replace(/[^a-zA-Z0-9]/g, '_')}" class="w-16 bg-[#06080d] border border-[#223048] rounded-lg px-2 py-1 text-xs text-white" />
            <button onclick="savePortalDailyLimit('${safePortalName}')" class="p-1 text-slate-400 hover:text-cyan-400" title="Save daily limit">
              <i class="fa-solid fa-check text-xs"></i>
            </button>
          </div>
        </td>
        <td class="py-3 px-3 font-semibold text-slate-300">
          ${p.active_jobs || 0}
        </td>
        <td class="py-3 px-3 text-right">
          <span class="text-[11px] ${p.enabled ? 'text-emerald-400' : 'text-slate-500'} font-bold">
            ${p.enabled ? 'ENABLED' : 'PAUSED'}
          </span>
        </td>
      </tr>
    `;
  }).join('');
}

async function togglePortalPermission(portalName, enabled) {
  try {
    const res = await fetch(`/api/agent/portals/${encodeURIComponent(portalName)}`, {
      method: 'PUT',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: enabled })
    });
    if (res.ok) {
      showToast(`${portalName} portal ${enabled ? 'enabled' : 'disabled'}!`, 'success');
      loadAgentDashboard();
    } else {
      showToast('Failed to update portal permission', 'error');
    }
  } catch (err) {
    showToast('Network error updating portal', 'error');
  }
}

async function savePortalDailyLimit(portalName) {
  const safeId = portalName.replace(/[^a-zA-Z0-9]/g, '_');
  const input = document.getElementById(`portal-limit-${safeId}`);
  if (!input) return;

  const limit = parseInt(input.value) || 10;
  try {
    const res = await fetch(`/api/agent/portals/${encodeURIComponent(portalName)}`, {
      method: 'PUT',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_daily_applications: limit })
    });
    if (res.ok) {
      showToast(`Updated daily limit for ${portalName} to ${limit}!`, 'success');
    } else {
      showToast('Failed to save portal limit', 'error');
    }
  } catch (err) {
    showToast('Network error', 'error');
  }
}

// ----------------------------------------------------------------------------
// 7. Recruiter Outreach & Follow-up Cadence
// ----------------------------------------------------------------------------
async function loadAgentOutreach() {
  const contactsBody = document.getElementById('outreach-contacts-body');
  const emailsBody = document.getElementById('outreach-emails-body');
  const contactsCount = document.getElementById('recruiter-contacts-count');
  const emailsCount = document.getElementById('outreach-emails-count');

  try {
    const [resContacts, resEmails] = await Promise.all([
      fetch('/api/outreach/contacts', { headers: getAuthHeaders() }),
      fetch('/api/outreach/emails', { headers: getAuthHeaders() })
    ]);

    // Recruiter Contacts
    if (resContacts.ok && contactsBody) {
      const contacts = await resContacts.json();
      if (contactsCount) contactsCount.textContent = `${contacts.length} Contacts Found`;

      if (contacts.length === 0) {
        contactsBody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-slate-500">No recruiter contacts discovered yet. Run an autonomous cycle to auto-discover talent partners.</td></tr>';
      } else {
        contactsBody.innerHTML = contacts.map(c => `
          <tr class="hover:bg-[#111827]/40 transition">
            <td class="py-2.5 px-3">
              <span class="font-bold text-white block">${c.name}</span>
              <span class="text-[10px] text-slate-400">${c.role_title || 'Technical Recruiter'}</span>
            </td>
            <td class="py-2.5 px-3 font-semibold text-cyan-300">${c.company}</td>
            <td class="py-2.5 px-3 font-mono text-[11px] text-slate-300">${c.email}</td>
            <td class="py-2.5 px-3">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                ${Math.round((c.confidence_score || 0.85) * 100)}% Conf
              </span>
            </td>
            <td class="py-2.5 px-3 text-right text-[11px] text-slate-500">${formatDate(c.created_at)}</td>
          </tr>
        `).join('');
      }
    }

    // Cold Emails Log
    if (resEmails.ok && emailsBody) {
      const emails = await resEmails.json();
      currentSimEmails = emails;
      if (emailsCount) emailsCount.textContent = `${emails.length} Emails Transmitted`;

      // Update simulation dropdown
      const simSelect = document.getElementById('sim-reply-email-id');
      if (simSelect) {
        simSelect.innerHTML = '<option value="">Select an outreach email...</option>' +
          emails.map(e => `<option value="${e.id}">${e.company} &mdash; ${e.recipient_email} (${e.subject.slice(0, 35)}...)</option>`).join('');
      }

      if (emails.length === 0) {
        emailsBody.innerHTML = '<tr><td colspan="6" class="py-4 text-center text-slate-500">No outreach emails sent yet.</td></tr>';
      } else {
        emailsBody.innerHTML = emails.map(em => {
          const category = em.reply_category || em.response_category;
          let sentimentBadge = '<span class="text-slate-500 text-[10px]">Awaiting Reply</span>';
          if (category) {
            const colors = {
              'INTERVIEW': 'stage-outcome-interview',
              'INTERVIEW_OPPORTUNITY': 'stage-outcome-interview',
              'POSITIVE': 'stage-job-analyzed',
              'ACTION_REQUIRED': 'stage-resume-customized',
              'FOLLOWUP_REQUIRED': 'stage-hr-found',
              'FOLLOW_UP_REQUIRED': 'stage-hr-found',
              'REJECTION': 'stage-outcome-rejection',
              'NEGATIVE': 'stage-outcome-rejection',
              'NEUTRAL': 'stage-job-found'
            };
            const cls = colors[category] || 'stage-job-found';
            sentimentBadge = `<span class="stage-pill ${cls}">${category}</span>`;
          }

          return `
            <tr class="hover:bg-[#111827]/40 transition">
              <td class="py-2.5 px-3">
                <span class="font-bold text-white block">${em.company}</span>
                <span class="text-[10px] text-slate-400">${em.recipient_email}</span>
              </td>
              <td class="py-2.5 px-3 text-slate-300 max-w-xs truncate">${em.subject}</td>
              <td class="py-2.5 px-3">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold ${em.status === 'SENT' ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/30' : 'bg-slate-800 text-slate-300'}">
                  ${em.status}
                </span>
              </td>
              <td class="py-2.5 px-3 text-slate-400 font-semibold">${em.follow_up_count || 0}</td>
              <td class="py-2.5 px-3">${sentimentBadge}</td>
              <td class="py-2.5 px-3 text-right text-[11px] text-slate-500">${formatDate(em.sent_at || em.created_at)}</td>
            </tr>
          `;
        }).join('');
      }
    }

  } catch (err) {
    console.error('Failed to load outreach logs:', err);
  }
}

async function triggerFollowups() {
  const btn = document.getElementById('btn-trigger-followups');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin mr-1"></i>Checking Cadence...';
  }

  try {
    const res = await fetch('/api/outreach/trigger-followups', {
      method: 'POST',
      headers: getAuthHeaders()
    });

    if (res.ok) {
      const data = await res.json();
      showToast(`Follow-up cadence executed! ${data.followups_sent || 0} follow-ups scheduled/sent.`, 'success');
      loadAgentOutreach();
      loadAgentDashboard();
    } else {
      showToast('Failed to trigger follow-up cadence', 'error');
    }
  } catch (err) {
    showToast('Network error triggering follow-ups', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-clock-rotate-left mr-1.5"></i><span>Trigger Follow-up Cadence</span>';
    }
  }
}

// ----------------------------------------------------------------------------
// Recruiter Reply Simulator Modal
// ----------------------------------------------------------------------------
function openRecruiterReplyModal() {
  const modal = document.getElementById('recruiter-reply-modal');
  if (modal) modal.classList.remove('hidden');
}

function closeRecruiterReplyModal() {
  const modal = document.getElementById('recruiter-reply-modal');
  if (modal) modal.classList.add('hidden');
}

function setSimReplyText(type) {
  const bodyEl = document.getElementById('sim-reply-body');
  if (!bodyEl) return;

  if (type === 'interview') {
    bodyEl.value = "Hi! Thank you for reaching out with your resume. We were very impressed by your background in scalable Python backend services. Are you free for an initial 30-minute technical interview this Thursday or Friday?";
  } else if (type === 'positive') {
    bodyEl.value = "Hello! Thanks for your email. I have forwarded your profile and customized resume to the Engineering Manager for review. We will be in touch shortly.";
  } else if (type === 'action') {
    bodyEl.value = "Hi, thank you for contacting us. Could you please confirm your current notice period, salary expectations, and whether you require visa sponsorship?";
  } else if (type === 'rejection') {
    bodyEl.value = "Dear candidate, thank you for your interest in our team. Unfortunately, we have decided to move forward with another candidate whose qualifications more closely match our current needs. We wish you the best in your search.";
  }
}

async function submitSimulateReply() {
  const emailSelect = document.getElementById('sim-reply-email-id');
  const bodyText = document.getElementById('sim-reply-body')?.value.trim();
  const emailId = emailSelect?.value;

  if (!emailId) {
    showToast('Please select a recipient email from the list', 'warning');
    return;
  }
  if (!bodyText) {
    showToast('Please provide recruiter reply text to analyze', 'warning');
    return;
  }

  const btn = document.getElementById('btn-submit-sim-reply');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner animate-spin mr-1"></i>Analyzing NLP Sentiment...';
  }

  try {
    const res = await fetch('/api/outreach/simulate-response', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ email_id: emailId, response_body: bodyText })
    });

    if (res.ok) {
      const data = await res.json();
      const resultBox = document.getElementById('sim-reply-result');
      const catEl = document.getElementById('sim-result-category');
      const notesEl = document.getElementById('sim-result-notes');

      if (resultBox && catEl && notesEl) {
        resultBox.classList.remove('hidden');
        catEl.textContent = data.category || 'ANALYZED';
        notesEl.textContent = data.notes || 'Inbound email analyzed and timeline event generated.';
      }

      showToast(`Response categorized as ${data.category}! Timeline updated.`, 'success');
      loadAgentOutreach();
      loadAgentDashboard();
    } else {
      const err = await res.json();
      showToast(err.detail || 'Failed to simulate reply', 'error');
    }
  } catch (err) {
    showToast('Network error analyzing recruiter response', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-microscope mr-1.5"></i><span>Analyze &amp; Process Response</span>';
    }
  }
}

// ----------------------------------------------------------------------------
// 8. Self-Learning Engine & Verified Knowledge Base
// ----------------------------------------------------------------------------
async function loadAgentKnowledgeBase() {
  const kbList = document.getElementById('kb-facts-list');
  const metricsList = document.getElementById('kb-learning-metrics-list');
  const factsCount = document.getElementById('kb-facts-count');

  try {
    const [resKb, resInsights] = await Promise.all([
      fetch('/api/learner/knowledge-base', { headers: getAuthHeaders() }),
      fetch('/api/learner/insights', { headers: getAuthHeaders() })
    ]);

    // Verified Facts
    if (resKb.ok && kbList) {
      const facts = await resKb.json();
      if (factsCount) factsCount.textContent = `${facts.length} Facts`;

      if (facts.length === 0) {
        kbList.innerHTML = '<div class="text-slate-500 text-center py-6">No verified facts recorded yet.</div>';
      } else {
        kbList.innerHTML = facts.map(f => `
          <div class="p-3 rounded-xl bg-[#06080d] border border-[#1a2336] flex items-start justify-between gap-3">
            <div>
              <div class="flex items-center space-x-2 mb-1">
                <span class="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-500/30 uppercase">
                  ${f.category || 'General'}
                </span>
                <span class="font-bold text-white text-xs">${f.question}</span>
              </div>
              <p class="text-xs text-slate-300 pl-1">${f.verified_answer}</p>
            </div>
            <span class="text-[10px] text-emerald-400 font-bold flex items-center shrink-0">
              <i class="fa-solid fa-shield-check mr-1"></i>Verified
            </span>
          </div>
        `).join('');
      }
    }

    // Learned Metrics & Feature Correlations
    if (resInsights.ok && metricsList) {
      const insights = await resInsights.json();
      const topSkills = insights.top_performing_skills || [];
      const topSubjects = insights.top_performing_subject_patterns || [];
      const learningLog = insights.recent_metrics || [];

      metricsList.innerHTML = `
        <div class="space-y-4">
          <!-- Top Performing Skills -->
          <div class="p-3 rounded-xl bg-[#06080d] border border-[#1a2336] space-y-2">
            <span class="text-[11px] font-bold uppercase tracking-wider text-cyan-400 block">High-Converting Resume Skills</span>
            <div class="flex flex-wrap gap-1.5">
              ${topSkills.length > 0
                ? topSkills.map(s => `<span class="px-2 py-0.5 rounded bg-[#111827] text-slate-200 text-xs font-semibold border border-[#223048]"><i class="fa-solid fa-arrow-trend-up text-emerald-400 mr-1 text-[10px]"></i>${s}</span>`).join('')
                : '<span class="text-xs text-slate-500">Learning correlations in progress...</span>'
              }
            </div>
          </div>

          <!-- Subject Line Patterns -->
          <div class="p-3 rounded-xl bg-[#06080d] border border-[#1a2336] space-y-2">
            <span class="text-[11px] font-bold uppercase tracking-wider text-amber-400 block">Top Outreach Subject Lines</span>
            <div class="space-y-1 text-xs">
              ${topSubjects.length > 0
                ? topSubjects.map(sub => `<div class="p-2 rounded bg-[#111827] text-slate-300 truncate"><i class="fa-solid fa-envelope text-amber-400 mr-1.5 text-[10px]"></i>${sub}</div>`).join('')
                : '<span class="text-xs text-slate-500">Subject performance being benchmarked...</span>'
              }
            </div>
          </div>

          <!-- Self-Learning Adaptation Rule -->
          <div class="p-3 rounded-xl bg-[#06080d] border border-[#1a2336] text-[11px] text-slate-400 leading-relaxed">
            <strong class="text-slate-200 block mb-1">Safety &amp; Veracity Guarantee:</strong>
            The self-learning algorithm continuously adapts ranking weights and emphasizes matched skills from your Master Resume. It is mathematically restricted from hallucinating fake experience, unearned degrees, or unverified skills.
          </div>
        </div>
      `;
    }

  } catch (err) {
    console.error('Failed to load knowledge base data:', err);
  }
}

async function handleAddKbFact(event) {
  event.preventDefault();
  const qEl = document.getElementById('kb-add-question');
  const aEl = document.getElementById('kb-add-answer');
  const catEl = document.getElementById('kb-add-category');

  if (!qEl || !aEl) return;
  const question = qEl.value.trim();
  const answer = aEl.value.trim();
  const category = catEl ? catEl.value : 'career';

  if (!question || !answer) return;

  try {
    const res = await fetch('/api/learner/knowledge-base', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, answer, category })
    });

    if (res.ok) {
      showToast('Verified fact added to Knowledge Base!', 'success');
      qEl.value = '';
      aEl.value = '';
      loadAgentKnowledgeBase();
    } else {
      showToast('Failed to save fact', 'error');
    }
  } catch (err) {
    showToast('Network error', 'error');
  }
}

// ----------------------------------------------------------------------------
// 9. ATS-Compliant LaTeX & Overleaf Resume Generation
// ----------------------------------------------------------------------------
async function openLatexResumeModal(jobId, appId = null) {
  const modal = document.getElementById('latex-resume-modal');
  const codeViewer = document.getElementById('latex-code-viewer');
  const titleEl = document.getElementById('latex-modal-job-title');
  const companyEl = document.getElementById('latex-modal-company');
  const overleafBtn = document.getElementById('btn-overleaf-open');

  if (modal) modal.classList.remove('hidden');
  if (codeViewer) codeViewer.textContent = '% Synthesizing ATS LaTeX Resume matching target Job Description...\\n% Applying standard packages: geometry, enumitem, hyperref, titlesec...';

  try {
    let res;
    if (appId) {
      res = await fetch(`/api/resumes/${appId}/latex`, { headers: getAuthHeaders() });
    } else if (jobId) {
      res = await fetch('/api/resumes/generate-latex', {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId })
      });
    }

    if (res && res.ok) {
      const data = await res.json();
      currentLatexResume = {
        code: data.latex_code || '',
        app_id: data.application_id || appId,
        job_id: data.job_id || jobId,
        overleaf_url: data.overleaf_url || 'https://www.overleaf.com/docs'
      };

      if (codeViewer) codeViewer.textContent = data.latex_code || '% No LaTeX code returned';
      if (titleEl) titleEl.textContent = data.job_title || 'Target Position';
      if (companyEl) companyEl.textContent = data.company || 'Direct Employer';
      if (overleafBtn && data.overleaf_url) {
        overleafBtn.href = data.overleaf_url;
      }
    } else {
      const err = res ? await res.json() : { detail: 'Error' };
      if (codeViewer) codeViewer.textContent = `% Failed to generate LaTeX resume: ${err.detail || 'Server error'}`;
      showToast(err.detail || 'Failed to synthesize LaTeX resume', 'error');
    }
  } catch (err) {
    if (codeViewer) codeViewer.textContent = '% Network error generating ATS LaTeX resume.';
    showToast('Network error generating LaTeX resume', 'error');
  }
}

function closeLatexResumeModal() {
  const modal = document.getElementById('latex-resume-modal');
  if (modal) modal.classList.add('hidden');
}

function copyLatexCode() {
  if (!currentLatexResume.code) {
    showToast('No LaTeX code to copy', 'warning');
    return;
  }
  navigator.clipboard.writeText(currentLatexResume.code)
    .then(() => showToast('ATS-ready LaTeX code copied to clipboard!', 'success'))
    .catch(() => showToast('Failed to copy LaTeX code', 'error'));
}

function downloadLatexFile() {
  if (!currentLatexResume.code) {
    showToast('No LaTeX code available to download', 'warning');
    return;
  }

  // If application_id is available, direct download endpoint
  if (currentLatexResume.app_id) {
    window.location.href = `/api/resumes/${currentLatexResume.app_id}/download-tex`;
    return;
  }

  // Otherwise trigger client blob download
  const blob = new Blob([currentLatexResume.code], { type: 'text/x-tex;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `resume_${currentLatexResume.job_id || 'tailored'}.tex`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('Downloaded tailored .tex resume!', 'success');
}

function openLatexResumeForCurrentModalJob() {
  if (currentModalJobId) {
    openLatexResumeModal(currentModalJobId);
  }
}

function openInOverleafDirectly() {
  if (!currentLatexResume || !currentLatexResume.code) {
    showToast('Synthesizing LaTeX resume source...', 'info');
    return;
  }
  // Create dynamic form to POST directly to Overleaf docs snippet loader
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = 'https://www.overleaf.com/docs';
  form.target = '_blank';

  const snipInput = document.createElement('input');
  snipInput.type = 'hidden';
  snipInput.name = 'snip';
  snipInput.value = currentLatexResume.code;
  form.appendChild(snipInput);

  document.body.appendChild(form);
  form.submit();
  setTimeout(() => {
    try { document.body.removeChild(form); } catch (e) {}
  }, 1000);

  showToast('Opening ATS Resume project in Overleaf...', 'success');
}

function openRecruiterOutreach() {
  window.location.hash = 'outreach';
  switchView('agent', false);
  switchAgentTab('outreach');
  document.querySelectorAll('nav button').forEach(btn => {
    btn.classList.remove('nav-btn-active');
  });
  const activeNavBtn = document.getElementById('nav-btn-outreach');
  if (activeNavBtn) {
    activeNavBtn.classList.add('nav-btn-active');
  }
  loadAgentOutreach();
}

