/* ================================================================
   OpenClaw Investment Dashboard - Frontend Logic
   ================================================================ */
(function () {
  "use strict";

  const API = "";  // same origin
  const REFRESH_INTERVAL = 30000; // 30s

  // ---------------------------------------------------------------
  // State
  // ---------------------------------------------------------------
  let currentPage = "sectors";
  let allStocks = [];        // flat list of all stocks (populated from sectors)
  let priceChart = null;
  let volumeChart = null;
  let equityChart = null;
  let evoTypeChart = null;
  let selectedDays = 90;
  let refreshTimer = null;

  // ---------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------
  async function fetchJSON(path) {
    const res = await fetch(API + path);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  }

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return document.querySelectorAll(sel); }

  function fmt(n, d) {
    if (n == null) return "--";
    return Number(n).toLocaleString(undefined, {
      minimumFractionDigits: d || 0,
      maximumFractionDigits: d || 0,
    });
  }

  function fmtPct(n) {
    if (n == null) return "--";
    const sign = n >= 0 ? "+" : "";
    return sign + Number(n).toFixed(2) + "%";
  }

  function changeClass(n) {
    if (n == null) return "";
    return n >= 0 ? "up" : "down";
  }

  // ---------------------------------------------------------------
  // Clock
  // ---------------------------------------------------------------
  function updateClock() {
    const now = new Date();
    $("#clock").textContent = now.toLocaleTimeString("zh-CN", { hour12: false });
  }
  setInterval(updateClock, 1000);
  updateClock();

  // ---------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------
  $$("#sidebar li").forEach((li) => {
    li.addEventListener("click", () => {
      const page = li.dataset.page;
      navigateTo(page);
    });
  });

  $("#menu-toggle").addEventListener("click", () => {
    const sb = $("#sidebar");
    if (window.innerWidth <= 480) {
      sb.classList.toggle("open");
    } else {
      sb.classList.toggle("collapsed");
    }
  });

  function navigateTo(page) {
    currentPage = page;
    $$("#sidebar li").forEach((li) => li.classList.toggle("active", li.dataset.page === page));
    $$(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + page));
    // Close mobile menu
    $("#sidebar").classList.remove("open");
    loadPageData(page);
  }

  // ---------------------------------------------------------------
  // System status
  // ---------------------------------------------------------------
  async function loadStatus() {
    try {
      const d = await fetchJSON("/api/status");
      $("#sys-status").textContent = d.status === "running" ? "Running" : d.status;
      $("#sys-status").className = "status-badge" + (d.status !== "running" ? " error" : "");
      $("#sys-uptime").textContent = d.uptime;
    } catch {
      $("#sys-status").textContent = "Offline";
      $("#sys-status").className = "status-badge error";
    }
  }

  // ---------------------------------------------------------------
  // Page data loaders
  // ---------------------------------------------------------------
  function loadPageData(page) {
    switch (page) {
      case "sectors": loadSectors(); break;
      case "stock": loadStockPage(); break;
      case "portfolio": loadPortfolio(); break;
      case "reports": loadReports(); break;
      case "simulation": loadSimulation(); break;
      case "evolution": loadEvolution(); break;
    }
  }

  // ---------------------------------------------------------------
  // SECTORS PAGE
  // ---------------------------------------------------------------
  async function loadSectors() {
    const grid = $("#sectors-grid");
    grid.innerHTML = '<p class="placeholder">加载中...</p>';
    try {
      const sectors = await fetchJSON("/api/sectors");
      grid.innerHTML = "";
      allStocks = [];

      for (const sec of sectors) {
        const card = document.createElement("div");
        card.className = "sector-card";
        card.innerHTML = `
          <h3>${sec.name} <span style="color:var(--text-muted);font-size:0.8rem">${sec.id}</span></h3>
          <div class="desc">${sec.description}</div>
          <div class="stock-count">${sec.stock_count} 只股票 | 市场: ${sec.markets.join(", ")}</div>
          <div class="sector-stocks" id="sector-stocks-${sec.id}">
            <p class="placeholder" style="padding:8px 0;font-size:0.82rem">加载中...</p>
          </div>
        `;
        card.addEventListener("click", (e) => {
          // If clicking on a stock row, navigate to stock detail
          const row = e.target.closest(".stock-row");
          if (row) {
            const sym = row.dataset.symbol;
            if (sym) {
              $("#stock-selector").value = sym;
              navigateTo("stock");
              loadStockChart(sym, selectedDays);
            }
          }
        });
        grid.appendChild(card);

        // Load stocks for this sector
        loadSectorStocks(sec.id);
      }
    } catch (err) {
      grid.innerHTML = `<p class="placeholder">加载失败: ${err.message}</p>`;
    }
  }

  async function loadSectorStocks(sectorId) {
    const container = $(`#sector-stocks-${sectorId}`);
    if (!container) return;
    try {
      const stocks = await fetchJSON(`/api/stocks/${sectorId}`);
      let html = "";
      for (const s of stocks) {
        allStocks.push(s);
        const cc = changeClass(s.change_pct);
        html += `
          <div class="stock-row" data-symbol="${s.symbol}">
            <span class="sym">${s.symbol}</span>
            <span class="name">${s.name}</span>
            <span class="price">${s.close != null ? "$" + fmt(s.close, 2) : "--"}</span>
            <span class="change ${cc}">${s.change_pct != null ? fmtPct(s.change_pct) : "--"}</span>
          </div>`;
      }
      container.innerHTML = html || '<p class="placeholder" style="padding:4px 0;font-size:0.82rem">无数据</p>';

      // Also populate stock selector
      populateStockSelector();
    } catch {
      container.innerHTML = '<p class="placeholder" style="font-size:0.82rem">加载失败</p>';
    }
  }

  function populateStockSelector() {
    const sel = $("#stock-selector");
    const current = sel.value;
    const existing = new Set();
    // Keep the first option
    while (sel.options.length > 1) sel.remove(1);
    for (const s of allStocks) {
      if (existing.has(s.symbol)) continue;
      existing.add(s.symbol);
      const opt = document.createElement("option");
      opt.value = s.symbol;
      opt.textContent = `${s.symbol} - ${s.name}`;
      sel.appendChild(opt);
    }
    if (current) sel.value = current;
  }

  // ---------------------------------------------------------------
  // STOCK DETAIL PAGE
  // ---------------------------------------------------------------
  function loadStockPage() {
    populateStockSelector();
  }

  $("#stock-selector").addEventListener("change", function () {
    if (this.value) loadStockChart(this.value, selectedDays);
  });

  $$(".range-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      $$(".range-btn").forEach((b) => b.classList.remove("active"));
      this.classList.add("active");
      selectedDays = parseInt(this.dataset.days);
      const sym = $("#stock-selector").value;
      if (sym) loadStockChart(sym, selectedDays);
    });
  });

  async function loadStockChart(symbol, days) {
    try {
      const data = await fetchJSON(`/api/chart/${symbol}?days=${days}`);
      renderPriceChart(data);
      renderVolumeChart(data);
      renderStockInfo(symbol, data);
    } catch (err) {
      console.error("Chart load error:", err);
    }
  }

  function renderPriceChart(data) {
    const ctx = $("#price-chart");
    if (priceChart) priceChart.destroy();

    const labels = data.data.map((d) => d.date);
    const closes = data.data.map((d) => d.close);
    const sma20 = data.indicators.sma20;
    const sma50 = data.indicators.sma50;

    priceChart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Close",
            data: closes,
            borderColor: "#58a6ff",
            backgroundColor: "rgba(88,166,255,0.05)",
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.1,
          },
          {
            label: "SMA 20",
            data: sma20,
            borderColor: "#d29922",
            borderWidth: 1.2,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false,
          },
          {
            label: "SMA 50",
            data: sma50,
            borderColor: "#bc8cff",
            borderWidth: 1.2,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { color: "#8b949e", font: { size: 11 } } },
          tooltip: {
            backgroundColor: "#1c2128",
            borderColor: "#30363d",
            borderWidth: 1,
            titleColor: "#e6edf3",
            bodyColor: "#8b949e",
          },
        },
        scales: {
          x: {
            ticks: { color: "#6e7681", maxTicksLimit: 10, font: { size: 10 } },
            grid: { color: "rgba(48,54,61,0.5)" },
          },
          y: {
            ticks: { color: "#6e7681", font: { size: 10 } },
            grid: { color: "rgba(48,54,61,0.5)" },
          },
        },
      },
    });
  }

  function renderVolumeChart(data) {
    const ctx = $("#volume-chart");
    if (volumeChart) volumeChart.destroy();

    const labels = data.data.map((d) => d.date);
    const volumes = data.data.map((d) => d.volume);
    const colors = data.data.map((d, i) => {
      if (i === 0) return "rgba(88,166,255,0.5)";
      return d.close >= data.data[i - 1].close
        ? "rgba(63,185,80,0.5)"
        : "rgba(248,81,73,0.5)";
    });

    volumeChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Volume",
          data: volumes,
          backgroundColor: colors,
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            ticks: { color: "#6e7681", maxTicksLimit: 10, font: { size: 10 } },
            grid: { display: false },
          },
          y: {
            ticks: {
              color: "#6e7681", font: { size: 10 },
              callback: (v) => (v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : v),
            },
            grid: { color: "rgba(48,54,61,0.5)" },
          },
        },
      },
    });
  }

  function renderStockInfo(symbol, data) {
    const d = data.data;
    if (!d.length) return;
    const latest = d[d.length - 1];
    const first = d[0];
    const high = Math.max(...d.map((r) => r.high));
    const low = Math.min(...d.map((r) => r.low));
    const avgVol = Math.round(d.reduce((s, r) => s + r.volume, 0) / d.length);
    const change = latest.close - first.close;
    const changePct = ((change / first.close) * 100).toFixed(2);

    $("#stock-info-body").innerHTML = `
      <div class="kv-row"><span class="k">代码</span><span class="v">${symbol}</span></div>
      <div class="kv-row"><span class="k">最新价</span><span class="v">$${fmt(latest.close, 2)}</span></div>
      <div class="kv-row"><span class="k">期间涨跌</span><span class="v" style="color:${change >= 0 ? "var(--green)" : "var(--red)"}">${fmtPct(changePct)}</span></div>
      <div class="kv-row"><span class="k">最高价</span><span class="v">$${fmt(high, 2)}</span></div>
      <div class="kv-row"><span class="k">最低价</span><span class="v">$${fmt(low, 2)}</span></div>
      <div class="kv-row"><span class="k">日均量</span><span class="v">${(avgVol / 1e6).toFixed(2)}M</span></div>
      <div class="kv-row"><span class="k">开盘 (首日)</span><span class="v">$${fmt(first.open, 2)}</span></div>
      <div class="kv-row"><span class="k">数据天数</span><span class="v">${d.length}</span></div>
    `;
  }

  // ---------------------------------------------------------------
  // PORTFOLIO PAGE
  // ---------------------------------------------------------------
  async function loadPortfolio() {
    try {
      const portfolios = await fetchJSON("/api/portfolio");
      const p = portfolios[0]; // show first portfolio
      if (!p) return;

      const totalReturn = p.initial_capital > 0
        ? ((p.current_value - p.initial_capital) / p.initial_capital * 100)
        : 0;

      $("#portfolio-summary").innerHTML = `
        <div class="stat-card">
          <div class="label">总资产</div>
          <div class="value">$${fmt(p.current_value, 2)}</div>
          <div class="sub">${p.name}</div>
        </div>
        <div class="stat-card">
          <div class="label">初始资金</div>
          <div class="value">$${fmt(p.initial_capital, 2)}</div>
        </div>
        <div class="stat-card">
          <div class="label">总收益</div>
          <div class="value ${totalReturn >= 0 ? "green" : "red"}">${fmtPct(totalReturn.toFixed(2))}</div>
        </div>
        <div class="stat-card">
          <div class="label">未实现盈亏</div>
          <div class="value ${p.unrealized_pnl >= 0 ? "green" : "red"}">$${fmt(p.unrealized_pnl, 2)}</div>
        </div>
        <div class="stat-card">
          <div class="label">持仓数</div>
          <div class="value">${p.holdings.length}</div>
        </div>
      `;

      const tbody = $("#holdings-table tbody");
      if (p.holdings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="placeholder">暂无持仓</td></tr>';
      } else {
        tbody.innerHTML = p.holdings.map((h) => {
          const mv = h.shares * h.current_price;
          const cost = h.shares * h.avg_cost;
          const pnl = mv - cost;
          const pnlPct = cost > 0 ? (pnl / cost * 100) : 0;
          return `<tr>
            <td><strong>${h.symbol}</strong></td>
            <td>${fmt(h.shares)}</td>
            <td>$${fmt(h.avg_cost, 2)}</td>
            <td>$${fmt(h.current_price, 2)}</td>
            <td>$${fmt(mv, 2)}</td>
            <td style="color:${pnl >= 0 ? "var(--green)" : "var(--red)"}">$${fmt(pnl, 2)}</td>
            <td style="color:${pnl >= 0 ? "var(--green)" : "var(--red)"}">${fmtPct(pnlPct.toFixed(2))}</td>
          </tr>`;
        }).join("");
      }
    } catch (err) {
      console.error("Portfolio error:", err);
    }
  }

  // ---------------------------------------------------------------
  // REPORTS PAGE
  // ---------------------------------------------------------------
  async function loadReports() {
    try {
      const reports = await fetchJSON("/api/reports");
      const list = $("#reports-list");
      if (reports.length === 0) {
        list.innerHTML = '<li class="placeholder">暂无报告</li>';
        return;
      }
      list.innerHTML = reports.map((r) => `
        <li data-id="${r.id}">
          <div class="rtype">${r.type || "report"}</div>
          <div>${r.sector || "全市场"}</div>
          <div class="rdate">${r.created_at || "--"}</div>
        </li>
      `).join("");

      list.querySelectorAll("li[data-id]").forEach((li) => {
        li.addEventListener("click", () => {
          list.querySelectorAll("li").forEach((l) => l.classList.remove("active"));
          li.classList.add("active");
          loadReportDetail(li.dataset.id);
        });
      });
    } catch (err) {
      console.error("Reports error:", err);
    }
  }

  async function loadReportDetail(id) {
    try {
      const r = await fetchJSON(`/api/reports/${id}`);
      $("#report-content").textContent = r.content || "无内容";
    } catch {
      $("#report-content").textContent = "加载失败";
    }
  }

  // ---------------------------------------------------------------
  // SIMULATION PAGE
  // ---------------------------------------------------------------
  async function loadSimulation() {
    try {
      const data = await fetchJSON("/api/simulation/status");

      $("#sim-status").innerHTML = `
        <div class="stat-card">
          <div class="label">策略数量</div>
          <div class="value">${data.strategies.length}</div>
        </div>
        <div class="stat-card">
          <div class="label">模拟状态</div>
          <div class="value" style="font-size:1rem">${data.simulation_running ? "运行中" : "待启动"}</div>
        </div>
        <div class="stat-card">
          <div class="label">最近回测</div>
          <div class="value" style="font-size:1rem">${data.last_backtest || "--"}</div>
        </div>
      `;

      const tbody = $("#strategies-table tbody");
      tbody.innerHTML = data.strategies.map((s) => `
        <tr>
          <td><strong>${s.name}</strong></td>
          <td>${s.type}</td>
          <td><span class="badge badge-${s.status}">${s.status}</span></td>
          <td>${s.performance_score != null ? fmt(s.performance_score, 1) : "--"}</td>
          <td>${s.win_rate != null ? fmtPct(s.win_rate) : "--"}</td>
          <td>${s.sharpe_ratio != null ? fmt(s.sharpe_ratio, 2) : "--"}</td>
          <td style="font-size:0.78rem;color:var(--text-muted)">${JSON.stringify(s.params)}</td>
        </tr>
      `).join("");

      // Render a demo equity curve
      renderEquityCurve();
    } catch (err) {
      console.error("Simulation error:", err);
    }
  }

  function renderEquityCurve() {
    const ctx = $("#equity-chart");
    if (equityChart) equityChart.destroy();

    // Generate demo data
    const days = 60;
    const labels = [];
    const values = [];
    let v = 100000;
    const now = new Date();
    for (let i = days; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      labels.push(d.toISOString().slice(0, 10));
      v += (Math.random() - 0.45) * 800;
      values.push(Math.round(v));
    }

    equityChart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "组合净值",
          data: values,
          borderColor: "#3fb950",
          backgroundColor: "rgba(63,185,80,0.08)",
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
          tension: 0.2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: "#8b949e" } },
        },
        scales: {
          x: {
            ticks: { color: "#6e7681", maxTicksLimit: 8, font: { size: 10 } },
            grid: { color: "rgba(48,54,61,0.5)" },
          },
          y: {
            ticks: {
              color: "#6e7681", font: { size: 10 },
              callback: (v) => "$" + (v / 1000).toFixed(0) + "k",
            },
            grid: { color: "rgba(48,54,61,0.5)" },
          },
        },
      },
    });
  }

  // ---------------------------------------------------------------
  // EVOLUTION PAGE
  // ---------------------------------------------------------------
  async function loadEvolution() {
    try {
      const data = await fetchJSON("/api/evolution/status");
      const kb = data.knowledge_base;

      // Stats
      $("#evo-knowledge").innerHTML = `
        <div class="stat-card">
          <div class="label">知识库总量</div>
          <div class="value">${kb.total_items}</div>
        </div>
        <div class="stat-card">
          <div class="label">已处理</div>
          <div class="value green">${kb.processed}</div>
        </div>
        <div class="stat-card">
          <div class="label">待处理</div>
          <div class="value" style="color:var(--yellow)">${kb.unprocessed}</div>
        </div>
        <div class="stat-card">
          <div class="label">进化记录</div>
          <div class="value">${data.evolution_history.length}</div>
        </div>
      `;

      // Phase progress
      const pp = data.phase_progress;
      let progressHTML = "";
      for (const [key, val] of Object.entries(pp)) {
        progressHTML += `
          <div class="progress-item">
            <div class="progress-label">
              <span class="pname">${val.name}</span>
              <span class="ppct">${val.progress}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" style="width:${val.progress}%"></div>
            </div>
          </div>`;
      }
      $("#phase-progress").innerHTML = progressHTML;

      // Type stats chart
      renderEvoTypeChart(data.type_stats);

      // History table
      const tbody = $("#evo-history-table tbody");
      if (data.evolution_history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="placeholder">暂无进化记录</td></tr>';
      } else {
        tbody.innerHTML = data.evolution_history.map((r) => `
          <tr>
            <td style="font-size:0.78rem">${r.id}</td>
            <td style="font-size:0.78rem">${r.timestamp ? r.timestamp.slice(0, 19).replace("T", " ") : "--"}</td>
            <td>${r.type}</td>
            <td><span class="badge badge-${r.status}">${r.status}</span></td>
            <td>${r.trigger}</td>
            <td>${r.description}</td>
          </tr>
        `).join("");
      }
    } catch (err) {
      console.error("Evolution error:", err);
    }
  }

  function renderEvoTypeChart(stats) {
    const ctx = $("#evo-type-chart");
    if (evoTypeChart) evoTypeChart.destroy();

    const labels = Object.keys(stats);
    const completed = labels.map((k) => stats[k].completed || 0);
    const failed = labels.map((k) => stats[k].failed || 0);
    const other = labels.map((k) => (stats[k].total || 0) - (stats[k].completed || 0) - (stats[k].failed || 0));

    if (labels.length === 0) {
      // No data yet - show placeholder
      ctx.parentElement.innerHTML = '<p class="placeholder">暂无进化数据</p>';
      return;
    }

    evoTypeChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "完成", data: completed, backgroundColor: "rgba(63,185,80,0.7)" },
          { label: "失败", data: failed, backgroundColor: "rgba(248,81,73,0.7)" },
          { label: "其他", data: other, backgroundColor: "rgba(139,148,158,0.4)" },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#8b949e", font: { size: 10 } } } },
        scales: {
          x: {
            stacked: true,
            ticks: { color: "#6e7681", font: { size: 10 } },
            grid: { display: false },
          },
          y: {
            stacked: true,
            ticks: { color: "#6e7681", font: { size: 10 }, stepSize: 1 },
            grid: { color: "rgba(48,54,61,0.5)" },
          },
        },
      },
    });
  }

  // ---------------------------------------------------------------
  // Auto refresh
  // ---------------------------------------------------------------
  function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(() => {
      loadStatus();
      loadPageData(currentPage);
    }, REFRESH_INTERVAL);
  }

  // ---------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------
  loadStatus();
  loadSectors();
  startAutoRefresh();
})();
