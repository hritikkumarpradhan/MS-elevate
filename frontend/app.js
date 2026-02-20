/**
 * app.js — Mental Health Trend Monitor
 * Frontend logic: fetches data from Flask backend, renders charts and tables.
 */

const API_BASE = "";  // Same origin; Flask serves both frontend and API

// ─── Region color palette (matches chart_generator.py) ───────────────────────
const REGION_COLORS = [
  "#00BFA5", "#1B8ECA", "#4DD0C4",
  "#64B5F6", "#80CBC4", "#42A5F5"
];

// ─── App State ────────────────────────────────────────────────────────────────
const state = {
  regions: [],
  selectedRegions: new Set(),
  year: 2024,
  chartType: "trend",
  resourceData: [],
  sortCol: "allocation_score",
  sortDir: "desc",
  searchQuery: "",
};

// ─── DOM References ───────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ═════════════════════════════════════════════════════════════════════════════
//  INITIALIZATION
// ═════════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", async () => {
  updateTimestamp();
  setInterval(updateTimestamp, 60000);

  await initRegions();
  await loadStats();
  loadChart();
  loadResourceTable();

  // Event listeners
  $("btn-refresh").addEventListener("click", onRefresh);
  $("btn-export").addEventListener("click", onExport);
  $("btn-select-all").addEventListener("click", selectAllRegions);
  $("btn-clear-all").addEventListener("click", clearAllRegions);
  $("btn-dl-chart").addEventListener("click", downloadChart);
  $("btn-dl-table").addEventListener("click", exportCSV);
  $("table-search").addEventListener("input", onSearch);
  $("year-select").addEventListener("change", onYearChange);

  // Chart tabs
  document.querySelectorAll(".chart-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".chart-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      state.chartType = tab.dataset.type;
      loadChart();
    });
  });

  // Table sort headers
  document.querySelectorAll(".sort-col").forEach(th => {
    th.addEventListener("click", () => onSort(th.dataset.sort));
  });
});

// ═════════════════════════════════════════════════════════════════════════════
//  REGIONS
// ═════════════════════════════════════════════════════════════════════════════

async function initRegions() {
  try {
    const res = await fetch(`${API_BASE}/api/regions`);
    const data = await res.json();
    state.regions = data.regions;

    // Select all by default
    state.regions.forEach(r => state.selectedRegions.add(r));

    renderRegionList();
  } catch (err) {
    console.error("Failed to load regions:", err);
    showApiError("Could not connect to the backend. Ensure the Flask server is running on port 5000.");
  }
}

function renderRegionList(scores = {}) {
  const list = $("region-list");
  list.innerHTML = "";

  state.regions.forEach((region, i) => {
    const isActive = state.selectedRegions.has(region);
    const score = scores[region] != null ? `${scores[region].toFixed(1)}` : "";

    const item = document.createElement("div");
    item.className = `region-item ${isActive ? "active" : ""}`;
    item.dataset.region = region;
    item.innerHTML = `
      <div class="region-checkbox"></div>
      <div class="region-color-dot" style="background:${REGION_COLORS[i % REGION_COLORS.length]}"></div>
      <span class="region-name">${region}</span>
      <span class="region-score">${score}</span>
    `;
    item.addEventListener("click", () => toggleRegion(region, item));
    list.appendChild(item);
  });
}

function toggleRegion(region, el) {
  if (state.selectedRegions.has(region)) {
    if (state.selectedRegions.size <= 1) return;  // Keep at least one
    state.selectedRegions.delete(region);
    el.classList.remove("active");
  } else {
    state.selectedRegions.add(region);
    el.classList.add("active");
  }
  loadChart();
  loadResourceTable();
}

function selectAllRegions() {
  state.regions.forEach(r => state.selectedRegions.add(r));
  document.querySelectorAll(".region-item").forEach(el => el.classList.add("active"));
  loadChart();
  loadResourceTable();
}

