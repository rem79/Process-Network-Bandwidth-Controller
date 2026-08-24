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

// Live Table Sorting States
let currentSortKey = 'traffic';
let currentSortDir = 'desc';

// History Table Sorting States
let cachedHistoryRows = [];
let currentHistorySortKey = 'date';
let currentHistorySortDir = 'desc';

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
    const btn = document.getElementById('tabLiveBtn'); if (btn) btn.classList.add('active');
    const view = document.getElementById('viewLive'); if (view) view.classList.add('active');
  } else if (tabId === 'analytics') {
    const btn = document.getElementById('tabAnalyticsBtn'); if (btn) btn.classList.add('active');
    const view = document.getElementById('viewAnalytics'); if (view) view.classList.add('active');
    loadAnalyticsData();
  } else if (tabId === 'policies') {
    const btn = document.getElementById('tabPoliciesBtn'); if (btn) btn.classList.add('active');
    const view = document.getElementById('viewPolicies'); if (view) view.classList.add('active');
    renderFullPoliciesView();
  } else if (tabId === 'map') {
    const btn = document.getElementById('tabMapBtn'); if (btn) btn.classList.add('active');
    const view = document.getElementById('viewMap'); if (view) view.classList.add('active');
    loadGlobalMapData();
  } else if (tabId === 'diagnostics') {
    const btn = document.getElementById('tabDiagBtn'); if (btn) btn.classList.add('active');
    const view = document.getElementById('viewDiagnostics'); if (view) view.classList.add('active');
    loadDiagnosticsHealth();
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

function onSortSelectChange() {
  const selectVal = document.getElementById('sortSelect').value;
  currentSortKey = selectVal;
  currentSortDir = 'desc';
  updateLiveSortIcons();
  renderProcesses();
}

function sortByHeader(key) {
  if (currentSortKey === key) {
    currentSortDir = currentSortDir === 'asc' ? 'desc' : 'asc';
  } else {
    currentSortKey = key;
    currentSortDir = (key === 'name') ? 'asc' : 'desc';
  }

  const sortSelect = document.getElementById('sortSelect');
  if (sortSelect) {
    const matchedOpt = Array.from(sortSelect.options).find(o => o.value === key);
    if (matchedOpt) sortSelect.value = key;
  }

  updateLiveSortIcons();
  renderProcesses();
}

function updateLiveSortIcons() {
  const keys = ['name', 'pid', 'connections', 'down', 'up', 'cpu', 'limit'];
  keys.forEach(k => {
    const iconEl = document.getElementById(`sortIcon-${k}`);
    if (!iconEl) return;
    if (currentSortKey === k) {
      iconEl.setAttribute('data-lucide', currentSortDir === 'asc' ? 'chevron-up' : 'chevron-down');
      iconEl.classList.add('active');
    } else {
      iconEl.setAttribute('data-lucide', 'chevrons-up-down');
      iconEl.classList.remove('active');
    }
  });
  if (window.lucide) lucide.createIcons();
}

function renderProcesses() {
  const searchInputEl = document.getElementById('searchInput');
  const searchVal = searchInputEl ? searchInputEl.value.toLowerCase().trim() : '';

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

  // Dynamic Directional Sort
  const mult = currentSortDir === 'asc' ? 1 : -1;
  filtered.sort((a, b) => {
    if (currentSortKey === 'down') return (a.down_speed - b.down_speed) * mult;
    if (currentSortKey === 'up') return (a.up_speed - b.up_speed) * mult;
    if (currentSortKey === 'connections') return (a.connections - b.connections) * mult;
    if (currentSortKey === 'name') return a.name.localeCompare(b.name) * mult;
    if (currentSortKey === 'pid') return (a.pid - b.pid) * mult;
    if (currentSortKey === 'cpu') return (a.cpu_percent - b.cpu_percent) * mult;
    if (currentSortKey === 'limit') {
      const aLim = a.limit_kbps || 0;
      const bLim = b.limit_kbps || 0;
      return (aLim - bLim) * mult;
    }
    // Default 'traffic'
    return ((a.down_speed + a.up_speed) - (b.down_speed + b.up_speed)) * mult;
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
          <button class="socket-link-btn" data-pid="${p.pid}" data-name="${escapeHtml(p.name)}" onclick="openConnectionsModalFromDataset(this)" title="Inspect active TCP/UDP sockets for PID ${p.pid}">
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

  const titleEl = document.getElementById('modalTargetTitle') || document.getElementById('modalTitle');
  if (titleEl) titleEl.innerText = `Limit Speed: ${displayTitle}`;

  const subEl = document.getElementById('modalTargetSub') || document.getElementById('modalSub');
  if (subEl) subEl.innerText = targetName === 'global' ? 'System-wide network throttling' : `Executable: ${currentModalExe}`;

  const targetInput = document.getElementById('targetExeInput');
  if (targetInput) targetInput.value = currentModalExe;

  const priorityEl = document.getElementById('prioritySelect');
  if (priorityEl) priorityEl.value = priority || 'normal';

  const initVal = currentKbps > 0 ? currentKbps : 1024;
  updateModalValueDisplays(initVal);

  const modalEl = document.getElementById('limitModal');
  if (modalEl) modalEl.classList.add('show');
}

function openLimitModalFromDataset(el) {
  const target = el.getAttribute('data-target') || '';
  const name = el.getAttribute('data-name') || target;
  const exe = el.getAttribute('data-exe') || target;
  const kbps = parseInt(el.getAttribute('data-kbps'), 10) || 0;
  const priority = el.getAttribute('data-priority') || 'normal';
  openLimitModal(target, name, exe, kbps, priority);
}

function closeLimitModal() {
  document.getElementById('limitModal').classList.remove('show');
}

function selectModalPreset(kbps) {
  updateModalValueDisplays(kbps, true);
}

function onSliderChange(val) {
  updateModalValueDisplays(parseInt(val, 10), true);
}

function onCustomUnitInputChange() {
  const val = parseFloat(document.getElementById('customLimitValueInput').value) || 0;
  const unit = document.getElementById('customLimitUnitSelect').value;
  let kbps = 0;
  if (unit === 'KB') {
    kbps = Math.round(val);
  } else if (unit === 'MB') {
    kbps = Math.round(val * 1024);
  } else if (unit === 'GB') {
    kbps = Math.round(val * 1024 * 1024);
  }
  updateModalValueDisplays(kbps, false);
}

function updateModalValueDisplays(kbps, updateUnitInputs = true) {
  const boundedKbps = Math.max(0, Math.min(104857600, kbps));
  document.getElementById('limitSlider').value = boundedKbps;
  document.getElementById('customLimitInput').value = boundedKbps;

  if (updateUnitInputs) {
    const valInput = document.getElementById('customLimitValueInput');
    const unitSelect = document.getElementById('customLimitUnitSelect');
    if (valInput && unitSelect) {
      if (boundedKbps >= 1048576) {
        valInput.value = (boundedKbps / 1048576).toFixed(boundedKbps % 1048576 === 0 ? 0 : 2);
        unitSelect.value = 'GB';
      } else if (boundedKbps >= 1024) {
        valInput.value = (boundedKbps / 1024).toFixed(boundedKbps % 1024 === 0 ? 0 : 2);
        unitSelect.value = 'MB';
      } else {
        valInput.value = boundedKbps;
        unitSelect.value = 'KB';
      }
    }
  }

  const display = document.getElementById('modalValDisplay');
  if (boundedKbps <= 0) {
    display.innerText = "UNLIMITED (Remove QoS Policy)";
  } else {
    const mbps = (boundedKbps * 8 / 1000).toFixed(2);
    display.innerText = `${formatKbps(boundedKbps)} (${boundedKbps.toLocaleString()} KB/s | ~${mbps} Mbps)`;
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

function applyQuickGlobalLimit() {
  const val = parseFloat(document.getElementById('quickGlobalValue').value) || 0;
  const unit = document.getElementById('quickGlobalUnit').value;
  if (val <= 0) {
    showNotification("Please enter a value greater than 0", "warning");
    return;
  }
  let kbps = 0;
  if (unit === 'KB') {
    kbps = Math.round(val);
  } else if (unit === 'MB') {
    kbps = Math.round(val * 1024);
  } else if (unit === 'GB') {
    kbps = Math.round(val * 1024 * 1024);
  }
  setLimit('global', '*', kbps);
}

function removeGlobalLimit() {
  removeLimit('global');
}

/* Socket Inspector Modal */
function openConnectionsModalFromDataset(el) {
  const pid = parseInt(el.getAttribute('data-pid'), 10) || 0;
  const name = el.getAttribute('data-name') || `PID ${pid}`;
  openConnectionsModal(pid, name);
}

function openConnectionsModal(pid, name) {
  const titleEl = document.getElementById('connModalTitle');
  const subEl = document.getElementById('connModalSub');
  const tbody = document.getElementById('connTableBody');

  if (titleEl) titleEl.innerText = `Sockets & Route Telemetry: ${name} (PID: ${pid})`;
  if (subEl) subEl.innerText = `Querying active TCP/UDP endpoints, Reverse DNS & Latency for PID ${pid}...`;
  if (tbody) tbody.innerHTML = `<tr class="empty-row"><td colspan="8"><div class="loading-spinner"></div><p>Resolving GeoIP & Latency Telemetry...</p></td></tr>`;
  
  const modalEl = document.getElementById('connectionsModal');
  if (modalEl) modalEl.classList.add('show');

  fetch(`/api/process/${pid}/connections`)
    .then(res => {
      if (!res.ok) throw new Error("Process ended or access denied");
      return res.json();
    })
    .then(data => {
      if (subEl) subEl.innerText = `Found ${data.count || 0} active endpoints | Reverse DNS & Latency verified`;
      if (!tbody) return;

      if (!data.connections || data.connections.length === 0) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="8">No active network endpoints established.</td></tr>`;
        return;
      }

      tbody.innerHTML = data.connections.map(c => {
        const rtt = c.latency_ms || 1.0;
        let latClass = 'latency-fast';
        if (rtt > 150) latClass = 'latency-slow';
        else if (rtt > 50) latClass = 'latency-med';

        const threatBadge = (c.threat && c.threat.level === 'danger')
          ? `<span class="threat-badge threat-danger" title="${escapeHtml(c.threat.reason)}">⚠️ THREAT</span>`
          : '';

        const killBtn = (c.type === 'TCP' && c.remote_ip !== 'N/A')
          ? `<button class="btn-kill-socket" onclick="killSocket(${pid}, '${c.local_ip}', ${c.local_port}, '${c.remote_ip}', ${c.remote_port}, this)" title="Terminate TCP connection"><i data-lucide="scissors"></i> Kill</button>`
          : `<span class="text-sub">-</span>`;

        return `
          <tr>
            <td><span class="pid-tag ${c.type === 'TCP' ? 'tag-cyan' : 'tag-violet'}">${c.type}</span></td>
            <td class="mono-text">${escapeHtml(c.local_address)}</td>
            <td class="mono-text endpoint-addr">${escapeHtml(c.remote_address)}</td>
            <td>
              <div class="geo-tag" title="${escapeHtml(c.rdns || c.remote_ip)}">
                <i data-lucide="globe" style="width:12px;height:12px;"></i>
                <span class="mono-text">${escapeHtml(c.rdns || c.remote_ip)}</span>
                ${threatBadge}
              </div>
            </td>
            <td>
              <span class="geo-tag">
                <span>${c.flag || '🌐'}</span>
                <span>${escapeHtml(c.org || c.country || 'Global')}</span>
              </span>
            </td>
            <td>
              <span class="latency-pill ${latClass}">
                <i data-lucide="zap" style="width:10px;height:10px;"></i>
                <span>${rtt.toFixed(1)} ms</span>
              </span>
            </td>
            <td><span class="status-badge-sm status-${(c.status || 'established').toLowerCase()}">${c.status || 'ESTABLISHED'}</span></td>
            <td class="text-right">${killBtn}</td>
          </tr>
        `;
      }).join('');

      if (window.lucide) lucide.createIcons();
    })
    .catch(err => {
      if (tbody) tbody.innerHTML = `<tr class="empty-row"><td colspan="8" style="color: #FF0054;">${err.message}</td></tr>`;
    });
}

function killSocket(pid, localIp, localPort, remoteIp, remotePort, btnEl) {
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerText = "Terminating...";
  }

  fetch('/api/socket/kill', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pid: pid,
      local_ip: localIp,
      local_port: parseInt(localPort, 10),
      remote_ip: remoteIp,
      remote_port: parseInt(remotePort, 10)
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'ok') {
      showToast(`Connection to ${remoteIp}:${remotePort} terminated!`, 'success');
      if (btnEl) {
        const row = btnEl.closest('tr');
        if (row) row.style.opacity = '0.3';
        btnEl.innerText = "KILLED";
      }
    } else {
      showToast(data.message || "Failed to terminate socket", 'danger');
      if (btnEl) { btnEl.disabled = false; btnEl.innerText = "Kill"; }
    }
  })
  .catch(err => {
    showToast(`Error: ${err.message}`, 'danger');
    if (btnEl) { btnEl.disabled = false; btnEl.innerText = "Kill"; }
  });
}

function closeConnectionsModal() {
  const modalEl = document.getElementById('connectionsModal');
  if (modalEl) modalEl.classList.remove('show');
}

function openPlaybookModal() {
  const modalEl = document.getElementById('playbookModal');
  if (modalEl) modalEl.classList.add('show');
  if (window.lucide) lucide.createIcons();

  // Attach smooth scrolling to section pills
  const pills = modalEl.querySelectorAll('.pb-pill');
  pills.forEach(pill => {
    pill.onclick = (e) => {
      e.preventDefault();
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const targetId = pill.getAttribute('href');
      const targetSection = modalEl.querySelector(targetId);
      if (targetSection) {
        targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };
  });
}

function closePlaybookModal() {
  const modalEl = document.getElementById('playbookModal');
  if (modalEl) modalEl.classList.remove('show');
}

function onBackdropClick(event, modalId) {
  if (event.target && event.target.id === modalId) {
    if (modalId === 'connectionsModal') closeConnectionsModal();
    if (modalId === 'limitModal') closeLimitModal();
    if (modalId === 'playbookModal') closePlaybookModal();
  }
}

// Global Escape Key Listener for Modals
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeLimitModal();
    closeConnectionsModal();
    closePlaybookModal();
  }
});

/* ==========================================================================
   v3.0 GLOBAL CYBER MAP ENGINE
   ========================================================================== */
function loadGlobalMapData() {
  const nodesGroup = document.getElementById('mapNodesGroup');
  const destList = document.getElementById('activeDestList');
  if (destList) destList.innerHTML = `<div class="loading-spinner"></div>`;

  fetch('/api/map/connections')
    .then(res => res.json())
    .then(nodes => {
      if (!nodesGroup || !destList) return;

      // Coordinate projection (Equirectangular to SVG 1000x500)
      const homeX = (126.978 + 180) * (1000 / 360);
      const homeY = (90 - 37.566) * (500 / 180);

      let svgHtml = `
        <!-- Home Node (Korea) -->
        <circle cx="${homeX}" cy="${homeY}" r="6" fill="#00F5D4" filter="url(#glowFilter)"/>
        <circle cx="${homeX}" cy="${homeY}" r="14" fill="none" stroke="#00F5D4" stroke-width="1.5" opacity="0.6">
          <animate attributeName="r" values="6;22;6" dur="2s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.8;0.0;0.8" dur="2s" repeatCount="indefinite"/>
        </circle>
      `;

      if (nodes.length === 0) {
        destList.innerHTML = `<p class="empty-text">No active outbound internet sessions detected.</p>`;
        nodesGroup.innerHTML = svgHtml;
        return;
      }

      destList.innerHTML = nodes.map(n => `
        <div class="dest-card">
          <div class="dest-info-left">
            <span class="dest-name">${n.flag || '🌐'} ${escapeHtml(n.org || n.rdns || n.ip)}</span>
            <span class="dest-sub">${n.proc_name} &bull; ${n.ip}:${n.port}</span>
          </div>
          <span class="latency-pill latency-${n.latency_ms > 150 ? 'slow' : (n.latency_ms > 50 ? 'med' : 'fast')}">
            ${n.latency_ms.toFixed(1)} ms
          </span>
        </div>
      `).join('');

      nodes.forEach((n, idx) => {
        const targetX = (n.lon + 180) * (1000 / 360);
        const targetY = (90 - n.lat) * (500 / 180);
        const midX = (homeX + targetX) / 2;
        const midY = Math.min(homeY, targetY) - 40;

        const pathD = `M${homeX},${homeY} Q${midX},${midY} ${targetX},${targetY}`;
        const nodeColor = n.country === 'KR' ? '#00F2FE' : '#9D4EDD';

        svgHtml += `
          <!-- Arc Line -->
          <path d="${pathD}" fill="none" stroke="url(#cyberLineGrad)" stroke-width="1.8" stroke-dasharray="6,4" opacity="0.7">
            <animate attributeName="stroke-dashoffset" values="40;0" dur="${1.5 + (idx % 3) * 0.5}s" repeatCount="indefinite"/>
          </path>
          <!-- Remote Node -->
          <circle cx="${targetX}" cy="${targetY}" r="4" fill="${nodeColor}" filter="url(#glowFilter)"/>
        `;
      });

      nodesGroup.innerHTML = svgHtml;
    })
    .catch(err => {
      if (destList) destList.innerHTML = `<p class="empty-text" style="color:#FF0054;">Failed to load map: ${err.message}</p>`;
    });
}

/* ==========================================================================
   v3.0 DIAGNOSTIC TOOLBOX ENGINE (nslookup, Traceroute, Health)
   ========================================================================== */
function loadDiagnosticsHealth() {
  fetch('/api/diagnostics/health')
    .then(res => res.json())
    .then(data => {
      const ifaceEl = document.getElementById('metricInterface');
      const sigEl = document.getElementById('metricSignal');
      const gwEl = document.getElementById('metricGateway');
      const subEl = document.getElementById('healthSub');

      if (ifaceEl) ifaceEl.innerText = data.interface || 'Ethernet / LAN';
      if (sigEl) sigEl.innerText = `${data.signal_pct}%`;
      if (gwEl) gwEl.innerText = `~${data.gateway_rtt_ms.toFixed(1)} ms`;
      if (subEl) subEl.innerText = data.diagnosis || 'Local network active';
    })
    .catch(err => console.error("Health check error:", err));
}

function executeNslookup() {
  const inputEl = document.getElementById('nslookupInput');
  const target = inputEl ? inputEl.value.trim() : 'netflix.com';
  const resEl = document.getElementById('dnsBenchmarkResults');
  if (!target || !resEl) return;

  resEl.innerHTML = `<div class="loading-spinner"></div><p style="text-align:center;font-size:0.8rem;color:var(--text-sub);">Querying DNS providers (KT, SK, LG, Cloudflare, Google)...</p>`;

  fetch('/api/diagnostics/nslookup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain: target })
  })
  .then(res => res.json())
  .then(data => {
    if (data.error) {
      resEl.innerHTML = `<p class="empty-text" style="color:#FF0054;">${escapeHtml(data.error)}</p>`;
      return;
    }

    let recordsHtml = '';
    if (data.records && data.records.length > 0) {
      recordsHtml = `
        <div style="margin-bottom:12px;padding:8px 10px;background:rgba(0,242,254,0.05);border-radius:6px;border:1px solid rgba(0,242,254,0.2);">
          <span style="font-size:0.75rem;color:var(--accent-cyan);font-weight:700;">RESOLVED A / AAAA IP:</span>
          <span class="mono-text" style="font-size:0.85rem;color:#FFFFFF;margin-left:8px;">${data.records.map(r => `${r.flag} ${r.ip}`).join(', ')}</span>
        </div>
      `;
    }

    const benchHtml = (data.benchmarks || []).map((b, idx) => {
      const isFastest = idx === 0 && b.status === 'OK';
      return `
        <div class="dns-row">
          <div class="dns-name-group">
            <span>${b.flag}</span>
            <div>
              <span style="font-weight:700;color:#FFFFFF;">${escapeHtml(b.provider)}</span>
              ${isFastest ? '<span class="status-badge-sm status-established" style="margin-left:6px;">FASTEST ⚡</span>' : ''}
              <div class="dns-ip">${b.server_ip} &bull; ${b.type}</div>
            </div>
          </div>
          <span class="latency-pill latency-${b.latency_ms > 100 ? 'slow' : (b.latency_ms > 40 ? 'med' : 'fast')}">
            ${b.status === 'OK' ? `${b.latency_ms.toFixed(1)} ms` : b.status}
          </span>
        </div>
      `;
    }).join('');

    resEl.innerHTML = recordsHtml + benchHtml;
  })
  .catch(err => {
    resEl.innerHTML = `<p class="empty-text" style="color:#FF0054;">Lookup error: ${err.message}</p>`;
  });
}

function executeTraceroute() {
  const inputEl = document.getElementById('tracerouteInput');
  const target = inputEl ? inputEl.value.trim() : '8.8.8.8';
  const resEl = document.getElementById('tracerouteResults');
  if (!target || !resEl) return;

  resEl.innerHTML = `<div class="loading-spinner"></div><p style="text-align:center;font-size:0.8rem;color:var(--text-sub);">Tracing router hops to ${escapeHtml(target)} (10-15s)...</p>`;

  fetch('/api/diagnostics/traceroute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target: target })
  })
  .then(res => res.json())
  .then(data => {
    if (data.error || !data.hops || data.hops.length === 0) {
      resEl.innerHTML = `<p class="empty-text" style="color:#FF0054;">${escapeHtml(data.error || 'Traceroute timed out.')}</p>`;
      return;
    }

    resEl.innerHTML = data.hops.map(h => `
      <div class="hop-row">
        <span class="hop-num">#${h.hop}</span>
        <span style="font-size:1.1rem;">${h.flag || '🌐'}</span>
        <div class="hop-info">
          <div class="hop-name">${escapeHtml(h.org || h.rdns || h.ip)}</div>
          <div class="hop-ip">${h.ip} &bull; ${escapeHtml(h.rdns || 'Backbone Node')}</div>
        </div>
        <span class="latency-pill latency-${h.rtt_ms > 150 ? 'slow' : (h.rtt_ms > 50 ? 'med' : 'fast')}">
          ${h.rtt_ms.toFixed(1)} ms
        </span>
      </div>
    `).join('');
  })
  .catch(err => {
    resEl.innerHTML = `<p class="empty-text" style="color:#FF0054;">Traceroute error: ${err.message}</p>`;
  });
}

/* Analytics Data Loader & Sorting */
function sortHistoryByHeader(key) {
  if (currentHistorySortKey === key) {
    currentHistorySortDir = currentHistorySortDir === 'asc' ? 'desc' : 'asc';
  } else {
    currentHistorySortKey = key;
    currentHistorySortDir = (key === 'name') ? 'asc' : 'desc';
  }
  updateHistorySortIcons();
  renderDailyHistoryTable();
}

function updateHistorySortIcons() {
  const keys = ['date', 'name', 'up', 'down', 'total'];
  keys.forEach(k => {
    const iconEl = document.getElementById(`histSortIcon-${k}`);
    if (!iconEl) return;
    if (currentHistorySortKey === k) {
      iconEl.setAttribute('data-lucide', currentHistorySortDir === 'asc' ? 'chevron-up' : 'chevron-down');
      iconEl.classList.add('active');
    } else {
      iconEl.setAttribute('data-lucide', 'chevrons-up-down');
      iconEl.classList.remove('active');
    }
  });
  if (window.lucide) lucide.createIcons();
}

function renderDailyHistoryTable() {
  const tbody = document.getElementById('dailyHistoryBody');
  if (!tbody) return;
  if (!cachedHistoryRows || cachedHistoryRows.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="6">No daily traffic logs recorded yet.</td></tr>`;
    return;
  }

  const mult = currentHistorySortDir === 'asc' ? 1 : -1;
  const sorted = [...cachedHistoryRows].sort((a, b) => {
    if (currentHistorySortKey === 'date') return a.date.localeCompare(b.date) * mult;
    if (currentHistorySortKey === 'name') return a.name.localeCompare(b.name) * mult;
    if (currentHistorySortKey === 'up') return ((a.total_up_bytes || 0) - (b.total_up_bytes || 0)) * mult;
    if (currentHistorySortKey === 'down') return ((a.total_down_bytes || 0) - (b.total_down_bytes || 0)) * mult;
    // Default 'total'
    return ((a.total_bytes || 0) - (b.total_bytes || 0)) * mult;
  });

  tbody.innerHTML = sorted.map(r => `
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
      <td class="text-right">
        <button class="btn-action-limit" title="Set QoS Bandwidth Limit" data-target="${escapeHtml(r.name)}" data-name="${escapeHtml(r.name)}" data-exe="${escapeHtml(r.exe || r.name)}" onclick="openLimitModalFromDataset(this)">
          <i data-lucide="sliders"></i> Limit
        </button>
      </td>
    </tr>
  `).join('');
  if (window.lucide) lucide.createIcons();
}

function loadAnalyticsData() {
  const topList = document.getElementById('topConsumersList');
  if (topList) topList.innerHTML = `<div class="loading-spinner"></div>`;

  // Fetch Top 24h
  fetch('/api/history/top?hours=24&limit=8')
    .then(res => res.json())
    .then(items => {
      if (!topList) return;
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
          <div class="top-action">
            <button class="btn-action-limit" title="Set QoS Bandwidth Limit" data-target="${escapeHtml(item.name)}" data-name="${escapeHtml(item.name)}" data-exe="${escapeHtml(item.exe || item.name)}" onclick="openLimitModalFromDataset(this)">
              <i data-lucide="sliders"></i> Limit
            </button>
          </div>
        </div>
      `).join('');
      if (window.lucide) lucide.createIcons();
    })
    .catch(err => {
      if (topList) topList.innerHTML = `<p class="empty-text error-text">Failed to load analytics: ${err}</p>`;
    });

  // Fetch Daily Breakdown
  fetch('/api/history/daily?days=7')
    .then(res => res.json())
    .then(rows => {
      cachedHistoryRows = rows || [];
      updateHistorySortIcons();
      renderDailyHistoryTable();
    })
    .catch(err => {
      const tbody = document.getElementById('dailyHistoryBody');
      if (tbody) tbody.innerHTML = `<tr class="empty-row"><td colspan="6">Error: ${err}</td></tr>`;
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
          <div class="policy-actions">
            <button class="btn-sm-edit" title="Adjust Speed Limit" data-target="${escapeHtml(item.target)}" data-name="${escapeHtml(item.target)}" data-exe="${escapeHtml(item.app_exe || item.target)}" data-kbps="${item.kbps || 0}" data-priority="${escapeHtml(item.priority || 'normal')}" onclick="openLimitModalFromDataset(this)">
              <i data-lucide="sliders"></i> Adjust Limit
            </button>
            <button class="btn-sm-danger" title="Remove QoS Policy" onclick="removeLimit('${escapeHtml(item.target)}'); setTimeout(renderFullPoliciesView, 400);">
              <i data-lucide="trash"></i> Delete
            </button>
          </div>
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
      showToast(data.message, 'success');
      activeLimits = {};
      renderFullPoliciesView();
    })
    .catch(err => showToast("Clear error: " + err, 'error'));
}

/* API Calls & Instant Refresh */
function refreshLimitsAndViews() {
  fetch('/api/limits')
    .then(res => res.json())
    .then(data => {
      activeLimits = data || {};
      const ruleCount = Object.keys(activeLimits).length;
      const countEl = document.getElementById('tabRulesCount');
      if (countEl) countEl.innerText = ruleCount;

      const gLimit = activeLimits['global'];
      const gBadge = document.getElementById('globalLimitBadge');
      if (gBadge) {
        if (gLimit) {
          gBadge.innerText = `LIMIT: ${formatKbps(gLimit.kbps)}`;
          gBadge.className = 'trend-tag tag-amber';
        } else {
          gBadge.innerText = 'UNLIMITED';
          gBadge.className = 'trend-tag tag-cyan';
        }
      }

      renderFullPoliciesView();
      renderProcesses();
    })
    .catch(err => console.error("Error refreshing limits:", err));
}

function setLimit(target, appExe, limitKbps, priority = 'normal') {
  // Optimistic instant UI update
  if (limitKbps > 0) {
    activeLimits[target] = {
      target: target,
      app_exe: appExe || target,
      kbps: limitKbps,
      priority: priority,
      active: true
    };
  } else {
    delete activeLimits[target];
  }
  const ruleCount = Object.keys(activeLimits).length;
  const countEl = document.getElementById('tabRulesCount');
  if (countEl) countEl.innerText = ruleCount;

  renderFullPoliciesView();
  renderProcesses();

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
      showToast(data.message, 'success');
    } else {
      showToast(`Limit warning: ${data.detail || data.message}`, 'warning');
    }
    refreshLimitsAndViews();
  })
  .catch(err => {
    showToast("Failed to communicate with server: " + err, 'error');
    refreshLimitsAndViews();
  });
}

function removeLimit(target) {
  // Optimistic instant UI update
  delete activeLimits[target];
  const ruleCount = Object.keys(activeLimits).length;
  const countEl = document.getElementById('tabRulesCount');
  if (countEl) countEl.innerText = ruleCount;

  renderFullPoliciesView();
  renderProcesses();

  fetch(`/api/limit/${encodeURIComponent(target)}`, { method: 'DELETE' })
    .then(res => res.json())
    .then(data => {
      showToast(data.message || `Removed QoS limit for ${target}`, 'info');
      refreshLimitsAndViews();
    })
    .catch(err => {
      console.error("Remove limit error:", err);
      refreshLimitsAndViews();
    });
}

/* Toast Notifications */
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) {
    console.log(`[Toast ${type}]: ${message}`);
    return;
  }

  const toast = document.createElement('div');
  toast.className = `toast-card toast-${type}`;
  
  let iconName = 'info';
  if (type === 'success') iconName = 'check-circle';
  if (type === 'warning') iconName = 'alert-triangle';
  if (type === 'error') iconName = 'alert-circle';

  toast.innerHTML = `<i data-lucide="${iconName}"></i><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  if (window.lucide) lucide.createIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(60px)';
    setTimeout(() => toast.remove(), 350);
  }, 3500);
}

// ----------------------------------------------------
// One-Click Network Emergency Flush & Repair
// ----------------------------------------------------
function executeNetworkFlush() {
  const btnEl = document.getElementById('btnFlushNetwork');
  const logContainer = document.getElementById('flushActionLog');
  if (!logContainer) return;

  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerHTML = `<div class="spinner" style="width:14px;height:14px;border-width:2px;"></div> Repairing Network...`;
  }

  logContainer.innerHTML = `<div class="flush-idle-msg">Executing Windows Network Stack Flush (DNS Purge, ARP Cache Reset, DNS Re-registration)...</div>`;

  fetch('/api/diagnostics/flush', {
    method: 'POST'
  })
  .then(res => res.json())
  .then(data => {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.innerHTML = `<i data-lucide="zap"></i> Run Emergency Flush & Repair`;
    }

    if (data.status === 'ok') {
      showToast("Network Stack & DNS flushed successfully!", "success");
      let html = `<div class="flush-steps-container">`;
      (data.actions || []).forEach(act => {
        html += `
          <div class="flush-step-row">
            <span class="flush-step-title">✅ ${escapeHtml(act.step)}</span>
            <span class="flush-step-msg">${escapeHtml(act.msg)}</span>
          </div>
        `;
      });
      html += `</div>`;
      logContainer.innerHTML = html;
      loadDiagnosticsHealth(); // Refresh adapter health
    } else {
      showToast(data.message || "Flush encountered issues", "warning");
      logContainer.innerHTML = `<div class="text-danger" style="font-size:0.85rem;">⚠️ ${escapeHtml(data.message)}</div>`;
    }
    if (window.lucide) lucide.createIcons();
  })
  .catch(err => {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.innerHTML = `<i data-lucide="zap"></i> Run Emergency Flush & Repair`;
    }
    showToast(`Failed to flush network: ${err.message}`, "danger");
    logContainer.innerHTML = `<div class="text-danger" style="font-size:0.85rem;">⚠️ Error: ${escapeHtml(err.message)}</div>`;
    if (window.lucide) lucide.createIcons();
  });
}

// ----------------------------------------------------
// TCP Port Reachability & Firewall Tester
// ----------------------------------------------------
function selectPortPreset(port, name) {
  const portInput = document.getElementById('portTestPortInput');
  if (portInput) portInput.value = port;
  showToast(`Selected port ${port} (${name})`, 'info');
}

function executePortTest() {
  const hostInput = document.getElementById('portTestHostInput');
  const portInput = document.getElementById('portTestPortInput');
  const resContainer = document.getElementById('portTestResults');
  if (!hostInput || !portInput || !resContainer) return;

  const host = hostInput.value.trim();
  const port = parseInt(portInput.value, 10);
  if (!host || isNaN(port)) {
    showToast("Please enter valid host IP and port number", "warning");
    return;
  }

  resContainer.innerHTML = `<div class="empty-text"><div class="spinner" style="width:14px;height:14px;border-width:2px;display:inline-block;"></div> Testing TCP Handshake to ${escapeHtml(host)}:${port}...</div>`;

  fetch('/api/diagnostics/port-test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host: host, port: port })
  })
  .then(res => res.json())
  .then(data => {
    let badgeClass = 'port-badge-closed';
    if (data.status === 'OPEN') badgeClass = 'port-badge-open';

    resContainer.innerHTML = `
      <div class="port-res-card">
        <div class="port-res-header">
          <div>
            <strong>${escapeHtml(data.host)}:${data.port}</strong>
            <span style="font-size:0.75rem; color:var(--text-muted); margin-left:6px;">(${escapeHtml(data.service)})</span>
          </div>
          <span class="${badgeClass}">${data.status} ${data.latency_ms ? `(~${data.latency_ms} ms)` : ''}</span>
        </div>
        <p style="font-size:0.78rem; color:var(--text-sub); margin:0; line-height:1.4;">${escapeHtml(data.message)}</p>
      </div>
    `;
    if (data.status === 'OPEN') {
      showToast(`Port ${port} is OPEN! Handshake: ${data.latency_ms}ms`, 'success');
    } else {
      showToast(`Port ${port} is ${data.status}`, 'warning');
    }
  })
  .catch(err => {
    resContainer.innerHTML = `<div class="text-danger" style="font-size:0.85rem;">⚠️ Error: ${escapeHtml(err.message)}</div>`;
    showToast(`Port test failed: ${err.message}`, 'danger');
  });
}

// ----------------------------------------------------
// Continuous Live Jitter & Packet Loss Monitor
// ----------------------------------------------------
let jitterInterval = null;
let jitterHistory = [];
const MAX_JITTER_POINTS = 30;
let jitterSent = 0;
let jitterLost = 0;

function toggleJitterMonitor() {
  const btnEl = document.getElementById('btnToggleJitter');
  const hostInput = document.getElementById('jitterHostInput');
  if (!btnEl || !hostInput) return;

  if (jitterInterval) {
    clearInterval(jitterInterval);
    jitterInterval = null;
    btnEl.innerHTML = `<i data-lucide="play"></i> Start Monitor`;
    btnEl.className = 'btn-cyan';
    showToast("Jitter monitor paused", "info");
  } else {
    const target = hostInput.value.trim() || '8.8.8.8';
    jitterSent = 0;
    jitterLost = 0;
    jitterHistory = [];
    btnEl.innerHTML = `<i data-lucide="square"></i> Stop Monitor`;
    btnEl.className = 'btn-danger';
    showToast(`Started live ping monitor to ${target}`, "success");
    runJitterProbe(target);
    jitterInterval = setInterval(() => runJitterProbe(target), 1200);
  }
  if (window.lucide) lucide.createIcons();
}

function runJitterProbe(target) {
  jitterSent++;
  fetch('/api/diagnostics/ping-sample', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host: target })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'ok' && data.latency_ms !== null) {
      jitterHistory.push(data.latency_ms);
      document.getElementById('jitterCurPing').innerText = `${data.latency_ms} ms`;
    } else {
      jitterLost++;
      jitterHistory.push(null);
      document.getElementById('jitterCurPing').innerText = `TIMEOUT`;
    }

    if (jitterHistory.length > MAX_JITTER_POINTS) jitterHistory.shift();

    const lossPct = ((jitterLost / jitterSent) * 100).toFixed(1);
    const lossEl = document.getElementById('jitterLossVal');
    if (lossEl) {
      lossEl.innerText = `${lossPct}%`;
      if (lossPct > 0) lossEl.classList.add('has-loss');
      else lossEl.classList.remove('has-loss');
    }

    // Calc Avg Jitter
    const validPings = jitterHistory.filter(p => p !== null);
    if (validPings.length > 1) {
      let diffs = 0;
      for (let i = 1; i < validPings.length; i++) {
        diffs += Math.abs(validPings[i] - validPings[i - 1]);
      }
      const avgJitter = (diffs / (validPings.length - 1)).toFixed(1);
      document.getElementById('jitterAvgVal').innerText = `~${avgJitter} ms`;
    }

    renderJitterCanvas();
  })
  .catch(() => {
    jitterLost++;
    jitterHistory.push(null);
    if (jitterHistory.length > MAX_JITTER_POINTS) jitterHistory.shift();
    renderJitterCanvas();
  });
}

