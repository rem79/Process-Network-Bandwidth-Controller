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