function clearAllRegions() {
  // Keep first region selected
  state.selectedRegions.clear();
  state.selectedRegions.add(state.regions[0]);
  document.querySelectorAll(".region-item").forEach((el, i) => {
    el.classList.toggle("active", i === 0);
  });
  loadChart();
  loadResourceTable();
}

// ═════════════════════════════════════════════════════════════════════════════
//  STATS
// ═════════════════════════════════════════════════════════════════════════════

async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/api/stats?year=${state.year}`);
    const data = await res.json();

    $("stat-national").textContent = `${data.national_avg_sentiment.toFixed(1)}/100`;
    $("stat-best").textContent = data.highest_region;
    $("stat-worst").textContent = data.lowest_region;
    $("stat-samples").textContent = data.total_samples_processed.toLocaleString();

    // Update stat cards
    $("scard-regions-val").textContent = data.regions_monitored;
    $("scard-sentiment-val").textContent = `${data.national_avg_sentiment.toFixed(1)}`;
    $("scard-samples-val").textContent = data.total_samples_processed.toLocaleString();

    const scoreDiff = data.highest_score - data.lowest_score;
    $("scard-trend-val").textContent = scoreDiff > 10 ? "Mixed" : "Stable";

    // -------------------------------
    // Load per-region scores for sidebar using /api/sentiment?region=all
    // -------------------------------
    const allRes = await fetch(`${API_BASE}/api/sentiment?region=all&year=${state.year}`);
    const allData = await allRes.json();
    const scores = {};
    Object.entries(allData.regions).forEach(([region, months]) => {
      if (months && months.length > 0) {
        const avg = months.reduce((s, m) => s + m.avg_sentiment, 0) / months.length;
        scores[region] = avg;
      }
    });
    renderRegionList(scores);

  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

// ═════════════════════════════════════════════════════════════════════════════
//  CHART
// ═════════════════════════════════════════════════════════════════════════════

async function loadChart() {
  const loading = $("chart-loading");
  const img = $("chart-img");

  // Show spinner, hide image
  loading.style.display = "flex";
  img.style.display = "none";
  img.src = "";
  $("chart-pipeline-info").textContent = "Generating via Matplotlib + spaCy + NLTK VADER…";

  try {
    let url;
    if (state.chartType === "comparison") {
      url = `${API_BASE}/api/chart?type=comparison&year=${state.year}&_t=${Date.now()}`;
    } else {
      // Use plain comma-separated string WITHOUT encodeURIComponent — 
      // the server splits on comma and spaces are fine in query strings
      const regionParam = Array.from(state.selectedRegions).join(",");
      url = `${API_BASE}/api/chart?region=${regionParam}&year=${state.year}&type=trend&_t=${Date.now()}`;
    }

    // ─── KEY FIX: set img.src directly to the API URL ───
    // The browser fetches and renders it natively — no blob() needed.
    img.onload = () => {
      loading.style.display = "none";
      img.style.display = "block";
      const regionNames = state.chartType === "comparison"
        ? "All Regions"
        : Array.from(state.selectedRegions).join(", ");
      $("chart-pipeline-info").textContent =
        `Generated server-side with Matplotlib • Regions: ${regionNames} • Year: ${state.year} • NLP: spaCy + NLTK VADER`;
      checkSpacyStatus();
    };

    img.onerror = () => {
      loading.innerHTML = `
        <div style="text-align:center;color:var(--red-500)">
          <p style="font-size:1.1rem;margin-bottom:.5rem">⚠️ Chart failed to load</p>
          <p style="font-size:.82rem;color:var(--text-muted)">Check server: <code>python backend/app.py</code></p>
        </div>`;
    };

    img.src = url;

  } catch (err) {
    loading.innerHTML = `
      <div style="text-align:center;color:var(--red-500);padding:2rem">
        <p style="font-size:1.2rem;margin-bottom:.5rem">⚠️ Chart generation failed</p>
        <p style="font-size:.85rem;color:var(--text-muted)">${err.message}</p>
      </div>`;
  }
}

function downloadChart() {
  const img = $("chart-img");
  if (!img.src || img.src === window.location.href) return;
  const a = document.createElement("a");
  a.href = img.src;
  a.download = `mental-health-trend-${state.year}.png`;
  a.click();
}

async function checkSpacyStatus() {
  try {
    const region = state.regions[0];
    if (!region) return;
    const res = await fetch(`${API_BASE}/api/sentiment?region=${encodeURIComponent(region)}&year=${state.year}`);
    const data = await res.json();
    const spacy = $("spacy-status");
    if (!spacy) return;
    if (data.spacy_available) {
      spacy.innerHTML = `<span class="status-dot active"></span>Active (en_core_web_sm)`;
      spacy.className = "comp-status active";
    } else {
      spacy.innerHTML = `<span class="status-dot"></span>Fallback mode (model not found)`;
      spacy.className = "comp-status";
    }
  } catch { }
}

// ═════════════════════════════════════════════════════════════════════════════
//  RESOURCE TABLE
// ═════════════════════════════════════════════════════════════════════════════

async function loadResourceTable() {
  const tbody = $("resources-tbody");
  tbody.innerHTML = `<tr><td colspan="8" class="table-loading"><div class="spinner small"></div> Loading resource data…</td></tr>`;

  try {
    // ─── KEY FIX: use plain comma join, not encodeURIComponent ───
    const regionParam = Array.from(state.selectedRegions).join(",");
    const url = `${API_BASE}/api/resources?region=${regionParam}&year=${state.year}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (!data.resources || data.resources.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="table-loading">No data returned for selected regions.</td></tr>`;
      return;
    }

    state.resourceData = data.resources;
    renderTable();

    // Totals in footer
    const totalsEl = $("table-totals");
    if (totalsEl) {
      totalsEl.innerHTML = `
        <span>Total counselors: <strong>${data.total_counselors_needed}</strong></span>
        <span>Total budget allocated: <strong>${data.total_budget_pct_allocated}%</strong></span>
      `;
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-loading" style="color:var(--red-500)">Failed to load resource data: ${err.message}</td></tr>`;
  }
}

