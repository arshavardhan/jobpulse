import os

agent_html = """
    <!-- ===================================================================== -->
    <!-- 4.10 VIEW: AUTONOMOUS AGENT HUB & CONTINUOUS COPILOT                   -->
    <!-- ===================================================================== -->
    <section id="view-agent" class="space-y-8 hidden">

      <!-- Agent Control Center Hero Banner -->
      <div class="relative overflow-hidden rounded-3xl border border-[#223048] bg-gradient-to-b from-[#0b101b] via-[#090d16] to-[#06080d] p-6 sm:p-8 shadow-2xl">
        <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-[#1a2336]">
          <div>
            <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 mb-3">
              <i class="fa-solid fa-microchip text-cyan-400"></i>
              <span>4-Module Persistent Autonomous Job Copilot</span>
            </div>
            <h1 class="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
              Agent <span class="jp-gradient-text">Autopilot Hub</span>
            </h1>
            <p class="text-xs sm:text-sm text-slate-300 mt-2 max-w-2xl leading-relaxed">
              Autonomous execution across 19+ platforms: searches verified live jobs, tailors ATS-compliant Overleaf LaTeX resumes, discovers HR talent contacts, sends personalized cold outreach, tracks outcomes, and adapts weights dynamically.
            </p>
          </div>

          <!-- Active Operating Mode Pill & Batch Trigger -->
          <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full lg:w-auto">
            <div class="p-3 bg-[#06080d] rounded-2xl border border-[#1a2336] flex flex-col justify-center">
              <span class="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">Active Operating Mode</span>
              <div class="flex items-center space-x-2">
                <span class="status-dot-pulse"></span>
                <span id="agent-active-mode-badge" class="text-xs font-extrabold text-cyan-300 uppercase tracking-wide">Fully Autonomous</span>
              </div>
            </div>

            <div class="flex items-center space-x-2 bg-[#06080d] p-2 rounded-2xl border border-[#1a2336]">
              <select id="agent-cycle-batch-size" class="bg-[#0b101b] text-white border border-[#223048] text-xs rounded-xl px-2.5 py-2 font-semibold focus:outline-none focus:border-cyan-500">
                <option value="3">3 Jobs</option>
                <option value="5" selected>5 Jobs</option>
                <option value="10">10 Jobs</option>
              </select>
              <button onclick="triggerAutonomousCycle()" id="btn-run-agent-cycle" class="btn-primary py-2.5 px-4 text-xs font-bold rounded-xl flex items-center space-x-2 shadow-lg shadow-cyan-500/20 whitespace-nowrap">
                <i class="fa-solid fa-bolt text-yellow-300"></i>
                <span>Run Autonomous Cycle</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Operating Mode Controls & Quota Progress Bar -->
        <div class="pt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- Mode Switcher Buttons -->
          <div class="lg:col-span-2 space-y-2">
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Candidate Operating Mode Control</span>
              <span class="text-[11px] text-slate-400">Select how autonomously the agent operates</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <button onclick="setOperatingMode('FULLY_AUTONOMOUS')" id="mode-btn-autonomous" class="p-3 rounded-xl border border-cyan-500/40 bg-cyan-950/20 text-left hover:border-cyan-400 transition flex flex-col justify-between">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-bold text-white flex items-center"><i class="fa-solid fa-bolt text-yellow-400 mr-1.5"></i>Autonomous</span>
                  <i id="mode-check-autonomous" class="fa-solid fa-circle-check text-cyan-400 text-xs"></i>
                </div>
                <p class="text-[10px] text-slate-400">Applies &amp; emails recruiters automatically based on your limits.</p>
              </button>

              <button onclick="setOperatingMode('APPROVAL_MODE')" id="mode-btn-approval" class="p-3 rounded-xl border border-[#1a2336] bg-[#06080d] text-left hover:border-amber-400 transition flex flex-col justify-between">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-bold text-slate-300 flex items-center"><i class="fa-solid fa-shield-halved text-amber-400 mr-1.5"></i>Approval Mode</span>
                  <i id="mode-check-approval" class="fa-solid fa-circle-check text-slate-600 text-xs hidden"></i>
                </div>
                <p class="text-[10px] text-slate-400">Prepares resumes &amp; outreach drafts, queues for 1-click confirmation.</p>
              </button>

              <button onclick="setOperatingMode('ASSISTED')" id="mode-btn-assisted" class="p-3 rounded-xl border border-[#1a2336] bg-[#06080d] text-left hover:border-blue-400 transition flex flex-col justify-between">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-bold text-slate-300 flex items-center"><i class="fa-solid fa-handshake text-blue-400 mr-1.5"></i>Assisted</span>
                  <i id="mode-check-assisted" class="fa-solid fa-circle-check text-slate-600 text-xs hidden"></i>
                </div>
                <p class="text-[10px] text-slate-400">Prepares tailored LaTeX resumes; application links left to candidate.</p>
              </button>
            </div>
          </div>

          <!-- Quota & Safety Limits -->
          <div class="p-4 bg-[#06080d] rounded-2xl border border-[#1a2336] flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-xs font-bold text-slate-300">Daily Applications Quota</span>
                <span class="text-xs font-bold text-cyan-400"><span id="agent-quota-count">0</span> / <span id="agent-quota-max">50</span></span>
              </div>
              <div class="w-full bg-[#111827] h-2.5 rounded-full overflow-hidden border border-[#223048]">
                <div id="agent-quota-progress-bar" class="bg-gradient-to-r from-cyan-500 to-indigo-500 h-full rounded-full transition-all duration-500" style="width: 0%;"></div>
              </div>
            </div>

            <div class="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-[#1a2336]">
              <span>Portal Cap: <strong class="text-white" id="agent-portal-cap">10</strong> / portal</span>
              <span>Remaining Today: <strong class="text-emerald-400" id="agent-quota-remaining">50 left</strong></span>
            </div>
          </div>

        </div>
      </div>

      <!-- Agent Sub-Navigation Tabs -->
      <div class="flex items-center space-x-2 overflow-x-auto pb-2 border-b border-[#1a2336] scrollbar-none">
        <button onclick="switchAgentTab('dashboard')" id="agent-tab-dashboard" class="agent-tab-btn agent-tab-active flex items-center space-x-2">
          <i class="fa-solid fa-chart-line text-cyan-400"></i>
          <span>Overview</span>
        </button>
        <button onclick="switchAgentTab('timeline')" id="agent-tab-timeline" class="agent-tab-btn flex items-center space-x-2">
          <i class="fa-solid fa-timeline text-indigo-400"></i>
          <span>9-Stage Timeline</span>
        </button>
        <button onclick="switchAgentTab('approvals')" id="agent-tab-approvals" class="agent-tab-btn flex items-center space-x-2 relative">
          <i class="fa-solid fa-circle-check text-amber-400"></i>
          <span>Approval Queue</span>
          <span id="badge-pending-approvals" class="ml-1.5 px-1.5 py-0.2 rounded-full text-[9px] font-extrabold bg-amber-400 text-black hidden">0</span>
        </button>
        <button onclick="switchAgentTab('preferences')" id="agent-tab-preferences" class="agent-tab-btn flex items-center space-x-2">
          <i class="fa-solid fa-sliders text-cyan-400"></i>
          <span>Target Roles &amp; Resume</span>
        </button>
        <button onclick="switchAgentTab('portals')" id="agent-tab-portals" class="agent-tab-btn flex items-center space-x-2">
          <i class="fa-solid fa-globe text-emerald-400"></i>
          <span>Portal Permissions</span>
        </button>
        <button onclick="switchAgentTab('outreach')" id="agent-tab-outreach" class="agent-tab-btn flex items-center space-x-2">
          <i class="fa-solid fa-paper-plane text-purple-400"></i>
          <span>HR Outreach</span>
        </button>
        <button onclick="switchAgentTab('kb')" id="agent-tab-kb" class="agent-tab-btn flex items-center space-x-2">
          <i class="fa-solid fa-brain text-pink-400"></i>
          <span>Self-Learning &amp; Q&amp;A</span>
        </button>
      </div>

      <!-- TAB 1: OVERVIEW DASHBOARD -->
      <div id="agent-subview-dashboard" class="space-y-6">
        <!-- Top Metrics -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="p-4 rounded-2xl bg-[#0b101b] border border-[#1a2336] relative overflow-hidden">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">Live Jobs Monitored</span>
            <div class="flex items-baseline space-x-2">
              <span class="text-2xl sm:text-3xl font-extrabold text-white" id="stat-agent-total-jobs">1,001</span>
              <span class="text-xs text-cyan-400 font-semibold">19 Portals</span>
            </div>
            <i class="fa-solid fa-compass absolute right-3 bottom-3 text-2xl text-cyan-500/10"></i>
          </div>

          <div class="p-4 rounded-2xl bg-[#0b101b] border border-[#1a2336] relative overflow-hidden">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">LaTeX Resumes Synthesized</span>
            <div class="flex items-baseline space-x-2">
              <span class="text-2xl sm:text-3xl font-extrabold text-emerald-400" id="stat-agent-resumes">0</span>
              <span class="text-xs text-slate-400">Overleaf Ready</span>
            </div>
            <i class="fa-solid fa-file-code absolute right-3 bottom-3 text-2xl text-emerald-500/10"></i>
          </div>

          <div class="p-4 rounded-2xl bg-[#0b101b] border border-[#1a2336] relative overflow-hidden">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">Applications Submitted</span>
            <div class="flex items-baseline space-x-2">
              <span class="text-2xl sm:text-3xl font-extrabold text-white" id="stat-agent-applications">0</span>
              <span class="text-xs text-indigo-400 font-semibold">Tracked</span>
            </div>
            <i class="fa-solid fa-paper-plane absolute right-3 bottom-3 text-2xl text-indigo-500/10"></i>
          </div>

          <div class="p-4 rounded-2xl bg-[#0b101b] border border-[#1a2336] relative overflow-hidden">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">Recruiter Inbound Replies</span>
            <div class="flex items-baseline space-x-2">
              <span class="text-2xl sm:text-3xl font-extrabold text-amber-400" id="stat-agent-replies">0</span>
              <span class="text-xs text-emerald-400 font-semibold" id="stat-agent-response-rate">0% Rate</span>
            </div>
            <i class="fa-solid fa-envelope-open-text absolute right-3 bottom-3 text-2xl text-amber-500/10"></i>
          </div>
        </div>

        <!-- 3 Analytics Panels -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- Portal Distribution -->
          <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between pb-3 border-b border-[#1a2336] mb-4">
                <h3 class="text-sm font-bold text-white flex items-center space-x-2">
                  <i class="fa-solid fa-server text-cyan-400"></i>
                  <span>Jobs By Source Portal</span>
                </h3>
                <span class="text-[11px] text-slate-400">19 Sources</span>
              </div>
              <div id="agent-dashboard-portals-summary" class="space-y-2.5 max-h-72 overflow-y-auto pr-1 text-xs">
                <div class="text-slate-500 text-center py-4">Loading portal breakdown...</div>
              </div>
            </div>
            <div class="pt-3 border-t border-[#1a2336] mt-4 flex items-center justify-between text-xs">
              <span class="text-slate-400">Need to adjust portals?</span>
              <button onclick="switchAgentTab('portals')" class="text-cyan-400 hover:text-cyan-300 font-semibold">Manage Permissions &rarr;</button>
            </div>
          </div>

          <!-- Recruiter Sentiment Distribution -->
          <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between pb-3 border-b border-[#1a2336] mb-4">
                <h3 class="text-sm font-bold text-white flex items-center space-x-2">
                  <i class="fa-solid fa-chart-pie text-purple-400"></i>
                  <span>Recruiter Sentiment Distribution</span>
                </h3>
                <span class="text-[11px] text-slate-400">7 Classes</span>
              </div>
              <div id="agent-dashboard-sentiment-summary" class="space-y-2 text-xs">
                <div class="text-slate-500 text-center py-4">Loading sentiment analytics...</div>
              </div>
            </div>
            <div class="pt-3 border-t border-[#1a2336] mt-4 flex items-center justify-between text-xs">
              <span class="text-slate-400">View cold emails &amp; replies:</span>
              <button onclick="switchAgentTab('outreach')" class="text-purple-400 hover:text-purple-300 font-semibold">Outreach Log &rarr;</button>
            </div>
          </div>

          <!-- Self-Learning Weights & Dynamic Optimization -->
          <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between pb-3 border-b border-[#1a2336] mb-4">
                <h3 class="text-sm font-bold text-white flex items-center space-x-2">
                  <i class="fa-solid fa-brain text-pink-400"></i>
                  <span>Self-Learning Weight Vector</span>
                </h3>
                <span class="text-[10px] px-2 py-0.5 rounded bg-pink-950/80 text-pink-300 border border-pink-500/30 font-bold">Auto-Optimized</span>
              </div>
              <p class="text-[11px] text-slate-400 mb-3 leading-relaxed">
                Weights are dynamically adapted based on real interview and recruiter response outcomes without modifying candidate facts.
              </p>
              <div id="agent-dashboard-weights-summary" class="space-y-2.5 text-xs">
                <div class="text-slate-500 text-center py-4">Loading weights...</div>
              </div>
            </div>
            <div class="pt-3 border-t border-[#1a2336] mt-4 flex items-center justify-between text-xs">
              <span class="text-slate-400">Verified Candidate Facts:</span>
              <button onclick="switchAgentTab('kb')" class="text-pink-400 hover:text-pink-300 font-semibold">Knowledge Base &rarr;</button>
            </div>
          </div>

        </div>
      </div>

      <!-- TAB 2: 9-STAGE REAL-TIME TIMELINE -->
      <div id="agent-subview-timeline" class="space-y-6 hidden">
        <!-- 9-Stage Explainer Strip -->
        <div class="p-4 rounded-2xl bg-[#0b101b] border border-[#1a2336] overflow-x-auto scrollbar-none">
          <div class="flex items-center space-x-2 min-w-[760px] text-[11px] font-bold">
            <span class="stage-pill stage-job-found"><i class="fa-solid fa-compass"></i>1. Job Found</span>
            <span class="text-slate-600">&rarr;</span>
            <span class="stage-pill stage-job-analyzed"><i class="fa-solid fa-brain"></i>2. Analyzed</span>
            <span class="text-slate-600">&rarr;</span>
            <span class="stage-pill stage-resume-customized"><i class="fa-solid fa-file-code"></i>3. Resume Customized</span>
            <span class="text-slate-600">&rarr;</span>
            <span class="stage-pill stage-app-submitted"><i class="fa-solid fa-paper-plane"></i>4. App Submitted</span>
            <span class="text-slate-600">&rarr;</span>
            <span class="stage-pill stage-hr-found"><i class="fa-solid fa-id-badge"></i>5. HR Found</span>
            <span class="text-slate-600">&rarr;</span>
            <span class="stage-pill stage-email-sent"><i class="fa-solid fa-envelope-open-text"></i>6. Email Sent</span>
            <span class="text-slate-600">&rarr;</span>
            <span class="stage-pill stage-recruiter-replied"><i class="fa-solid fa-reply"></i>7. Replied</span>
            <span class="text-slate-600">&rarr;</span>
            <span class="stage-pill stage-response-analyzed"><i class="fa-solid fa-microscope"></i>8. Analyzed</span>
            <span class="text-slate-600">&rarr;</span>
            <span class="stage-pill stage-outcome-interview"><i class="fa-solid fa-trophy"></i>9. Outcome</span>
          </div>
        </div>

        <!-- Filter & Action Controls -->
        <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div class="flex items-center space-x-2 w-full sm:w-auto">
            <select id="timeline-stage-filter" onchange="filterTimelineEvents()" class="bg-[#0b101b] border border-[#223048] rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500">
              <option value="">All 9 Stages</option>
              <option value="JOB_FOUND">1. Job Found</option>
              <option value="JOB_ANALYZED">2. Job Analyzed</option>
              <option value="RESUME_CUSTOMIZED">3. Resume Customized (LaTeX)</option>
              <option value="APPLICATION_SUBMITTED">4. Application Submitted</option>
              <option value="HR_CONTACT_FOUND">5. HR Contact Found</option>
              <option value="COLD_EMAIL_SENT">6. Cold Email Sent</option>
              <option value="RECRUITER_RESPONSE_RECEIVED">7. Recruiter Response Received</option>
              <option value="RESPONSE_ANALYZED">8. Response Analyzed</option>
              <option value="OUTCOME_INTERVIEW">9. Outcome (Interview / Offer)</option>
            </select>
          </div>
          <button onclick="loadAgentTimeline()" class="btn-secondary text-xs py-1.5 px-3 flex items-center space-x-1.5">
            <i class="fa-solid fa-rotate text-cyan-400"></i>
            <span>Refresh Feed</span>
          </button>
        </div>

        <!-- Timeline Stream Container -->
        <div class="p-6 rounded-2xl bg-[#0b101b] border border-[#1a2336]">
          <div id="agent-timeline-stream" class="space-y-1">
            <div class="text-slate-500 text-center py-8 text-xs">Loading real-time timeline events...</div>
          </div>
        </div>
      </div>

      <!-- TAB 3: APPROVAL QUEUE -->
      <div id="agent-subview-approvals" class="space-y-6 hidden">
        <!-- Explainer -->
        <div class="p-4 rounded-2xl bg-amber-950/20 border border-amber-500/30 flex items-start space-x-3 text-xs">
          <i class="fa-solid fa-shield-halved text-amber-400 text-base mt-0.5"></i>
          <div class="text-slate-300 leading-relaxed">
            <strong class="text-white block mb-0.5">Candidate Verification Safeguard</strong>
            When Approval Mode is active, or when questions require explicit candidate confirmation, items will appear below. One click approves and proceeds.
          </div>
        </div>

        <!-- Pending Applications Section -->
        <div class="space-y-3">
          <h3 class="text-sm font-bold text-white flex items-center space-x-2">
            <i class="fa-solid fa-paper-plane text-cyan-400"></i>
            <span>Pending Application Approvals</span>
          </h3>
          <div id="approval-applications-list" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] text-center text-xs text-slate-500 col-span-full">
              No pending applications in queue.
            </div>
          </div>
        </div>

        <!-- Pending Outreach Emails Section -->
        <div class="space-y-3 pt-4 border-t border-[#1a2336]">
          <h3 class="text-sm font-bold text-white flex items-center space-x-2">
            <i class="fa-solid fa-envelope-open-text text-amber-400"></i>
            <span>Pending Recruiter Cold Emails</span>
          </h3>
          <div id="approval-emails-list" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] text-center text-xs text-slate-500 col-span-full">
              No pending recruiter outreach drafts.
            </div>
          </div>
        </div>

        <!-- Sensitive / Uncertain Questions Section -->
        <div class="space-y-3 pt-4 border-t border-[#1a2336]">
          <h3 class="text-sm font-bold text-white flex items-center space-x-2">
            <i class="fa-solid fa-circle-question text-pink-400"></i>
            <span>Sensitive Screener Questions Requiring Human Confirmation</span>
          </h3>
          <p class="text-xs text-slate-400">
            The engine detects sensitive topics (security clearance, non-competes, salary floors, background check specifics) and prevents hallucination by requesting your direct answer.
          </p>
          <div id="approval-questions-list" class="space-y-3">
            <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] text-center text-xs text-slate-500">
              All questions resolved. No pending sensitive inquiries.
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 4: PREFERENCES & MASTER RESUME -->
      <div id="agent-subview-preferences" class="space-y-6 hidden">
        <form id="agent-preferences-form" onsubmit="handleSavePreferences(event)" class="p-6 rounded-2xl bg-[#0b101b] border border-[#1a2336] space-y-5">
          
          <div class="pb-4 border-b border-[#1a2336]">
            <h3 class="text-base font-bold text-white mb-1">Candidate Job Search Preferences</h3>
            <p class="text-xs text-slate-400">Configure target titles, locations, compensation floor, daily quotas, and your master resume.</p>
          </div>

          <!-- Target Titles (Up to 3) -->
          <div>
            <label class="text-xs font-semibold text-slate-300 block mb-1">
              Target Job Titles <span class="text-slate-400 font-normal">(Up to 3 titles, comma separated)</span>
            </label>
            <input type="text" id="pref-target-titles" required placeholder="e.g. Full Stack Engineer, Backend Developer, Python Developer" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500" />
          </div>

          <!-- Preferred Locations -->
          <div>
            <label class="text-xs font-semibold text-slate-300 block mb-1">
              Preferred Locations <span class="text-slate-400 font-normal">(e.g. Remote, Bengaluru, Hyderabad, Pune, Mumbai, Delhi NCR)</span>
            </label>
            <input type="text" id="pref-locations" required placeholder="Remote, Bengaluru, Hyderabad" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500" />
          </div>

          <!-- Grid: Work Preference & Experience Level -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="text-xs font-semibold text-slate-300 block mb-1">Work Preference</label>
              <select id="pref-work-pref" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
                <option value="REMOTE">Remote Only</option>
                <option value="HYBRID">Hybrid</option>
                <option value="ONSITE">On-site</option>
                <option value="ANY" selected>Any Work Mode</option>
              </select>
            </div>

            <div>
              <label class="text-xs font-semibold text-slate-300 block mb-1">Experience Level Alignment</label>
              <select id="pref-exp-level" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
                <option value="ENTRY">Fresher / Entry (0-2 Yrs)</option>
                <option value="MID" selected>Mid-Level (3-5 Yrs)</option>
                <option value="SENIOR">Senior (5+ Yrs)</option>
                <option value="LEAD">Lead / Principal (8+ Yrs)</option>
              </select>
            </div>
          </div>

          <!-- Grid: Salary Expectation -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div class="sm:col-span-2">
              <label class="text-xs font-semibold text-slate-300 block mb-1">Minimum Salary Expectation (Per Annum)</label>
              <input type="number" id="pref-min-salary" placeholder="e.g. 1500000 or 90000" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500" />
            </div>
            <div>
              <label class="text-xs font-semibold text-slate-300 block mb-1">Currency</label>
              <select id="pref-salary-curr" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
                <option value="INR" selected>INR (₹)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>

          <!-- Grid: Application Safety Limits -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="text-xs font-semibold text-slate-300 block mb-1">Max Daily Applications Limit</label>
              <input type="number" id="pref-max-daily" min="1" max="100" value="25" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500" />
            </div>
            <div>
              <label class="text-xs font-semibold text-slate-300 block mb-1">Max Applications Per Portal</label>
              <input type="number" id="pref-max-portal" min="1" max="50" value="10" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-500" />
            </div>
          </div>

          <!-- Master Resume Text Area -->
          <div class="pt-2">
            <div class="flex items-center justify-between mb-1.5">
              <label class="text-xs font-semibold text-slate-300">
                Master Resume Markdown / Plain Text
              </label>
              <label class="cursor-pointer text-xs text-cyan-400 hover:text-cyan-300 flex items-center space-x-1">
                <i class="fa-solid fa-cloud-arrow-up"></i>
                <span>Extract from File</span>
                <input type="file" id="pref-resume-upload" accept=".txt,.md,.pdf,.docx" class="hidden" onchange="handleResumeFileUpload(event)" />
              </label>
            </div>
            <textarea id="pref-master-resume-text" rows="8" required placeholder="Paste your complete Master Resume here with work history, projects, tech stack, and education..." class="w-full bg-[#06080d] border border-[#223048] rounded-xl p-3 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500 leading-relaxed"></textarea>
            <p class="text-[11px] text-slate-400 mt-1">This Master Resume is used by the LaTeX engine to generate compile-ready, tailored resumes matching the exact JD without hallucinating credentials.</p>
          </div>

          <div class="pt-3 flex justify-end">
            <button type="submit" id="btn-save-preferences" class="btn-primary py-2.5 px-6 text-xs font-bold rounded-xl flex items-center space-x-2">
              <i class="fa-solid fa-floppy-disk"></i>
              <span>Save Agent Configuration</span>
            </button>
          </div>

        </form>
      </div>

      <!-- TAB 5: PORTAL PERMISSIONS -->
      <div id="agent-subview-portals" class="space-y-6 hidden">
        <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] space-y-4">
          <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-[#1a2336]">
            <div>
              <h3 class="text-base font-bold text-white">Candidate Portal Permissions (19+ Sources)</h3>
              <p class="text-xs text-slate-400">Toggle permission for each job portal and set specific daily submission limits.</p>
            </div>
            <input type="text" id="portal-filter-search" oninput="filterPortalsList()" placeholder="Search portal..." class="bg-[#06080d] border border-[#223048] rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 w-full sm:w-56" />
          </div>

          <!-- Portals Table -->
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead>
                <tr class="border-b border-[#1a2336] text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th class="py-3 px-3">Platform Name</th>
                  <th class="py-3 px-3">Source Category</th>
                  <th class="py-3 px-3">Status</th>
                  <th class="py-3 px-3">Daily Limit</th>
                  <th class="py-3 px-3">Live Jobs</th>
                  <th class="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody id="portal-permissions-body" class="divide-y divide-[#1a2336]">
                <tr><td colspan="6" class="py-6 text-center text-slate-500">Loading portal registry...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 6: RECRUITER OUTREACH -->
      <div id="agent-subview-outreach" class="space-y-6 hidden">
        
        <!-- Header Actions -->
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 class="text-base font-bold text-white">Automated Recruiter Outreach &amp; Inbound Replies</h3>
            <p class="text-xs text-slate-400">Public talent partner discovery, personalized cold emails, and multi-stage follow-up cadences.</p>
          </div>
          <div class="flex items-center space-x-2">
            <button onclick="openRecruiterReplyModal()" class="btn-secondary text-xs py-2 px-3.5 flex items-center space-x-1.5 text-purple-400 border-purple-500/30 hover:bg-purple-950/30">
              <i class="fa-solid fa-microscope"></i>
              <span>Simulate Recruiter Reply</span>
            </button>
            <button onclick="triggerFollowups()" id="btn-trigger-followups" class="btn-primary text-xs py-2 px-4 flex items-center space-x-1.5">
              <i class="fa-solid fa-clock-rotate-left"></i>
              <span>Trigger Follow-up Cadence</span>
            </button>
          </div>
        </div>

        <!-- Discovered Contacts Section -->
        <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-[#1a2336]">
            <h4 class="text-xs font-bold uppercase tracking-wider text-purple-400 flex items-center space-x-2">
              <i class="fa-solid fa-id-badge"></i>
              <span>Discovered HR &amp; Talent Contacts</span>
            </h4>
            <span id="recruiter-contacts-count" class="text-xs text-slate-400">0 Contacts Found</span>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead>
                <tr class="border-b border-[#1a2336] text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th class="py-2.5 px-3">Name &amp; Role</th>
                  <th class="py-2.5 px-3">Company</th>
                  <th class="py-2.5 px-3">Email Address</th>
                  <th class="py-2.5 px-3">Confidence</th>
                  <th class="py-2.5 px-3 text-right">Discovered</th>
                </tr>
              </thead>
              <tbody id="outreach-contacts-body" class="divide-y divide-[#1a2336]">
                <tr><td colspan="5" class="py-4 text-center text-slate-500">Loading contacts...</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Cold Email Logs Section -->
        <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-[#1a2336]">
            <h4 class="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center space-x-2">
              <i class="fa-solid fa-envelope-open-text"></i>
              <span>Cold Outreach Email History</span>
            </h4>
            <span id="outreach-emails-count" class="text-xs text-slate-400">0 Emails Transmitted</span>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead>
                <tr class="border-b border-[#1a2336] text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th class="py-2.5 px-3">Recruiter &amp; Company</th>
                  <th class="py-2.5 px-3">Subject Line</th>
                  <th class="py-2.5 px-3">Status</th>
                  <th class="py-2.5 px-3">Follow-ups</th>
                  <th class="py-2.5 px-3">Response Sentiment</th>
                  <th class="py-2.5 px-3 text-right">Sent</th>
                </tr>
              </thead>
              <tbody id="outreach-emails-body" class="divide-y divide-[#1a2336]">
                <tr><td colspan="6" class="py-4 text-center text-slate-500">Loading email logs...</td></tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>

      <!-- TAB 7: SELF LEARNING & KNOWLEDGE BASE -->
      <div id="agent-subview-kb" class="space-y-6 hidden">
        
        <!-- Explainer -->
        <div class="p-4 rounded-2xl bg-pink-950/20 border border-pink-500/30 flex items-start space-x-3 text-xs">
          <i class="fa-solid fa-brain text-pink-400 text-base mt-0.5"></i>
          <div class="text-slate-300 leading-relaxed">
            <strong class="text-white block mb-0.5">Continuous Improvement Without Hallucination</strong>
            The self-learning engine analyzes which resume keywords, subject lines, and skills generate interviews and positive replies. It continuously fine-tunes weighting algorithms while keeping your verified personal facts 100% authentic.
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          <!-- Candidate Verified Facts List -->
          <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] space-y-4">
            <div class="flex items-center justify-between pb-3 border-b border-[#1a2336]">
              <h4 class="text-sm font-bold text-white flex items-center space-x-2">
                <i class="fa-solid fa-circle-check text-emerald-400"></i>
                <span>Verified Candidate Knowledge Base</span>
              </h4>
              <span id="kb-facts-count" class="text-xs text-slate-400">5 Facts</span>
            </div>

            <div id="kb-facts-list" class="space-y-3 max-h-80 overflow-y-auto pr-1 text-xs">
              <div class="text-slate-500 text-center py-6">Loading knowledge base facts...</div>
            </div>

            <!-- Add Verified Fact Form -->
            <form id="kb-add-form" onsubmit="handleAddKbFact(event)" class="pt-3 border-t border-[#1a2336] space-y-2">
              <span class="text-xs font-semibold text-slate-300 block">Add New Verified Fact</span>
              <input type="text" id="kb-add-question" required placeholder="e.g. Notice Period or Willingness to Relocate" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3 py-1.5 text-xs text-white" />
              <input type="text" id="kb-add-answer" required placeholder="e.g. Immediate / 15 days or Yes, willing to relocate" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3 py-1.5 text-xs text-white" />
              <div class="flex items-center justify-between pt-1">
                <select id="kb-add-category" class="bg-[#06080d] border border-[#223048] rounded-xl px-2.5 py-1 text-xs text-slate-300">
                  <option value="career">Career</option>
                  <option value="compensation">Compensation</option>
                  <option value="legal">Legal / Auth</option>
                  <option value="relocation">Relocation</option>
                  <option value="education">Education</option>
                </select>
                <button type="submit" class="btn-primary py-1.5 px-3 text-xs font-semibold rounded-xl">Save Fact</button>
              </div>
            </form>
          </div>

          <!-- Self-Learning Metric Correlations & Winning Features -->
          <div class="p-5 rounded-2xl bg-[#0b101b] border border-[#1a2336] space-y-4">
            <div class="flex items-center justify-between pb-3 border-b border-[#1a2336]">
              <h4 class="text-sm font-bold text-white flex items-center space-x-2">
                <i class="fa-solid fa-chart-line text-cyan-400"></i>
                <span>Learned Metrics &amp; Success Factors</span>
              </h4>
              <span class="text-xs text-slate-400">Optimized</span>
            </div>

            <div id="kb-learning-metrics-list" class="space-y-3 text-xs">
              <div class="text-slate-500 text-center py-6">Loading learning feedback metrics...</div>
            </div>
          </div>

        </div>

      </div>

    </section>
"""