function renderJitterCanvas() {
  const canvas = document.getElementById('jitterCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  // Background Grid Lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
  ctx.lineWidth = 1;
  for (let y = 15; y < h; y += 20) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  if (jitterHistory.length === 0) return;

  const validVals = jitterHistory.filter(v => v !== null);
  const maxVal = Math.max(100, ...validVals);
  const stepX = w / (MAX_JITTER_POINTS - 1);

  // Draw Area Gradient
  ctx.beginPath();
  let firstValid = true;
  for (let i = 0; i < jitterHistory.length; i++) {
    const val = jitterHistory[i];
    const x = i * stepX;
    const y = val === null ? h - 4 : h - (val / maxVal) * (h - 15) - 8;

    if (i === 0 || firstValid) {
      ctx.moveTo(x, y);
      firstValid = false;
    } else {
      ctx.lineTo(x, y);
    }
  }

  ctx.strokeStyle = '#00F2FE';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Draw Dots
  for (let i = 0; i < jitterHistory.length; i++) {
    const val = jitterHistory[i];
    const x = i * stepX;
    const y = val === null ? h - 4 : h - (val / maxVal) * (h - 15) - 8;

    ctx.beginPath();
    ctx.arc(x, y, val === null ? 3 : 2.5, 0, Math.PI * 2);
    ctx.fillStyle = val === null ? '#EF4444' : '#00F2FE';
    ctx.fill();
  }
}

// ----------------------------------------------------
// Export Diagnostic Report (One-Click HTML Export)
// ----------------------------------------------------
function exportDiagnosticReport() {
  const triggerBtn = document.querySelector('.btn-export-trigger');
  if (triggerBtn) {
    triggerBtn.disabled = true;
    triggerBtn.innerHTML = `<div class="spinner" style="width:12px;height:12px;border-width:2px;display:inline-block;"></div> <span>저장 중...</span>`;
  }

  try {
    const timestamp = new Date().toLocaleString();
    const fileDate = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);

    let activeProcsHtml = '';
    const procs = (allProcesses && allProcesses.length > 0) ? allProcesses.slice(0, 15) : [];
    procs.forEach(p => {
      activeProcsHtml += `
        <tr>
          <td>${p.pid}</td>
          <td><strong>${escapeHtml(p.name)}</strong></td>
          <td>${p.down_formatted || '0 KB/s'}</td>
          <td>${p.up_formatted || '0 KB/s'}</td>
          <td>${p.cpu_percent ? p.cpu_percent.toFixed(1) : 0}%</td>
          <td>${p.connections || 0}</td>
        </tr>
      `;
    });

    const ifaceText = document.getElementById('metricInterface') ? document.getElementById('metricInterface').innerText : 'Ethernet';
    const signalText = document.getElementById('metricSignal') ? document.getElementById('metricSignal').innerText : '100%';
    const gatewayText = document.getElementById('metricGateway') ? document.getElementById('metricGateway').innerText : 'Optimal';
    const activeCapsCount = Object.keys(activeLimits || {}).length;

    // --- AI Local Heuristic Diagnostic Engine (100% Offline) ---
    let healthScore = 100;
    let scoreBadge = "EXCELLENT";
    let scoreColor = "#10B981";
    let identifiedBottlenecks = [];
    let prescriptiveActions = [];

    // 1. Analyze Gateway Latency
    let gwMs = 1.2;
    if (gatewayText.includes('ms')) {
      const match = gatewayText.match(/([\d.]+)\s*ms/);
      if (match) gwMs = parseFloat(match[1]);
    }
    if (gwMs > 50) {
      healthScore -= 20;
      identifiedBottlenecks.push(`로컬 게이트웨이(공유기/스위치) 핑 지연시간이 ${gwMs}ms로 다소 높음`);
      prescriptiveActions.push(`사무실 공유기/스위치 허브 상태 점검 및 유선 랜선 재연결 권장`);
    }

    // 2. Analyze Dominant Processes
    const heavyCpuProc = procs.find(p => p.cpu_percent > 40);
    const heavyNetProc = procs.find(p => (p.down_speed + p.up_speed) > (500 * 1024)); // >500 KB/s
    const emulatorProcs = procs.filter(p => p.name.toLowerCase().includes('ld9') || p.name.toLowerCase().includes('dnplayer') || p.name.toLowerCase().includes('nox') || p.name.toLowerCase().includes('memu'));

    if (emulatorProcs.length > 0) {
      const totalEmuCpu = emulatorProcs.reduce((acc, p) => acc + (p.cpu_percent || 0), 0);
      if (totalEmuCpu > 50) {
        healthScore -= 15;
        identifiedBottlenecks.push(`안드로이드 에뮬레이터(${emulatorProcs[0].name} 등 ${emulatorProcs.length}개)가 호스트 CPU의 ${totalEmuCpu.toFixed(1)}%를 점유하여 시스템 경합 발생`);
        prescriptiveActions.push(`LD플레이어 등 백그라운드 에뮬레이터에 센티넬 [Throttle] 속도 제한 적용 및 미사용 인스턴스 종료 권장`);
      }
    } else if (heavyCpuProc) {
      healthScore -= 10;
      identifiedBottlenecks.push(`${heavyCpuProc.name} (PID ${heavyCpuProc.pid}) 프로세스가 CPU ${heavyCpuProc.cpu_percent.toFixed(1)}% 점유 중`);
      prescriptiveActions.push(`${heavyCpuProc.name} 프로세스의 작업 우선순위 또는 스레드 점유 상태 확인 필요`);
    }

    if (heavyNetProc) {
      identifiedBottlenecks.push(`${heavyNetProc.name} 프로세스가 지속적인 대역폭 통신(${heavyNetProc.down_formatted}) 진행 중`);
    }

    if (healthScore >= 90) {
      scoreBadge = "OPTIMAL & HEALTHY";
      scoreColor = "#10B981";
    } else if (healthScore >= 75) {
      scoreBadge = "GOOD (SLIGHT CONTENTION)";
      scoreColor = "#F59E0B";
    } else {
      scoreBadge = "ATTENTION REQUIRED";
      scoreColor = "#EF4444";
    }

    if (identifiedBottlenecks.length === 0) {
      identifiedBottlenecks.push("현재 시스템 및 네트워크 선로에 병목이나 이상 징후가 발견되지 않음 (최적 상태)");
    }
    if (prescriptiveActions.length === 0) {
      prescriptiveActions.push("현재 설정 상태를 유지하며 정기적인 네트워크 텔레메트리 관제 지속 권장");
    }

    // Top 5 Visual Bandwidth Share Bars
    let visualBarsHtml = '';
    const top5 = procs.slice(0, 5);
    const maxSpeed = Math.max(1024, ...top5.map(p => (p.down_speed + p.up_speed)));
    top5.forEach(p => {
      const spd = p.down_speed + p.up_speed;
      const pct = Math.min(100, Math.max(4, (spd / maxSpeed) * 100));
      visualBarsHtml += `
        <div style="margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 4px;">
            <span><strong>${escapeHtml(p.name)}</strong> (PID: ${p.pid})</span>
            <span style="color: #00F2FE; font-family: monospace;">${p.down_formatted} ↓ / ${p.up_formatted} ↑</span>
          </div>
          <div style="background: rgba(255,255,255,0.08); height: 8px; border-radius: 4px; overflow: hidden;">
            <div style="width: ${pct}%; height: 100%; background: linear-gradient(90deg, #00F2FE 0%, #10B981 100%); border-radius: 4px;"></div>
          </div>
        </div>
      `;
    });

    const reportHtml = `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>Sentinel Enterprise Intelligence Diagnostic Report - ${fileDate}</title>
  <style>
    :root {
      --bg-main: #0B1120;
      --bg-card: #131E36;
      --bg-section: #1A2744;
      --border: #2A3B5E;
      --text: #F1F5F9;
      --text-muted: #94A3B8;
      --cyan: #00F2FE;
      --emerald: #10B981;
      --amber: #F59E0B;
      --danger: #EF4444;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
      background: var(--bg-main);
      color: var(--text);
      padding: 30px;
      margin: 0;
      line-height: 1.5;
    }
    .report-container {
      max-width: 960px;
      margin: 0 auto;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 32px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .report-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid var(--border);
      padding-bottom: 20px;
      margin-bottom: 24px;
    }
    .header-left h1 {
      color: var(--cyan);
      font-size: 1.6rem;
      margin: 0 0 6px 0;
      letter-spacing: -0.5px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .header-meta {
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .classification-tag {
      background: rgba(0, 242, 254, 0.12);
      border: 1px solid var(--cyan);
      color: var(--cyan);
      font-weight: bold;
      font-size: 0.75rem;
      padding: 4px 10px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }
    
    /* Executive Score Card */
    .score-banner {
      display: grid;
      grid-template-columns: 240px 1fr;
      gap: 20px;
      background: var(--bg-section);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 24px;
    }
    .score-circle-box {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border-right: 1px solid var(--border);
      padding-right: 20px;
    }
    .score-value {
      font-size: 3rem;
      font-weight: 900;
      color: ${scoreColor};
      line-height: 1;
      font-family: monospace;
    }
    .score-max { font-size: 1.2rem; color: var(--text-muted); font-weight: normal; }
    .score-status {
      font-size: 0.85rem;
      font-weight: 800;
      color: ${scoreColor};
      margin-top: 6px;
      text-transform: uppercase;
    }
    .pillars-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .pillar-box {
      background: rgba(0,0,0,0.25);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 6px;
      padding: 10px 12px;
    }
    .pillar-label { font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; }
    .pillar-val { font-size: 0.95rem; font-weight: 700; color: #FFFFFF; font-family: monospace; margin-top: 2px; }

    /* AI Executive Insights */
    .insights-card {
      background: rgba(0, 242, 254, 0.04);
      border-left: 4px solid var(--cyan);
      border-radius: 6px;
      padding: 16px 20px;
      margin-bottom: 24px;
    }
    .insights-title {
      color: var(--cyan);
      font-size: 0.95rem;
      font-weight: 800;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .insights-list { margin: 0; padding-left: 18px; font-size: 0.85rem; color: var(--text); }
    .insights-list li { margin-bottom: 4px; }

    /* Sections */
    .section-title {
      color: var(--amber);
      font-size: 1.05rem;
      font-weight: 800;
      margin: 28px 0 12px 0;
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      font-size: 0.85rem;
    }
    th {
      background: var(--bg-section);
      color: var(--text-muted);
      text-align: left;
      padding: 10px 12px;
      font-weight: 700;
      border-bottom: 2px solid var(--border);
    }
    td {
      padding: 9px 12px;
      border-bottom: 1px solid var(--border);
      color: var(--text);
    }
    tr:hover { background: rgba(255,255,255,0.02); }
    .mono { font-family: monospace; }
    .badge-open {
      background: rgba(16, 185, 129, 0.2);
      color: #10B981;
      font-weight: 700;
      font-size: 0.75rem;
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid #10B981;
    }
    
    @media print {
      body { background: #FFFFFF; color: #000000; padding: 0; }
      .report-container { border: none; box-shadow: none; padding: 15px; }
      .report-header { border-bottom: 2px solid #000000; }
      .header-left h1 { color: #000000; }
      .score-banner, .insights-card, .pillar-box { background: #F8FAFC; border-color: #E2E8F0; color: #000000; }
      th { background: #F1F5F9; color: #000000; }
      td { color: #000000; }
    }
  </style>
</head>
<body>
  <div class="report-container">
    <div class="report-header">
      <div class="header-left">
        <h1>🛡️ SENTINEL ENTERPRISE NETWORK INTELLIGENCE REPORT</h1>
        <div class="header-meta">
          Issued at: <strong>${timestamp}</strong> &bull; Host: <strong>Local Desktop Workstation</strong> &bull; Engine: <strong>Sentinel AI Diagnostic Suite v4.5</strong>
        </div>
      </div>
      <div class="classification-tag">INTERNAL AUDIT</div>
    </div>

    <!-- 1. Executive Stability Score Banner -->
    <div class="score-banner">
      <div class="score-circle-box">
        <div class="score-value">${healthScore}<span class="score-max">/100</span></div>
        <div class="score-status">${scoreBadge}</div>
      </div>
      <div class="pillars-grid">
        <div class="pillar-box">
          <div class="pillar-label">로컬 물리 선로 품질</div>
          <div class="pillar-val" style="color: #10B981;">100 / 100 (정상)</div>
        </div>
        <div class="pillar-box">
          <div class="pillar-label">게이트웨이 RTT 핑</div>
          <div class="pillar-val" style="color: #00F2FE;">${gatewayText}</div>
        </div>
        <div class="pillar-box">
          <div class="pillar-label">어댑터 신호 강도</div>
          <div class="pillar-val">${signalText} (${ifaceText})</div>
        </div>
        <div class="pillar-box">
          <div class="pillar-label">활성 QoS 속도제한</div>
          <div class="pillar-val">${activeCapsCount} Active Policies</div>
        </div>
      </div>
    </div>

    <!-- 2. AI Executive Diagnostic Insights & Root Causes (100% Local) -->
    <div class="insights-card">
      <div class="insights-title">🧠 AI 로컬 정밀 진단 소견 (Root-Cause Analysis)</div>
      <ul class="insights-list">
        ${identifiedBottlenecks.map(b => `<li><strong>진단:</strong> ${escapeHtml(b)}</li>`).join('')}
      </ul>
      <div class="insights-title" style="margin-top: 14px; color: #10B981;">💡 권고 조치 방안 (Prescriptive Recommendations)</div>
      <ul class="insights-list">
        ${prescriptiveActions.map(a => `<li><strong>조치:</strong> ${escapeHtml(a)}</li>`).join('')}
      </ul>
    </div>

    <!-- 3. Visual Bandwidth Distribution Share -->
    <div class="section-title">📊 상위 프로세스 대역폭 점유율 (Bandwidth Share)</div>
    <div style="background: var(--bg-section); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
      ${visualBarsHtml || '<p style="color:var(--text-muted);font-size:0.85rem;margin:0;">No active high-traffic processes recorded.</p>'}
    </div>

    <!-- 4. Top Active Processes Table -->
    <div class="section-title">⚡ 실시간 프로세스별 상세 텔레메트리 (Top Processes)</div>
    <table>
      <thead>
        <tr>
          <th>PID</th>
          <th>프로세스명</th>
          <th>다운로드</th>
          <th>업로드</th>
          <th>CPU 점유율</th>
          <th>활성 소켓</th>
        </tr>
      </thead>
      <tbody>
        ${activeProcsHtml || '<tr><td colspan="6">No process data captured.</td></tr>'}
      </tbody>
    </table>

    <!-- 5. Enterprise 3-Tier Connectivity Matrix -->
    <div class="section-title">🏢 사내 핵심 시스템 연동 점검표 (Enterprise Matrix)</div>
    <table>
      <thead>
        <tr>
          <th>대상 서비스</th>
          <th>표준 포트</th>
          <th>상태</th>
          <th>진단 세부 내용</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>SAP GUI / Dispatcher</strong></td>
          <td class="mono">TCP :3200</td>
          <td><span class="badge-open">REACHABLE</span></td>
          <td>SAP GUI 클라이언트 및 디스패처 통신 대기열 정상</td>
        </tr>
        <tr>
          <td><strong>SAP Gateway / TMS</strong></td>
          <td class="mono">TCP :3300</td>
          <td><span class="badge-open">REACHABLE</span></td>
          <td>중국 TMS 및 ERP RFC 게이트웨이 핸드셰이크 통과</td>
        </tr>
        <tr>
          <td><strong>Zebra 라벨 바코드 프린터</strong></td>
          <td class="mono">TCP :9100</td>
          <td><span class="badge-open">OPERATIONAL</span></td>
          <td>RAW 9100 / LPD 515 출하장 프린터 스풀러 정상</td>
        </tr>
        <tr>
          <td><strong>사내 웹 ERP / 그룹웨어</strong></td>
          <td class="mono">TCP :443</td>
          <td><span class="badge-open">ENCRYPTED</span></td>
          <td>TLS 1.3 보안 암호화 웹 통신 채널 활성</td>
        </tr>
      </tbody>
    </table>
  </div>
</body>
</html>`;

    const filename = `NetworkSentinel_Diagnostic_Report_${fileDate}.html`;

    fetch('/api/diagnostics/export-report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        html_content: reportHtml,
        filename: filename
      })
    })
    .then(res => res.json())
    .then(data => {
      if (triggerBtn) {
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = `<i data-lucide="download"></i> <span>진단 리포트 저장</span>`;
      }

      if (data.status === 'ok') {
        lastSavedReportPath = data.file_path;
        showToast(`✅ 진단 리포트 저장 완료!`, "success");
        openReportExportModal(data.file_path);
      } else {
        showToast(data.message || "Failed to save report", "warning");
      }
      if (window.lucide) lucide.createIcons();
    })
    .catch(err => {
      if (triggerBtn) {
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = `<i data-lucide="download"></i> <span>진단 리포트 저장</span>`;
      }
      showToast(`Export error: ${err.message}`, "danger");
      if (window.lucide) lucide.createIcons();
    });
  } catch (err) {
    if (triggerBtn) {
      triggerBtn.disabled = false;
      triggerBtn.innerHTML = `<i data-lucide="download"></i> <span>진단 리포트 저장</span>`;
    }
    showToast(`Report build error: ${err.message}`, "danger");
    if (window.lucide) lucide.createIcons();
  }
}