function renderTable() {
  const tbody = $("resources-tbody");
  const query = state.searchQuery.toLowerCase().trim();

  let rows = [...state.resourceData];

  // Filter
  if (query) {
    rows = rows.filter(r => r.region.toLowerCase().includes(query));
  }

  // Sort
  rows.sort((a, b) => {
    const aVal = a[state.sortCol];
    const bVal = b[state.sortCol];
    const cmp = typeof aVal === "string"
      ? aVal.localeCompare(bVal)
      : (aVal - bVal);
    return state.sortDir === "asc" ? cmp : -cmp;
  });

  const countEl = $("table-row-count");
  if (countEl) countEl.textContent = `${rows.length} region${rows.length !== 1 ? "s" : ""}`;

  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="table-loading">No regions match your search.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map(row => {
    const sentColor = row.avg_sentiment >= 60
      ? "var(--teal-500)" : row.avg_sentiment >= 45
        ? "var(--amber-500)" : "var(--red-500)";

    const allocBarColor = row.allocation_score >= 75
      ? "var(--red-500)" : row.allocation_score >= 60
        ? "var(--amber-500)" : "var(--teal-500)";

    // Strip leading arrow from priority for badge class lookup
    const priorityClass = row.priority.replace(/^[↑↓]\s*/, "").split(" ")[0];

    const trendDisplay = row.trend === "improving"
      ? `<span class="trend-improving">↑ Improving</span>`
      : `<span class="trend-declining">↓ Declining</span>`;

    return `
      <tr>
        <td><strong>${row.region}</strong></td>
        <td>
          <div class="score-cell">
            <span style="color:${sentColor};font-weight:600;min-width:38px;font-variant-numeric:tabular-nums">${row.avg_sentiment.toFixed(1)}</span>
            <div class="score-bar-track">
              <div class="score-bar-fill" style="width:${row.avg_sentiment}%;background:${sentColor}"></div>
            </div>
          </div>
        </td>
        <td>${trendDisplay}</td>
        <td><span class="priority-badge priority-${priorityClass}">${row.priority}</span></td>
        <td>
          <div class="score-cell">
            <span style="font-weight:600;font-variant-numeric:tabular-nums;min-width:26px">${row.allocation_score}</span>
            <div class="score-bar-track">
              <div class="score-bar-fill" style="width:${row.allocation_score}%;background:${allocBarColor}"></div>
            </div>
          </div>
        </td>
        <td>${row.recommended_counselors}</td>
        <td>${row.active_programs}</td>
        <td><strong>${row.budget_allocation_pct}%</strong></td>
      </tr>`;
  }).join("");
}

