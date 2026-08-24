/* ==========================================================================
   ANTIGRAVITY NETWORK SENTINEL - FRONTEND CONTROLLER (v2.0)
   ========================================================================== */

let ws = null;
let downChart = null;
let upChart = null;

let allProcesses = [];
let activeLimits = {};
let maxDownSpeedSeen = 100 * 1024;
let maxUpSpeedSeen = 100 * 1024;
let currentCategoryFilter = 'all';

let chartHistoryLength = 30;
let downChartData = Array(chartHistoryLength).fill(0);
let upChartData = Array(chartHistoryLength).fill(0);
let chartLabels = Array(chartHistoryLength).fill('');

// Modal States
let currentModalTarget = '';
let currentModalExe = '';

const BROWSER_EXE_NAMES = [
  'chrome.exe', 'firefox.exe', 'msedge.exe', 'brave.exe', 'opera.exe', 'vivaldi.exe', 'whale.exe', 'safari.exe'
];

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    lucide.createIcons();
  }

  initCharts();
  connectWebSocket();
  fetchSystemInfo();
});

/* Tab Switching */
function switchTab(tabId) {
  document.querySelectorAll('.nav-tab').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-view').forEach(view => view.classList.remove('active'));

  if (tabId === 'live') {
    document.getElementById('tabLiveBtn').classList.add('active');
    document.getElementById('viewLive').classList.add('active');
  } else if (tabId === 'analytics') {
    document.getElementById('tabAnalyticsBtn').classList.add('active');
    document.getElementById('viewAnalytics').classList.add('active');
    loadAnalyticsData();
  } else if (tabId === 'policies') {
    document.getElementById('tabPoliciesBtn').classList.add('active');
    document.getElementById('viewPolicies').classList.add('active');
    renderFullPoliciesView();
  }

  if (window.lucide) lucide.createIcons();
}

function fetchSystemInfo() {
  fetch('/api/system-info')
    .then(res => res.json())
    .then(data => {
      updateAdminBadge(data.is_admin);
      updateAutostartBadge(data.autostart);
    })
    .catch(err => console.error("System info error:", err));
}

function updateAdminBadge(isAdmin) {
  const badge = document.getElementById('adminStatus');
  if (isAdmin) {
    badge.className = 'status-badge admin-ok';
    badge.innerHTML = `<i data-lucide="shield-check"></i><span>ADMIN PRIVILEGES ACTIVE</span>`;
  } else {
    badge.className = 'status-badge admin-warn';
    badge.innerHTML = `<i data-lucide="shield-alert"></i><span>USER MODE (Admin Required for QoS)</span>`;
  }
  if (window.lucide) lucide.createIcons();
}

function updateAutostartBadge(isAutostart) {
  const badge = document.getElementById('autostartStatus');
  const text = document.getElementById('autostartText');
  if (isAutostart) {
    badge.className = 'status-badge admin-ok';
    text.innerText = 'Auto-Start: ON (Boot Enabled)';
    badge.innerHTML = `<i data-lucide="power"></i><span>Auto-Start: ON</span>`;
  } else {
    badge.className = 'status-badge';
    text.innerText = 'Auto-Start: OFF';
    badge.innerHTML = `<i data-lucide="power-off"></i><span>Auto-Start: OFF</span>`;
  }
  if (window.lucide) lucide.createIcons();
}

function toggleAutostartUI() {
  const badge = document.getElementById('autostartStatus');
  const isCurrentlyOn = badge.classList.contains('admin-ok');
  const nextState = !isCurrentlyOn;

  fetch('/api/autostart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enable: nextState })
  })
  .then(res => res.json())
  .then(data => {
    updateAutostartBadge(data.autostart);
  })
  .catch(err => console.error("Toggle autostart error:", err));
}