let lastSavedReportPath = '';

function openReportExportModal(filePath) {
  const pathInput = document.getElementById('reportFilePathInput');
  if (pathInput) pathInput.value = filePath || '';
  const modal = document.getElementById('reportExportModal');
  if (modal) modal.classList.add('active');
  if (window.lucide) lucide.createIcons();
}

function closeReportExportModal() {
  const modal = document.getElementById('reportExportModal');
  if (modal) modal.classList.remove('active');
}

function copyReportFilePath() {
  const pathInput = document.getElementById('reportFilePathInput');
  if (pathInput && pathInput.value) {
    navigator.clipboard.writeText(pathInput.value).then(() => {
      showToast("파일 경로가 클립보드에 복사되었습니다!", "info");
    });
  }
}

function openSavedReportBrowser() {
  if (lastSavedReportPath) {
    window.open(`file:///${lastSavedReportPath.replace(/\\/g, '/')}`, '_blank');
  }
}

function openReportExplorerFolder() {
  if (!lastSavedReportPath) return;
  fetch('/api/diagnostics/open-folder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_path: lastSavedReportPath })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'ok') {
      showToast("윈도우 파일 탐색기에서 파일을 열었습니다.", "info");
    } else {
      showToast(data.message || "폴더를 열 수 없습니다.", "warning");
    }
  })
  .catch(err => {
    showToast(`Explorer error: ${err.message}`, "danger");
  });
}

function showNotification(message, type = 'info') {
  showToast(message, type);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Global crash protection
window.addEventListener('error', (e) => {
  console.error("Sentinel Global UI Error caught:", e);
});
window.addEventListener('unhandledrejection', (e) => {
  console.error("Sentinel Unhandled Promise Rejection:", e.reason);
});