modals_html = """
  <!-- ===================================================================== -->
  <!-- 8.6 ATS-COMPLIANT LATEX & OVERLEAF RESUME MODAL                       -->
  <!-- ===================================================================== -->
  <div id="latex-resume-modal" class="modal-backdrop hidden" style="z-index: 65;">
    <div class="modal-content max-w-3xl p-6 relative max-h-[90vh] flex flex-col">
      <button onclick="closeLatexResumeModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white p-1 text-base">
        <i class="fa-solid fa-xmark"></i>
      </button>

      <!-- Modal Header -->
      <div class="pb-3 border-b border-[#1a2336] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pr-8">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
            <i class="fa-solid fa-file-code"></i>
          </div>
          <div>
            <h3 class="text-base font-extrabold text-white flex items-center space-x-2">
              <span>ATS-Compliant LaTeX Resume</span>
              <span id="latex-modal-badge" class="px-2 py-0.5 rounded-full text-[10px] bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-bold">Compile-Ready</span>
            </h3>
            <p class="text-xs text-slate-400" id="latex-modal-subtitle">Synthesized dynamically matching Job Description</p>
          </div>
        </div>

        <div class="flex items-center space-x-2 w-full sm:w-auto justify-end">
          <a id="btn-overleaf-open" href="https://www.overleaf.com/docs" target="_blank" rel="noopener noreferrer" class="btn-primary py-1.5 px-3 text-xs font-bold rounded-lg flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500">
            <i class="fa-solid fa-leaf"></i>
            <span>Open in Overleaf</span>
          </a>
          <button onclick="downloadLatexFile()" class="btn-secondary py-1.5 px-3 text-xs font-semibold rounded-lg flex items-center space-x-1" title="Download .tex file">
            <i class="fa-solid fa-download"></i>
            <span>.tex</span>
          </button>
          <button onclick="copyLatexCode()" class="btn-secondary py-1.5 px-3 text-xs font-semibold rounded-lg flex items-center space-x-1" title="Copy LaTeX code">
            <i class="fa-solid fa-copy"></i>
            <span>Copy</span>
          </button>
        </div>
      </div>

      <!-- LaTeX Code Display -->
      <div class="pt-4 flex-1 overflow-hidden flex flex-col">
        <div class="flex items-center justify-between text-[11px] text-slate-400 mb-2 px-1">
          <span>Target Job: <strong id="latex-modal-job-title" class="text-cyan-300">Senior Engineer</strong> &bull; <span id="latex-modal-company">Company</span></span>
          <span class="text-[10px] text-slate-500">Engine: pdfLaTeX / XeLaTeX</span>
        </div>
        <div class="latex-code-box flex-1 overflow-y-auto" id="latex-code-viewer">% Loading ATS LaTeX Resume...</div>
      </div>
    </div>
  </div>

  <!-- ===================================================================== -->
  <!-- 8.7 RECRUITER INBOUND REPLY SIMULATOR MODAL                           -->
  <!-- ===================================================================== -->
  <div id="recruiter-reply-modal" class="modal-backdrop hidden" style="z-index: 65;">
    <div class="modal-content max-w-lg p-6 relative">
      <button onclick="closeRecruiterReplyModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white p-1 text-base">
        <i class="fa-solid fa-xmark"></i>
      </button>

      <div class="pb-3 border-b border-[#1a2336] mb-4">
        <div class="flex items-center space-x-2 text-purple-400 mb-1">
          <i class="fa-solid fa-envelope-open-text"></i>
          <h3 class="text-base font-bold text-white">Simulate Recruiter Inbound Reply</h3>
        </div>
        <p class="text-xs text-slate-400">Test how the NLP agent analyzes responses into the 7 sentiment categories.</p>
      </div>

      <div class="space-y-3 text-xs">
        <div>
          <label class="block text-slate-300 font-semibold mb-1">Select Outreach Recipient</label>
          <select id="sim-reply-email-id" class="w-full bg-[#06080d] border border-[#223048] rounded-xl px-3 py-2 text-xs text-white">
            <option value="">Select an outreach email...</option>
          </select>
        </div>

        <div>
          <label class="block text-slate-300 font-semibold mb-1">Quick Sample Responses</label>
          <div class="flex flex-wrap gap-1.5">
            <button type="button" onclick="setSimReplyText('interview')" class="px-2 py-1 rounded bg-[#1e293b] hover:bg-slate-700 text-slate-300 text-[11px]">🎉 Interview Invitation</button>
            <button type="button" onclick="setSimReplyText('positive')" class="px-2 py-1 rounded bg-[#1e293b] hover:bg-slate-700 text-slate-300 text-[11px]">👍 Positive / Forwarded</button>
            <button type="button" onclick="setSimReplyText('action')" class="px-2 py-1 rounded bg-[#1e293b] hover:bg-slate-700 text-slate-300 text-[11px]">📋 Availability / Notice</button>
            <button type="button" onclick="setSimReplyText('rejection')" class="px-2 py-1 rounded bg-[#1e293b] hover:bg-slate-700 text-slate-300 text-[11px]">❌ Polite Rejection</button>
          </div>
        </div>

        <div>
          <label class="block text-slate-300 font-semibold mb-1">Recruiter Response Text</label>
          <textarea id="sim-reply-body" rows="4" class="w-full bg-[#06080d] border border-[#223048] rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-cyan-500" placeholder="Paste recruiter reply email here..."></textarea>
        </div>

        <button type="button" onclick="submitSimulateReply()" id="btn-submit-sim-reply" class="w-full btn-primary py-2 text-xs font-bold rounded-xl mt-2">
          <i class="fa-solid fa-microscope mr-1.5"></i>Analyze &amp; Process Response
        </button>

        <!-- Simulation Result Box -->
        <div id="sim-reply-result" class="hidden p-3 rounded-xl bg-[#06080d] border border-[#1a2336] space-y-1">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-slate-400">Classified Category:</span>
            <span id="sim-result-category" class="stage-pill stage-job-found">INTERVIEW</span>
          </div>
          <p id="sim-result-notes" class="text-[11px] text-slate-300"></p>
        </div>
      </div>
    </div>
  </div>
"""

target_path = 'src/frontend/index.html'
with open(target_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Insert section before </main>
main_marker = '</main>'
idx = text.find(main_marker)
if idx == -1:
    raise ValueError("Could not find </main> in index.html")
text = text[:idx] + agent_html + '\n  ' + text[idx:]

# 2. Insert modals before toast container
toast_marker = '<!-- Toast Notification Container -->'
idx_toast = text.find(toast_marker)
if idx_toast == -1:
    raise ValueError("Could not find <!-- Toast Notification Container -->")
text = text[:idx_toast] + modals_html + '\n  ' + text[idx_toast:]

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(text)

print(f"Success! index.html updated. New total length: {len(text)}")
