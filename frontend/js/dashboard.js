/* dashboard.js — KPI, Charts, Table, Crawl, Analyze */

let currentSessionId = null;
let allProducts = [];
let filteredProducts = [];
let currentPage = 1;
const PAGE_SIZE = 20;
let sortKey = 'price';
let sortAsc = false;
let charts = {};
let currentUnit = "đ";

// ── Chart colour palette ──────────────────────────────────────────────────
const PALETTE = [
  '#7c3aed','#2563eb','#06b6d4','#10b981',
  '#f59e0b','#ef4444','#8b5cf6','#3b82f6',
  '#14b8a6','#f97316','#ec4899','#84cc16',
];

Chart.defaults.color = '#cbd5e1';
Chart.defaults.borderColor = 'rgba(255,255,255,0.07)';
Chart.defaults.font.family = 'Inter';

const GRID = { color: 'rgba(255,255,255,0.05)', borderColor: 'transparent' };
const TOOLTIP = {
  backgroundColor: '#1a1a3e',
  borderColor: 'rgba(124,58,237,0.5)',
  borderWidth: 1,
  titleFont: { family: 'Inter', size: 12 },
  bodyFont:  { family: 'Inter', size: 11 },
  padding: 10,
};

function fmtTick(v) {
  if (v >= 1e6) return (v/1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v/1e3).toFixed(1) + 'K';
  return Number.isInteger(v) ? v : v.toFixed(1);
}

function truncLabel(s, max = 14) {
  return String(s).length > max ? String(s).slice(0, max) + '…' : String(s);
}

// ── Charts Grid ─────────────────────────────────────────────────────────────
function renderCharts(cd) {
  buildBar(cd.bar_category);
  buildPie(cd.pie_distribution);
  buildHBar(cd.hbar_avg_price);
  buildScatter(cd.scatter_price_rating);
  if (cd.line_trend && cd.line_trend.labels && cd.line_trend.labels.length >= 2) {
    buildLine(cd.line_trend);
  }
  document.getElementById('chartsGrid').style.display = '';
}