/* WebSocket Telemetry Connection */
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/stats`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    document.getElementById('connectionStatus').innerHTML = `<span class="pulse-dot"></span><span>SENTINEL ONLINE</span>`;
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleTelemetryData(data);
  };

  ws.onclose = () => {
    document.getElementById('connectionStatus').innerHTML = `<span class="pulse-dot" style="background: #FF0054; box-shadow: none;"></span><span>RECONNECTING...</span>`;
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
}

function handleTelemetryData(data) {
  const g = data.global;
  activeLimits = data.active_limits || {};
  allProcesses = data.processes || [];

  // Update System Total Stats
  document.getElementById('totalDownFormatted').innerText = g.download_formatted;
  document.getElementById('totalDownRaw').innerText = `Total Recv: ${(g.total_recv / (1024 * 1024)).toFixed(1)} MB`;

  document.getElementById('totalUpFormatted').innerText = g.upload_formatted;
  document.getElementById('totalUpRaw').innerText = `Total Sent: ${(g.total_sent / (1024 * 1024)).toFixed(1)} MB`;

  // Update Global Limit Status Badge
  const gLimit = activeLimits['global'];
  const gBadge = document.getElementById('globalLimitBadge');
  if (gLimit) {
    gBadge.innerText = `LIMIT: ${formatKbps(gLimit.kbps)}`;
    gBadge.className = 'trend-tag tag-amber';
  } else {
    gBadge.innerText = 'UNLIMITED';
    gBadge.className = 'trend-tag tag-cyan';
  }

  // Update active policies count
  const ruleCount = Object.keys(activeLimits).length;
  document.getElementById('tabRulesCount').innerText = ruleCount;

  // Update Charts
  updateCharts(g.download_speed / 1024, g.upload_speed / 1024);

  // Render Table
  renderProcesses();
}

/* Charts Initialization & Updates */
function initCharts() {
  const ctxDown = document.getElementById('downChart').getContext('2d');
  const ctxUp = document.getElementById('upChart').getContext('2d');

  const gradientDown = ctxDown.createLinearGradient(0, 0, 0, 75);
  gradientDown.addColorStop(0, 'rgba(0, 242, 254, 0.4)');
  gradientDown.addColorStop(1, 'rgba(0, 242, 254, 0.0)');

  const gradientUp = ctxUp.createLinearGradient(0, 0, 0, 75);
  gradientUp.addColorStop(0, 'rgba(157, 78, 221, 0.4)');
  gradientUp.addColorStop(1, 'rgba(157, 78, 221, 0.0)');

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    scales: {
      x: { display: false },
      y: { display: false, min: 0 }
    },
    elements: {
      line: { tension: 0.4, borderWidth: 2 },
      point: { radius: 0 }
    }
  };

  downChart = new Chart(ctxDown, {
    type: 'line',
    data: {
      labels: chartLabels,
      datasets: [{
        data: downChartData,
        borderColor: '#00F2FE',
        backgroundColor: gradientDown,
        fill: true
      }]
    },
    options: chartOptions
  });

  upChart = new Chart(ctxUp, {
    type: 'line',
    data: {
      labels: chartLabels,
      datasets: [{
        data: upChartData,
        borderColor: '#9D4EDD',
        backgroundColor: gradientUp,
        fill: true
      }]
    },
    options: chartOptions
  });
}

function updateCharts(downKb, upKb) {
  downChartData.push(downKb);
  downChartData.shift();

  upChartData.push(upKb);
  upChartData.shift();

  downChart.update('none');
  upChart.update('none');
}

function formatKbps(kbps) {
  if (!kbps || kbps <= 0) return "UNLIMITED";
  if (kbps < 1024) return `${kbps} KB/s`;
  if (kbps < 1024 * 1024) return `${(kbps / 1024).toFixed(1)} MB/s`;
  return `${(kbps / (1024 * 1024)).toFixed(2)} GB/s`;
}

/* Category Filters */
function setCategoryFilter(category) {
  currentCategoryFilter = category;
  document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.filter === category);
  });
  renderProcesses();
}

function filterProcesses() {
  renderProcesses();
}

function renderProcesses() {
  const searchVal = document.getElementById('searchInput').value.toLowerCase().trim();
  const sortBy = document.getElementById('sortSelect').value;

  let filtered = allProcesses.filter(p => {
    // 1. Text search
    if (searchVal) {
      const match = p.name.toLowerCase().includes(searchVal) || 
                    String(p.pid).includes(searchVal) || 
                    (p.exe && p.exe.toLowerCase().includes(searchVal));
      if (!match) return false;
    }

    // 2. Category filter
    if (currentCategoryFilter === 'browser') {
      return BROWSER_EXE_NAMES.includes(p.name.toLowerCase());
    } else if (currentCategoryFilter === 'high') {
      return (p.down_speed + p.up_speed) > (50 * 1024); // > 50 KB/s
    } else if (currentCategoryFilter === 'limited') {
      return p.limit_kbps !== null && p.limit_kbps !== undefined;
    }

    return true;
  });

  // Sort
  filtered.sort((a, b) => {
    if (sortBy === 'down') return b.down_speed - a.down_speed;
    if (sortBy === 'up') return b.up_speed - a.up_speed;
    if (sortBy === 'connections') return b.connections - a.connections;
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    if (sortBy === 'pid') return a.pid - b.pid;
    // Default 'traffic'
    return (b.down_speed + b.up_speed) - (a.down_speed + a.up_speed);
  });

  document.getElementById('procCountBadge').innerText = `${filtered.length} Active`;

  const tbody = document.getElementById('processTableBody');
  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr class="empty-row">
        <td colspan="8">
          <p>No matching active processes found.</p>
        </td>
      </tr>
    `;
    return;
  }

  filtered.forEach(p => {
    if (p.down_speed > maxDownSpeedSeen) maxDownSpeedSeen = p.down_speed;
    if (p.up_speed > maxUpSpeedSeen) maxUpSpeedSeen = p.up_speed;
  });

  tbody.innerHTML = filtered.map(p => {
    const downPct = Math.min(100, Math.max(3, (p.down_speed / maxDownSpeedSeen) * 100));
    const upPct = Math.min(100, Math.max(3, (p.up_speed / maxUpSpeedSeen) * 100));

    const isLimited = p.limit_kbps !== null && p.limit_kbps !== undefined;
    const priorityTag = p.priority && p.priority !== 'normal' ? ` [${p.priority.toUpperCase()}]` : '';
    const limitBadge = isLimited 
      ? `<span class="limit-badge-col limit-active"><i data-lucide="shield"></i> ${formatKbps(p.limit_kbps)}${priorityTag}</span>`
      : `<span class="limit-badge-col limit-none">No Limit</span>`;

    return `
      <tr>
        <td>
          <div class="proc-info">
            <span class="proc-name">${escapeHtml(p.name)}</span>
            <span class="proc-path" title="${escapeHtml(p.exe)}">${escapeHtml(p.exe || 'N/A')}</span>
          </div>
        </td>
        <td><span class="pid-tag">${p.pid}</span></td>
        <td>
          <button class="socket-link-btn" onclick="openConnectionsModal(${p.pid}, '${escapeHtml(p.name)}')">
            <i data-lucide="network"></i> ${p.connections} sockets
          </button>
        </td>
        <td>
          <div class="speed-cell">
            <span class="speed-text down">${p.down_formatted}</span>
            <div class="speed-bar-bg">
              <div class="speed-bar-fill fill-down" style="width: ${downPct}%;"></div>
            </div>
          </div>
        </td>
        <td>
          <div class="speed-cell">
            <span class="speed-text up">${p.up_formatted}</span>
            <div class="speed-bar-bg">
              <div class="speed-bar-fill fill-up" style="width: ${upPct}%;"></div>
            </div>
          </div>
        </td>
        <td><span class="pid-tag">${p.cpu_percent.toFixed(1)}% / ${p.memory_mb} MB</span></td>
        <td>${limitBadge}</td>
        <td class="text-right">
          <button class="btn-sm-limit" onclick="openLimitModal('${escapeHtml(p.name)}', '${escapeHtml(p.name)} (${p.pid})', '${escapeHtml(p.exe)}', ${p.limit_kbps || 0}, '${p.priority || 'normal'}')">
            <i data-lucide="sliders"></i> Throttle
          </button>
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

/* Modal Speed Limiter Dialog Controls */
function openLimitModal(targetName, displayTitle, appExe = '', currentKbps = 0, priority = 'normal') {
  currentModalTarget = targetName;
  currentModalExe = appExe || targetName;

  document.getElementById('modalTargetTitle').innerText = `Limit Speed: ${displayTitle}`;
  document.getElementById('modalTargetSub').innerText = targetName === 'global' ? 'System-wide network throttling' : `Executable: ${currentModalExe}`;
  document.getElementById('targetExeInput').value = currentModalExe;
  document.getElementById('prioritySelect').value = priority || 'normal';

  const initVal = currentKbps > 0 ? currentKbps : 1024;
  updateModalValueDisplays(initVal);

  document.getElementById('limitModal').classList.add('show');
}

function closeLimitModal() {
  document.getElementById('limitModal').classList.remove('show');
}

function selectModalPreset(kbps) {
  updateModalValueDisplays(kbps);
}

function onSliderChange(val) {
  updateModalValueDisplays(parseInt(val, 10));
}

function onNumberInputChange(val) {
  const num = parseInt(val, 10) || 0;
  updateModalValueDisplays(num);
}

function updateModalValueDisplays(kbps) {
  document.getElementById('limitSlider').value = Math.min(104857600, kbps);
  document.getElementById('customLimitInput').value = kbps;

  const display = document.getElementById('modalValDisplay');
  if (kbps <= 0) {
    display.innerText = "UNLIMITED (Remove QoS Policy)";
  } else {
    display.innerText = `${formatKbps(kbps)} (${kbps.toLocaleString()} KB/s)`;
  }
}

function submitLimitModal() {
  const kbps = parseInt(document.getElementById('customLimitInput').value, 10) || 0;
  const priority = document.getElementById('prioritySelect').value;
  setLimit(currentModalTarget, currentModalExe, kbps, priority);
  closeLimitModal();
}

function setGlobalPreset(kbps) {
  setLimit('global', '*', kbps);
}

function removeGlobalLimit() {
  removeLimit('global');
}

/* Socket Inspector Modal */
function openConnectionsModal(pid, name) {
  document.getElementById('connModalTitle').innerText = `Sockets: ${name} (PID: ${pid})`;
  document.getElementById('connModalSub').innerText = `Querying active TCP/UDP endpoints for PID ${pid}...`;
  document.getElementById('connTableBody').innerHTML = `<tr class="empty-row"><td colspan="4"><div class="loading-spinner"></div><p>Fetching socket table...</p></td></tr>`;
  document.getElementById('connectionsModal').classList.add('show');

  fetch(`/api/process/${pid}/connections`)
    .then(res => {
      if (!res.ok) throw new Error("Process ended or access denied");
      return res.json();
    })
    .then(data => {
      document.getElementById('connModalSub').innerText = `Found ${data.count} active network sockets`;
      const tbody = document.getElementById('connTableBody');
      if (data.connections.length === 0) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="4">No active network endpoints established.</td></tr>`;
        return;
      }

      tbody.innerHTML = data.connections.map(c => `
        <tr>
          <td><span class="pid-tag ${c.type === 'TCP' ? 'tag-cyan' : 'tag-violet'}">${c.type}</span></td>
          <td class="mono-text">${escapeHtml(c.local_address)}</td>
          <td class="mono-text endpoint-addr">${escapeHtml(c.remote_address)}</td>
          <td><span class="status-badge-sm status-${(c.status || 'established').toLowerCase()}">${c.status || 'ESTABLISHED'}</span></td>
        </tr>
      `).join('');
    })
    .catch(err => {
      document.getElementById('connTableBody').innerHTML = `<tr class="empty-row"><td colspan="4" style="color: #FF0054;">${err.message}</td></tr>`;
    });
}

