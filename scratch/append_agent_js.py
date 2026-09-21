import os

js_code = '''

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
  const limit = batchSelect ? parseInt(batchSelect.value) || 5 : 5;

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
    const safePortalName = p.portal_name.replace(/'/g, "\\'");
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
          let sentimentBadge = '<span class="text-slate-500 text-[10px]">Awaiting Reply</span>';
          if (em.response_category) {
            const colors = {
              'INTERVIEW': 'stage-outcome-interview',
              'POSITIVE': 'stage-job-analyzed',
              'REJECTION': 'stage-outcome-rejection'
            };
            const cls = colors[em.response_category] || 'stage-job-found';
            sentimentBadge = `<span class="stage-pill ${cls}">${em.response_category}</span>`;
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
  if (codeViewer) codeViewer.textContent = '% Synthesizing ATS LaTeX Resume matching target Job Description...\n% Applying standard packages: geometry, enumitem, hyperref, titlesec...';

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
'''

app_js_path = 'src/frontend/app.js'
with open(app_js_path, 'r', encoding='utf-8') as f:
    existing = f.read()

updated = existing + '\n' + js_code

with open(app_js_path, 'w', encoding='utf-8') as f:
    f.write(updated)

print(f"app.js updated successfully! Total length: {len(updated)}")