function onSort(col) {
  if (state.sortCol === col) {
    state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
  } else {
    state.sortCol = col;
    state.sortDir = "desc";
  }

  document.querySelectorAll(".sort-col").forEach(th => {
    th.classList.remove("asc", "desc");
    if (th.dataset.sort === state.sortCol) {
      th.classList.add(state.sortDir);
    }
  });

  renderTable();
}

function onSearch(e) {
  state.searchQuery = e.target.value;
  renderTable();
}

// ═════════════════════════════════════════════════════════════════════════════
//  EXPORT CSV
// ═════════════════════════════════════════════════════════════════════════════

function exportCSV() {
  if (!state.resourceData.length) return;

  const headers = [
    "Region", "Avg Sentiment", "Trend", "Priority",
    "Allocation Score", "Counselors Needed", "Active Programs", "Budget %"
  ];
  const rows = state.resourceData.map(r => [
    r.region, r.avg_sentiment, r.trend, r.priority,
    r.allocation_score, r.recommended_counselors, r.active_programs, r.budget_allocation_pct
  ]);

  const csv = [headers, ...rows].map(row => row.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `resource-allocation-${state.year}.csv`;
  a.click();
}

// ═════════════════════════════════════════════════════════════════════════════
//  MISC EVENT HANDLERS
// ═════════════════════════════════════════════════════════════════════════════

function onRefresh() {
  const btn = $("btn-refresh");
  btn.style.opacity = "0.5";
  btn.disabled = true;
  Promise.all([loadStats(), loadChart(), loadResourceTable()])
    .finally(() => {
      btn.style.opacity = "1";
      btn.disabled = false;
    });
}

function onYearChange(e) {
  state.year = parseInt(e.target.value);
  loadStats();
  loadChart();
  loadResourceTable();
}

async function onExport() {
  const overlay = $("export-overlay");
  const progress = $("export-progress");
  overlay.style.display = "flex";
  progress.style.width = "0%";

  for (const pct of [15, 40, 65, 85, 98, 100]) {
    await delay(420);
    progress.style.width = pct + "%";
  }

  await delay(400);
  overlay.style.display = "none";

  // Download current chart as the "report"
  const img = $("chart-img");
  if (img && img.src && img.src !== window.location.href) {
    const a = document.createElement("a");
    a.href = img.src;
    a.download = `MH-TrendMonitor-Report-${state.year}.png`;
    a.click();
  }
}

function showApiError(msg) {
  const list = $("region-list");
  if (list) list.innerHTML = `<div style="color:var(--red-500);font-size:.8rem;padding:8px;line-height:1.5">${msg}</div>`;
}

function updateTimestamp() {
  const el = $("header-timestamp");
  if (!el) return;
  el.textContent = new Date().toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit"
  });
}

const delay = (ms) => new Promise(res => setTimeout(res, ms));