function closeConnectionsModal() {
  document.getElementById('connectionsModal').classList.remove('show');
}

/* Analytics Data Loader */
function loadAnalyticsData() {
  const topList = document.getElementById('topConsumersList');
  topList.innerHTML = `<div class="loading-spinner"></div>`;

  // Fetch Top 24h
  fetch('/api/history/top?hours=24&limit=8')
    .then(res => res.json())
    .then(items => {
      if (items.length === 0) {
        topList.innerHTML = `<p class="empty-text">No traffic history collected yet. Activity is recorded over time.</p>`;
        return;
      }
      topList.innerHTML = items.map((item, idx) => `
        <div class="top-item">
          <div class="top-rank">#${idx + 1}</div>
          <div class="top-details">
            <div class="top-name">${escapeHtml(item.name)}</div>
            <div class="top-exe">${escapeHtml(item.exe || 'N/A')}</div>
          </div>
          <div class="top-usage">
            <div class="top-total">${item.total_traffic_formatted}</div>
            <div class="top-breakdown">↓ ${item.total_down_formatted} / ↑ ${item.total_up_formatted}</div>
          </div>
        </div>
      `).join('');
    })
    .catch(err => {
      topList.innerHTML = `<p class="empty-text error-text">Failed to load analytics: ${err}</p>`;
    });

  // Fetch Daily Breakdown
  fetch('/api/history/daily?days=7')
    .then(res => res.json())
    .then(rows => {
      const tbody = document.getElementById('dailyHistoryBody');
      if (rows.length === 0) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="5">No daily traffic logs recorded yet.</td></tr>`;
        return;
      }
      tbody.innerHTML = rows.map(r => `
        <tr>
          <td><span class="pid-tag">${r.date}</span></td>
          <td>
            <div class="proc-info">
              <span class="proc-name">${escapeHtml(r.name)}</span>
              <span class="proc-path">${escapeHtml(r.exe || '')}</span>
            </div>
          </td>
          <td class="speed-text up">${r.up_formatted}</td>
          <td class="speed-text down">${r.down_formatted}</td>
          <td><strong>${r.total_formatted}</strong></td>
        </tr>
      `).join('');
    })
    .catch(err => {
      document.getElementById('dailyHistoryBody').innerHTML = `<tr class="empty-row"><td colspan="5">Error: ${err}</td></tr>`;
    });
}

/* Policies View */
function renderFullPoliciesView() {
  const grid = document.getElementById('fullPoliciesGrid');
  const keys = Object.keys(activeLimits);

  if (keys.length === 0) {
    grid.innerHTML = `<p class="empty-text">No QoS limits currently active on this system.</p>`;
    return;
  }

  grid.innerHTML = keys.map(k => {
    const item = activeLimits[k];
    return `
      <div class="policy-card">
        <div class="policy-card-top">
          <div>
            <h4>${escapeHtml(item.target)}</h4>
            <p class="policy-sub">${escapeHtml(item.app_exe || item.target)}</p>
          </div>
          <span class="limit-badge-col limit-active">${formatKbps(item.kbps)}</span>
        </div>
        <div class="policy-card-bottom">
          <span class="priority-tag priority-${item.priority || 'normal'}">Priority: ${(item.priority || 'normal').toUpperCase()}</span>
          <button class="btn-sm-danger" onclick="removeLimit('${escapeHtml(item.target)}'); setTimeout(renderFullPoliciesView, 400);">
            <i data-lucide="trash"></i> Delete
          </button>
        </div>
      </div>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

function clearAllPolicies() {
  if (!confirm("Are you sure you want to clear all active QoS bandwidth policies?")) return;
  fetch('/api/limits/clear', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      alert(data.message);
      activeLimits = {};
      renderFullPoliciesView();
    })
    .catch(err => alert("Clear error: " + err));
}

/* API Calls */
function setLimit(target, appExe, limitKbps, priority = 'normal') {
  fetch('/api/limit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target: target,
      app_exe: appExe,
      limit_kbps: limitKbps,
      priority: priority
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'ok') {
      console.log(data.message);
    } else {
      alert(`Limit application warning: ${data.detail || data.message}`);
    }
  })
  .catch(err => alert("Failed to communicate with server: " + err));
}

function removeLimit(target) {
  fetch(`/api/limit/${encodeURIComponent(target)}`, { method: 'DELETE' })
    .then(res => res.json())
    .then(data => console.log(data.message))
    .catch(err => console.error("Remove limit error:", err));
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