function buildBar(cd) {
  destroyChart('chartBar');
  if (!cd || !cd.labels || !cd.labels.length) return;
  charts['chartBar'] = new Chart(document.getElementById('chartBar'), {
    type: 'bar',
    data: {
      labels: cd.labels.map(l => truncLabel(l, 12)),
      datasets: [{
        label: 'Số sản phẩm',
        data: cd.data,
        backgroundColor: PALETTE.map(c => c + 'bb'),
        borderColor: PALETTE,
        borderWidth: 1,
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 900, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: { ...TOOLTIP, callbacks: {
          title: (items) => cd.labels[items[0].dataIndex],  // Full label in tooltip
          label:  (item) => ` ${item.raw.toLocaleString()} sản phẩm`,
        }},
      },
      scales: {
        x: {
          grid: GRID,
          ticks: {
            maxRotation: 40, minRotation: 0,
            font: { size: 10 },
            color: '#cbd5e1',
          },
        },
        y: {
          grid: GRID,
          ticks: { callback: v => fmtTick(v), font: { size: 10 } },
          beginAtZero: true,
        },
      },
    },
  });
}

function buildPie(cd) {
  destroyChart('chartPie');
  if (!cd || !cd.labels || !cd.labels.length) return;
  charts['chartPie'] = new Chart(document.getElementById('chartPie'), {
    type: 'doughnut',
    data: {
      labels: cd.labels,
      datasets: [{
        data: cd.data,
        backgroundColor: PALETTE,
        borderColor: '#07071a',
        borderWidth: 3,
        hoverOffset: 12,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      layout: { padding: 10 },
      animation: { duration: 900, animateRotate: true },
      cutout: '60%',
      plugins: {
        legend: {
          position: 'right',
          align: 'center',
          labels: {
            color: '#ffffff',
            font: { size: 11, weight: '600' },
            padding: 20,
            boxWidth: 12,
            usePointStyle: true,
            generateLabels: (chart) => {
              const dataset = chart.data.datasets[0];
              const total = dataset.data.reduce((a, b) => a + b, 0);
              return chart.data.labels.map((lbl, i) => {
                const val = dataset.data[i];
                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                return {
                  text: `${truncLabel(lbl, 15)} (${pct}%)`,
                  fillStyle: dataset.backgroundColor[i],
                  strokeStyle: dataset.backgroundColor[i],
                  lineWidth: 0,
                  index: i
                };
              });
            },
          },
        },
      },
    },
  });
}

function buildHBar(cd) {
  destroyChart('chartHBar');
  if (!cd || !cd.labels || !cd.labels.length) return;
  charts['chartHBar'] = new Chart(document.getElementById('chartHBar'), {
    type: 'bar',
    data: {
      labels: cd.labels.map(l => truncLabel(l, 13)),
      datasets: [{
        label: 'Giá TB',
        data: cd.data,
        backgroundColor: PALETTE.map(c => c + 'bb'),
        borderColor: PALETTE,
        borderWidth: 1,
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 900 },
      plugins: {
        legend: { display: false },
        tooltip: { ...TOOLTIP, callbacks: {
          title: (items) => cd.labels[items[0].dataIndex],
          label:  (item) => ` Giá TB: ${fmtPrice(item.raw)}`,
        }},
      },
      scales: {
        x: {
          grid: GRID,
          ticks: { callback: v => fmtTick(v), font: { size: 10 } },
          beginAtZero: true,
        },
        y: {
          grid: { display: false },
          ticks: { font: { size: 10 }, color: '#e2e8f0' },
        },
      },
    },
  });
}

function buildScatter(pts) {
  destroyChart('chartScatter');
  if (!pts || !pts.length) return;
  charts['chartScatter'] = new Chart(document.getElementById('chartScatter'), {
    type: 'scatter',
    data: { datasets: [{
      label: 'Giá vs Điểm',
      data: pts,
      backgroundColor: '#7c3aed88',
      borderColor:     '#7c3aedcc',
      pointRadius:     4,
      pointHoverRadius: 7,
    }]},
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 700 },
      plugins: {
        legend: { display: false },
        tooltip: { ...TOOLTIP, callbacks: {
          label: (item) => ` Giá: ${fmtPrice(item.parsed.x)}  |  Điểm/Rating: ${item.parsed.y}`,
        }},
      },
      scales: {
        x: { grid: GRID, title: { display: true, text: 'Giá', color: '#cbd5e1', font: { size: 10 } }, ticks: { callback: v => fmtTick(v), font: { size: 10 }, color: '#cbd5e1' } },
        y: { grid: GRID, title: { display: true, text: 'Điểm / Rating', color: '#cbd5e1', font: { size: 10 } }, ticks: { font: { size: 10 }, color: '#cbd5e1' } },
      },
    },
  });
}

function buildLine(cd) {
  destroyChart('chartLine');
  if (!cd || !cd.labels || !cd.labels.length) return;
  const lineCanvas = document.getElementById('chartLine');
  if (!lineCanvas) return;
  charts['chartLine'] = new Chart(lineCanvas, {
    type: 'line',
    data: {
      labels: cd.labels.map(l => truncLabel(l, 12)),
      datasets: [{
        label: 'Giá TB theo nhóm',
        data: cd.data,
        borderColor: '#06b6d4',
        backgroundColor: 'rgba(6,182,212,0.12)',
        borderWidth: 2.5,
        pointBackgroundColor: '#06b6d4',
        pointRadius: 5,
        pointHoverRadius: 8,
        tension: 0.35,
        fill: true,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 900 },
      plugins: {
        legend: { display: false },
        tooltip: { ...TOOLTIP, callbacks: {
          title: (items) => cd.labels[items[0].dataIndex],
          label:  (item) => ` Giá TB: ${fmtPrice(item.raw)}`,
        }},
      },
      scales: {
        x: { grid: GRID, ticks: { maxRotation: 40, font: { size: 10 }, color: '#cbd5e1' } },
        y: { grid: GRID, ticks: { callback: v => fmtTick(v), font: { size: 10 }, color: '#cbd5e1' }, beginAtZero: false },
      },
    },
  });
}


async function doCrawl() {
  let url = document.getElementById('urlInput').value.trim();
  if (!url) { toast('Vui lòng nhập URL!', 'error'); return; }
  if (!url.startsWith('http')) url = 'https://' + url;

  showLoading('🕷️ Đang crawl dữ liệu...');
  try {
    const data = await apiPost('/api/crawl/', { url });
    currentSessionId = data.session_id;
    toast(`✅ ${data.message}`, 'success');

    document.getElementById('currentSite').textContent = `— ${data.site_name}`;
    document.getElementById('emptyState').style.display = 'none';

    await refreshSessions();
    await loadProducts();
    await doAnalyze();
  } catch (e) {
    toast('❌ ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

function setDemo(url) {
  document.getElementById('urlInput').value = url;
  doCrawl();
}

// ── Upload ────────────────────────────────────────────────────────────────
async function doUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  showLoading('📤 Đang tải lên và xử lý file...');
  try {
    const response = await fetch('/api/upload/file', {
      method: 'POST',
      body: formData
    });
    const data = await response.json();
    
    if (data.success) {
      currentSessionId = data.session_id;
      toast(`✅ ${data.message}`, 'success');
      
      document.getElementById('currentSite').textContent = `— ${file.name}`;
      document.getElementById('emptyState').style.display = 'none';

      await refreshSessions();
      await loadProducts();
      await doAnalyze();
    } else {
      throw new Error(data.detail || 'Lỗi không xác định');
    }
  } catch (e) {
    toast('❌ Lỗi tải file: ' + e.message, 'error');
  } finally {
    hideLoading();
    event.target.value = ''; // Reset input
  }
}

// ── Analyze ───────────────────────────────────────────────────────────────
async function doAnalyze() {
  const qs = currentSessionId ? `?session_id=${currentSessionId}` : '';
  showLoading('📊 Đang phân tích...');
  try {
    const data = await apiGet('/api/analyze/' + qs);
    renderKPI(data.summary);
    renderInsights(data.insights);
    renderCharts(data.chart_data);
    showDashboard();
  } catch (e) {
    toast('⚠️ ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

// ── KPI Cards ─────────────────────────────────────────────────────────────
function renderKPI(s) {
  currentUnit = s.unit || "đ";
  document.getElementById('kpiTotal').textContent  = s.total_items.toLocaleString();
  document.getElementById('kpiAvg').textContent    = fmtPrice(s.avg_price);
  document.getElementById('kpiMax').textContent    = fmtPrice(s.max_price);
  document.getElementById('kpiMin').textContent    = fmtPrice(s.min_price);
  document.getElementById('kpiCats').textContent   = s.categories;
  document.getElementById('kpiRating').textContent = s.avg_rating ? s.avg_rating.toFixed(1) + '/5' : '—';
}

// ── Insights ──────────────────────────────────────────────────────────────
function renderInsights(insights) {
  const panel = document.getElementById('insightsPanel');
  document.getElementById('insightCount').textContent = insights.length;
  panel.innerHTML = insights.map(i =>
    `<div class="insight-item">${i}</div>`
  ).join('');
  document.getElementById('insightsSection').style.display = '';
}

// ── Table ─────────────────────────────────────────────────────────────────

async function loadProducts() {
  const qs = currentSessionId ? `?session_id=${currentSessionId}&limit=500` : '?limit=500';
  try {
    const data = await apiGet('/api/data/products' + qs);
    allProducts = data.products || [];
    filteredProducts = [...allProducts];
    document.getElementById('tableCount').textContent = allProducts.length;
    currentPage = 1;
    renderTable();
    document.getElementById('tableCard').style.display = '';
  } catch (e) {
    console.warn('loadProducts:', e);
  }
}

function filterTable() {
  const q = document.getElementById('tableSearch').value.toLowerCase();
  filteredProducts = allProducts.filter(p =>
    (p.name || '').toLowerCase().includes(q) ||
    (p.category || '').toLowerCase().includes(q)
  );
  currentPage = 1;
  renderTable();
}

function sortTable(key) {
  if (sortKey === key) sortAsc = !sortAsc;
  else { sortKey = key; sortAsc = false; }
  filteredProducts.sort((a, b) => {
    const av = a[key] || 0, bv = b[key] || 0;
    return sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });
  renderTable();
}

function renderTable() {
  const tbody = document.getElementById('tableBody');
  const start = (currentPage - 1) * PAGE_SIZE;
  const page  = filteredProducts.slice(start, start + PAGE_SIZE);

  tbody.innerHTML = page.map((p, i) => `
    <tr>
      <td class="name-cell" title="${p.name || ''}">${start + i + 1}. ${p.name || '—'}</td>
      <td class="price-cell">${p.price_raw || fmtPrice(p.price)}</td>
      <td><span class="cat-badge">${p.category || '—'}</span></td>
      <td class="stars" title="${p.rating || 0}/5">${stars(p.rating)}</td>
      <td>${p.url ? `<a href="${p.url}" target="_blank" rel="noopener noreferrer" style="color:var(--accent);font-size:0.75rem">🔗 Link</a>` : '—'}</td>
    </tr>
  `).join('');

  renderPagination();
}

function renderPagination() {
  const total = Math.ceil(filteredProducts.length / PAGE_SIZE);
  const pg = document.getElementById('pagination');
  if (total <= 1) { pg.innerHTML = ''; return; }

  let html = `<button class="page-btn" onclick="goPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>‹</button>`;
  for (let i = 1; i <= Math.min(total, 7); i++) {
    html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`;
  }
  if (total > 7) html += `<span style="color:var(--text3)">… ${total}</span>`;
  html += `<button class="page-btn" onclick="goPage(${currentPage + 1})" ${currentPage === total ? 'disabled' : ''}>›</button>`;
  pg.innerHTML = html;
}

function goPage(n) {
  const total = Math.ceil(filteredProducts.length / PAGE_SIZE);
  if (n < 1 || n > total) return;
  currentPage = n;
  renderTable();
}

// ── Sessions sidebar ──────────────────────────────────────────────────────
async function refreshSessions() {
  try {
    const sessions = await apiGet('/api/crawl/sessions');
    const list = document.getElementById('sessionList');
    if (!sessions.length) {
      list.innerHTML = `<div style="padding:12px;color:var(--text3);font-size:0.8rem;">Chưa có session nào</div>`;
      return;
    }
    list.innerHTML = sessions.map(s => `
      <div class="session-item ${s.id === currentSessionId ? 'active' : ''}" onclick="selectSession(${s.id}, '${s.site_name}')">
        <div class="s-name">🌐 ${s.site_name}</div>
        <div class="s-meta">${new Date(s.created_at).toLocaleString('vi-VN')}</div>
        <span class="s-badge">${s.total_items} items</span>
      </div>
    `).join('');
  } catch (e) { console.warn(e); }
}

async function selectSession(id, name) {
  currentSessionId = id;
  document.getElementById('currentSite').textContent = `— ${name}`;
  document.getElementById('emptyState').style.display = 'none';
  await loadProducts();
  await doAnalyze();
  await refreshSessions();
}

// ── Misc ──────────────────────────────────────────────────────────────────
function showDashboard() {
  document.getElementById('kpiGrid').style.display = '';
}

function exportCSV() {
  const qs = currentSessionId ? `?session_id=${currentSessionId}` : '';
  window.open(`/api/analyze/export/csv${qs}`, '_blank');
}

function openDocs() { window.open('/api/docs', '_blank'); }

async function clearAll() {
  if (!currentSessionId) { toast('Chưa có session nào để xóa', 'error'); return; }
  if (!confirm(`Xóa session #${currentSessionId}?`)) return;
  try {
    await fetch(`/api/crawl/sessions/${currentSessionId}`, { method: 'DELETE' });
    toast('✅ Đã xóa session', 'success');
    currentSessionId = null;
    allProducts = [];
    filteredProducts = [];
    document.getElementById('emptyState').style.display = '';
    document.getElementById('kpiGrid').style.display = 'none';
    document.getElementById('insightsSection').style.display = 'none';
    document.getElementById('chartsGrid').style.display = 'none';
    document.getElementById('tableCard').style.display = 'none';
    await refreshSessions();
  } catch (e) { toast('❌ ' + e.message, 'error'); }
}

// ── Init ──────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  await refreshSessions();
  // Auto-load last session if any
  try {
    const sessions = await apiGet('/api/crawl/sessions');
    if (sessions.length) {
      const last = sessions[0];
      await selectSession(last.id, last.site_name);
    }
  } catch (e) {}
});

// ── Helpers ───────────────────────────────────────────────────────────────
function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function fmtPrice(v) {
  if (v === undefined || v === null || isNaN(v)) return '—';
  
  // Format with the detected unit
  if (currentUnit === "đ" || currentUnit === "VND") {
      return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(v).replace("₫", "đ");
  }
  
  // For other currencies (£, $, etc.)
  try {
      const symbols = { "£": "GBP", "$": "USD", "€": "EUR" };
      const curCode = symbols[currentUnit] || "USD";
      if (symbols[currentUnit]) {
          return new Intl.NumberFormat('en-GB', { style: 'currency', currency: curCode }).format(v);
      }
  } catch(e) {}
  
  return `${currentUnit}${v.toLocaleString()}`;
}

function stars(r) {
  if (!r) return '☆☆☆☆☆';
  const full = Math.floor(r);
  const half = r % 1 >= 0.5 ? 1 : 0;
  return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(Math.max(0, 5 - Math.ceil(r)));
}

function toast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return console.log(msg);
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function showLoading(text) {
  const el = document.getElementById('loadingOverlay');
  if (el) {
    el.style.display = 'flex';
    document.getElementById('loadingText').textContent = text;
  }
}
function hideLoading() {
  const el = document.getElementById('loadingOverlay');
  if (el) el.style.display = 'none';
}
