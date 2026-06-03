/* The Consensus — institutional equity dashboard (client-side, reads data.json) */
"use strict";

let API = null, ALL = [], META = {};
const LS = "consensus.v1";
const state = { sectors: new Set(), themes: new Set(), hideNoCov: false, preset: null, q: "" };

/* ---------------- formatting ---------------- */
const f2 = v => (v == null ? "" : (+v).toFixed(2));
const f1 = v => (v == null ? "" : (+v).toFixed(1));
const pct = v => (v == null ? "" : (v > 0 ? "+" : "") + (+v).toFixed(2) + "%");
const money = v => (v == null ? "" : "$" + (+v).toFixed(2));
function cap(v) {
  if (v == null) return "";
  const a = Math.abs(v);
  if (a >= 1e12) return (v / 1e12).toFixed(2) + "T";
  if (a >= 1e9) return (v / 1e9).toFixed(1) + "B";
  if (a >= 1e6) return (v / 1e6).toFixed(0) + "M";
  return (+v).toFixed(0);
}
const band = s => Math.min(5, Math.max(1, Math.round(s)));
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function hl(text) {
  const q = state.q.trim();
  if (!q) return esc(text);
  const i = String(text).toLowerCase().indexOf(q.toLowerCase());
  if (i < 0) return esc(text);
  const t = String(text);
  return esc(t.slice(0, i)) + "<mark style='background:rgba(232,161,60,.35);color:#fff;border-radius:2px'>" +
    esc(t.slice(i, i + q.length)) + "</mark>" + esc(t.slice(i + q.length));
}

/* null-aware numeric sort: empty values always sink to the bottom */
function numCmp(a, b, na, nb, desc) {
  if (a == null && b == null) return 0;
  if (a == null) return desc ? -1 : 1;
  if (b == null) return desc ? 1 : -1;
  return a - b;
}

/* ---------------- cell renderers ---------------- */
const DIST = [["strongBuy", "var(--sb)"], ["buy", "var(--buy)"], ["hold", "var(--hold)"], ["sell", "var(--sell)"], ["strongSell", "var(--ss)"]];
function distBar(d, w) {
  if (!d) return "";
  const tot = DIST.reduce((s, [k]) => s + (d[k] || 0), 0);
  if (!tot) return "";
  const title = `Strong Buy ${d.strongBuy} · Buy ${d.buy} · Hold ${d.hold} · Sell ${d.sell} · Strong Sell ${d.strongSell}`;
  const segs = DIST.map(([k, c]) => { const p = (d[k] || 0) / tot * 100; return p ? `<i style="width:${p}%;background:${c}"></i>` : ""; }).join("");
  return `<span class="dist" style="width:${w || 88}px" title="${title}">${segs}</span>`;
}
function spark(arr) {
  if (!arr || arr.length < 2) return "";
  const w = 84, h = 22, mn = Math.min(...arr), mx = Math.max(...arr), rng = (mx - mn) || 1;
  const pts = arr.map((v, i) => `${(i / (arr.length - 1) * w).toFixed(1)},${(h - (v - mn) / rng * h).toFixed(1)}`).join(" ");
  const up = arr[arr.length - 1] >= arr[0], c = up ? "var(--pos)" : "var(--neg)";
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="${c}" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
}
const perfStyle = p => ({ color: p.value > 0 ? "var(--pos)" : p.value < 0 ? "var(--neg)" : "var(--muted)" });
const get = path => p => { const c = p.data && p.data.changes; return c ? c[path] : null; };

const R = {
  sym: p => `<span class="sym">${hl(p.value)}</span>`,
  name: p => `<span class="cname">${hl(p.value)}</span>`,
  consensus: p => p.value == null
    ? `<span class="pill cnone">No coverage</span>`
    : `<span class="pill c${band(p.value)}">${esc(p.data.label)} · ${p.value.toFixed(2)}</span>`,
  dist: p => distBar(p.data.distribution),
  momentum: p => {
    const d = p.data.consensus_dir, dl = p.data.consensus_delta;
    const g = d === "up" ? "▲" : d === "down" ? "▼" : "▬";
    return `<span class="arrow ${d}">${g}</span> <span class="num muted">${dl == null ? "" : (dl > 0 ? "+" : "") + dl}</span>`;
  },
  spark: p => spark(p.value),
  themes: p => (p.value || []).map(t => `<span class="tag">${esc(t)}</span>`).join(""),
  trend: p => { const v = p.value; if (!v) return ""; const c = v.includes("Up") ? "bU" : v.includes("Down") ? "bD" : "bN"; return `<span class="badge ${c}">${esc(v)}</span>`; },
  dma: p => { const v = p.value; if (!v) return ""; return `<span class="badge ${v === "Above" ? "bU" : "bD"}">${esc(v)}</span>`; },
  rsi: p => { const v = p.value; if (v == null) return ""; const col = v < 30 ? "var(--pos)" : v > 70 ? "var(--neg)" : "var(--ink2)"; return `<span class="num" style="color:${col}">${v.toFixed(0)}</span>`; },
};

/* ---------------- columns ---------------- */
const NUM = { filter: "agNumberColumnFilter", comparator: numCmp, type: "rightAligned", cellClass: "num" };
const TXT = { filter: "agTextColumnFilter" };

function columns() {
  return [
    {
      headerName: "Identity", children: [
        { colId: "symbol", field: "symbol", headerName: "Sym", pinned: "left", width: 92, cellRenderer: R.sym, ...TXT, filterValueGetter: p => p.data.symbol },
        { colId: "name", field: "name", headerName: "Company", pinned: "left", width: 210, cellRenderer: R.name, ...TXT },
      ]
    },
    {
      headerName: "Classification", children: [
        { colId: "sector", field: "sector", headerName: "Sector", width: 150, ...TXT },
        { colId: "industry", field: "industry", headerName: "Industry", width: 190, ...TXT, hide: true },
        { colId: "exchange", field: "exchange", headerName: "Exch", width: 110, ...TXT, hide: true },
        { colId: "mcat", field: "market_cap_category", headerName: "Cap Tier", width: 100, ...TXT, hide: true },
        { colId: "themes", field: "themes", headerName: "Themes", width: 200, cellRenderer: R.themes, sortable: false, getQuickFilterText: p => (p.value || []).join(" ") },
      ]
    },
    {
      headerName: "Market", children: [
        { colId: "market_cap", field: "market_cap", headerName: "Mkt Cap", width: 110, valueFormatter: p => cap(p.value), ...NUM, sort: null },
        { colId: "price", field: "price", headerName: "Price", width: 96, valueFormatter: p => money(p.value), ...NUM },
        { colId: "spark", field: "sparkline", headerName: "1Y Trend", width: 100, cellRenderer: R.spark, sortable: false, suppressMenu: true, getQuickFilterText: () => "" },
        { colId: "c1d", headerName: "1D %", width: 84, valueGetter: get("1D"), valueFormatter: p => pct(p.value), cellStyle: perfStyle, ...NUM },
        { colId: "c1w", headerName: "1W %", width: 84, valueGetter: get("1W"), valueFormatter: p => pct(p.value), cellStyle: perfStyle, ...NUM, hide: true },
        { colId: "c1m", headerName: "1M %", width: 84, valueGetter: get("1M"), valueFormatter: p => pct(p.value), cellStyle: perfStyle, ...NUM },
        { colId: "cytd", headerName: "YTD %", width: 88, valueGetter: get("YTD"), valueFormatter: p => pct(p.value), cellStyle: perfStyle, ...NUM },
        { colId: "c1y", headerName: "1Y %", width: 84, valueGetter: get("1Y"), valueFormatter: p => pct(p.value), cellStyle: perfStyle, ...NUM, hide: true },
      ]
    },
    {
      headerName: "Analyst Consensus", children: [
        { colId: "consensus", field: "consensus", headerName: "Consensus", width: 150, cellRenderer: R.consensus, comparator: numCmp, sort: "asc", sortIndex: 0, filter: "agNumberColumnFilter" },
        { colId: "dist", field: "distribution", headerName: "Distribution", width: 110, cellRenderer: R.dist, sortable: false, getQuickFilterText: () => "" },
        { colId: "momentum", field: "consensus_delta", headerName: "30d Δ", width: 92, cellRenderer: R.momentum, comparator: numCmp, filter: "agNumberColumnFilter", cellClass: "num" },
        { colId: "analysts", field: "analysts", headerName: "# Analysts", width: 100, sort: "desc", sortIndex: 1, ...NUM },
        { colId: "target", field: "price_target", headerName: "Avg Target", width: 104, valueFormatter: p => money(p.value), ...NUM, hide: true },
        { colId: "upside", field: "upside", headerName: "Upside %", width: 100, valueFormatter: p => pct(p.value), cellStyle: perfStyle, ...NUM },
      ]
    },
    {
      headerName: "Valuation & Quality", children: [
        { colId: "fpe", field: "forward_pe", headerName: "Fwd P/E", width: 92, valueFormatter: p => f1(p.value), ...NUM },
        { colId: "peg", field: "peg", headerName: "PEG", width: 80, valueFormatter: p => f2(p.value), ...NUM, hide: true },
        { colId: "div", field: "dividend_yield", headerName: "Div %", width: 84, valueFormatter: p => f2(p.value), ...NUM },
        { colId: "rev", field: "revenue_growth", headerName: "Rev Gr%", width: 92, valueFormatter: p => pct(p.value), cellStyle: perfStyle, ...NUM },
        { colId: "eps", field: "eps_growth", headerName: "EPS Gr%", width: 92, valueFormatter: p => pct(p.value), cellStyle: perfStyle, ...NUM, hide: true },
        { colId: "gm", field: "gross_margin", headerName: "Gross M%", width: 96, valueFormatter: p => f1(p.value), ...NUM, hide: true },
        { colId: "om", field: "operating_margin", headerName: "Op M%", width: 90, valueFormatter: p => f1(p.value), ...NUM },
        { colId: "roe", field: "roe", headerName: "ROE %", width: 88, valueFormatter: p => f1(p.value), ...NUM, hide: true },
        { colId: "fcf", field: "fcf_yield", headerName: "FCF Yld%", width: 94, valueFormatter: p => f2(p.value), ...NUM, hide: true },
      ]
    },
    {
      headerName: "Technicals", children: [
        { colId: "rsi", field: "rsi", headerName: "RSI", width: 76, cellRenderer: R.rsi, comparator: numCmp, filter: "agNumberColumnFilter", cellClass: "num" },
        { colId: "trend", field: "trend", headerName: "Trend", width: 134, cellRenderer: R.trend, ...TXT },
        { colId: "dma50", field: "dma50_status", headerName: "50 DMA", width: 92, cellRenderer: R.dma, ...TXT, hide: true },
        { colId: "dma200", field: "dma200_status", headerName: "200 DMA", width: 96, cellRenderer: R.dma, ...TXT, hide: true },
      ]
    },
  ];
}

/* ---------------- grid ---------------- */
function initGrid() {
  const opts = {
    columnDefs: columns(),
    rowData: ALL,
    defaultColDef: { sortable: true, resizable: true, filter: true, suppressHeaderMenuButton: false, minWidth: 70 },
    rowHeight: 38, headerHeight: 34, groupHeaderHeight: 28,
    animateRows: true, multiSortKey: "ctrl", suppressDragLeaveHidesColumns: true,
    enableCellTextSelection: true, ensureDomOrder: true,
    getRowClass: p => (p.data.consensus == null && !state.hideNoCov) ? "row-de" : "",
    isExternalFilterPresent: () => state.sectors.size || state.themes.size || state.hideNoCov || !!state.preset,
    doesExternalFilterPass: node => {
      const d = node.data;
      if (state.hideNoCov && d.consensus == null) return false;
      if (state.sectors.size && !state.sectors.has(d.sector)) return false;
      if (state.themes.size && !(d.themes || []).some(t => state.themes.has(t))) return false;
      if (state.preset && !state.preset.fn(d)) return false;
      return true;
    },
    onModelUpdated: updateCount,
    onRowClicked: e => openDrawer(e.data),
    onColumnVisible: saveState, onColumnMoved: saveState, onColumnResized: e => { if (e.finished) saveState(); },
    onSortChanged: saveState,
  };
  API = agGrid.createGrid(document.getElementById("grid"), opts);
  restoreState();
}

function updateCount() {
  if (!API) return;
  const shown = API.getDisplayedRowCount();
  document.getElementById("count").innerHTML = `Showing <b>${shown.toLocaleString()}</b> of <b>${ALL.length.toLocaleString()}</b> stocks`;
}

/* ---------------- dashboard cards ---------------- */
function cards() {
  const s = META.stats, el = document.getElementById("cards");
  const c = (l, v, x, cls) => `<div class="card ${cls || ""}"><div class="l">${l}</div><div class="v num">${v}</div><div class="x">${x || ""}</div></div>`;
  el.innerHTML = [
    c("Stocks Tracked", s.total, `${s.covered} with coverage`),
    c("Strong Buys", s.strong_buy, "consensus ≤ 1.5", "pos"),
    c("Sell-Rated", s.sell, "consensus > 3.5", s.sell ? "neg" : ""),
    c("Avg Consensus", s.avg_consensus ?? "—", s.avg_consensus <= 2.5 ? "net bullish" : "net cautious"),
    c("Avg Upside", pct(s.avg_upside), "to mean target", s.avg_upside > 0 ? "pos" : "neg"),
    c("Most Bullish Sector", s.most_bullish_sector || "—", "lowest avg score"),
    c("Most Bearish Sector", s.most_bearish_sector || "—", "highest avg score"),
    c("Most Upgraded", s.most_upgraded_sector || "—", "30d sentiment ↑"),
    c("Top Coverage", s.top_coverage ? s.top_coverage.symbol : "—", s.top_coverage ? s.top_coverage.analysts + " analysts" : ""),
    c("Largest Cap", s.largest ? s.largest.symbol : "—", s.largest ? cap(s.largest.market_cap) : ""),
  ].join("");
}

/* ---------------- charts ---------------- */
const consensusColor = v => v == null ? "#3a4250" : v <= 1.5 ? "#16c784" : v <= 2.2 ? "#5fce9b" : v <= 2.8 ? "#e3c34a" : v <= 3.5 ? "#f0935a" : "#ef5b53";

function heatmap() {
  const ch = echarts.init(document.getElementById("heatmap"), null, { renderer: "canvas" });
  const data = META.sectors.map(s => ({
    name: s.sector, value: s.market_cap,
    itemStyle: { color: consensusColor(s.avg_consensus) },
    sectorMeta: s,
  }));
  ch.setOption({
    backgroundColor: "transparent",
    tooltip: {
      backgroundColor: "#161b24", borderColor: "#2c3442", textStyle: { color: "#e8edf4", fontSize: 12 },
      formatter: p => { const m = p.data.sectorMeta; return `<b>${m.sector}</b><br/>Stocks: ${m.count}<br/>Mkt Cap: ${cap(m.market_cap)}<br/>Avg Consensus: ${m.avg_consensus ?? "—"}<br/>Avg Upside: ${pct(m.avg_upside)}`; }
    },
    series: [{
      type: "treemap", roam: false, nodeClick: false, breadcrumb: { show: false },
      width: "100%", height: "100%", top: 0, left: 0, right: 0, bottom: 0,
      itemStyle: { borderColor: "#0a0c10", borderWidth: 2, gapWidth: 2 },
      label: { show: true, color: "#06140d", fontFamily: "Inter", fontWeight: 700, fontSize: 12,
        formatter: p => `${p.name}\n${cap(p.value)}` },
      data,
    }]
  });
  ch.on("click", p => { if (p.data && p.data.name) { toggleSector(p.data.name); } });
  return ch;
}

function distChart() {
  const ch = echarts.init(document.getElementById("distChart"));
  const agg = { strongBuy: 0, buy: 0, hold: 0, sell: 0, strongSell: 0 };
  ALL.forEach(r => { if (r.distribution) DIST.forEach(([k]) => agg[k] += r.distribution[k] || 0); });
  ch.setOption({
    backgroundColor: "transparent", grid: { left: 8, right: 12, top: 14, bottom: 22 },
    tooltip: { backgroundColor: "#161b24", borderColor: "#2c3442", textStyle: { color: "#e8edf4" } },
    xAxis: { type: "category", data: ["Str Buy", "Buy", "Hold", "Sell", "Str Sell"], axisLabel: { color: "#8b93a0", fontSize: 10 }, axisLine: { lineStyle: { color: "#222936" } } },
    yAxis: { type: "value", axisLabel: { color: "#525b68", fontSize: 10 }, splitLine: { lineStyle: { color: "#161b22" } } },
    series: [{ type: "bar", data: DIST.map(([k, c]) => ({ value: agg[k], itemStyle: { color: c.replace("var(--sb)", "#16c784") } })), barWidth: "56%" }]
  });
  // color map fix
  ch.setOption({ series: [{ data: [agg.strongBuy, agg.buy, agg.hold, agg.sell, agg.strongSell].map((v, i) => ({ value: v, itemStyle: { color: ["#16c784", "#5fce9b", "#e3c34a", "#f0935a", "#ef5b53"][i] } })) }] });
  return ch;
}

function sectorChart() {
  const ch = echarts.init(document.getElementById("sectorChart"));
  const rows = META.sectors.filter(s => s.avg_upside != null).sort((a, b) => b.avg_upside - a.avg_upside).slice(0, 8).reverse();
  ch.setOption({
    backgroundColor: "transparent", grid: { left: 8, right: 40, top: 6, bottom: 6, containLabel: true },
    tooltip: { backgroundColor: "#161b24", borderColor: "#2c3442", textStyle: { color: "#e8edf4" }, formatter: p => `${p.name}: ${pct(p.value)}` },
    xAxis: { type: "value", axisLabel: { show: false }, splitLine: { show: false }, axisLine: { show: false } },
    yAxis: { type: "category", data: rows.map(s => s.sector), axisLabel: { color: "#8b93a0", fontSize: 10 }, axisLine: { lineStyle: { color: "#222936" } } },
    series: [{ type: "bar", data: rows.map(s => ({ value: +s.avg_upside.toFixed(1), itemStyle: { color: s.avg_upside >= 0 ? "#22c98a" : "#f0676b", borderRadius: 3 } })),
      label: { show: true, position: "right", color: "#c2cad6", fontSize: 10, formatter: p => pct(p.value) }, barWidth: "62%" }]
  });
  return ch;
}

/* ---------------- presets ---------------- */
const PRESETS = [
  { id: "sblc", label: "Strong Buy Large Caps", fn: d => d.consensus != null && d.consensus <= 1.5 && d.market_cap >= 10e9 },
  { id: "upside", label: "Highest Upside", fn: d => d.upside != null, sort: ["upside", "desc"] },
  { id: "upg", label: "Most Upgraded", fn: d => d.consensus_delta != null && d.consensus_delta < 0, sort: ["momentum", "asc"] },
  { id: "fav", label: "Analyst Favorites", fn: d => d.analysts >= 25 && d.consensus != null && d.consensus <= 2 },
  { id: "oversold", label: "Oversold Buys", fn: d => d.rsi != null && d.rsi < 35 && d.consensus != null && d.consensus <= 2.5 },
  { id: "growth", label: "Growth Leaders", fn: d => d.revenue_growth != null && d.revenue_growth >= 20, sort: ["rev", "desc"] },
  { id: "value", label: "Value Stocks", fn: d => d.forward_pe != null && d.forward_pe > 0 && d.forward_pe < 15 && d.consensus != null && d.consensus <= 3 },
  { id: "div", label: "Dividend Stocks", fn: d => d.dividend_yield != null && d.dividend_yield >= 3, sort: ["div", "desc"] },
  { id: "ai", label: "AI Stocks", fn: d => (d.themes || []).includes("AI") },
  { id: "semi", label: "Semiconductor Leaders", fn: d => (d.themes || []).includes("Semiconductors") },
  { id: "mom", label: "Momentum", fn: d => { const m = d.changes && d.changes["1M"]; return m != null && m > 10; }, sort: ["c1m", "desc"] },
  { id: "contra", label: "Contrarian Plays", fn: d => d.consensus != null && d.consensus >= 3 && d.upside != null && d.upside > 15 },
  { id: "quality", label: "Quality Compounders", fn: d => d.roe != null && d.roe >= 20 && d.operating_margin != null && d.operating_margin >= 20 && d.revenue_growth != null && d.revenue_growth >= 10 },
  { id: "smallcap", label: "Smaller-Cap Buys", fn: d => d.market_cap != null && d.market_cap < 20e9 && d.consensus != null && d.consensus <= 2 },
];

function buildPresets() {
  const el = document.getElementById("presets");
  el.innerHTML = PRESETS.map(p => `<button class="chip" data-id="${p.id}">${p.label}</button>`).join("");
  el.querySelectorAll(".chip").forEach(b => b.onclick = () => {
    const p = PRESETS.find(x => x.id === b.dataset.id);
    if (state.preset && state.preset.id === p.id) { state.preset = null; }
    else {
      state.preset = p;
      if (p.sort) API.applyColumnState({ state: [{ colId: p.sort[0], sort: p.sort[1], sortIndex: 0 }], defaultState: { sort: null } });
    }
    syncPresetChips();
    API.onFilterChanged();
  });
}
function syncPresetChips() {
  document.querySelectorAll("#presets .chip").forEach(b => b.classList.toggle("on", state.preset && state.preset.id === b.dataset.id));
}

/* ---------------- sectors/themes external filter via heatmap + drawer ---------------- */
function toggleSector(sec) {
  if (state.sectors.has(sec)) state.sectors.delete(sec); else state.sectors.add(sec);
  API.onFilterChanged(); updateCount();
}

/* ---------------- columns popover ---------------- */
function buildColsPopover() {
  const pop = document.getElementById("colsPop");
  const groups = columns();
  pop.innerHTML = groups.map(g => {
    const items = g.children.filter(c => c.colId !== "spark").map(c =>
      `<label><input type="checkbox" data-col="${c.colId}" ${c.hide ? "" : "checked"}> ${esc(c.headerName)}</label>`).join("");
    return `<div class="cg">${esc(g.headerName)}</div>${items}`;
  }).join("");
  pop.querySelectorAll("input[data-col]").forEach(cb => cb.onchange = () => API.setColumnsVisible([cb.dataset.col], cb.checked));
  document.getElementById("colsBtn").onclick = e => { e.stopPropagation(); pop.classList.toggle("open"); };
  document.addEventListener("click", e => { if (!pop.contains(e.target) && e.target.id !== "colsBtn") pop.classList.remove("open"); });
}
function syncColsPopover() {
  document.querySelectorAll("#colsPop input[data-col]").forEach(cb => {
    const col = API.getColumn(cb.dataset.col); if (col) cb.checked = col.isVisible();
  });
}

/* ---------------- detail drawer ---------------- */
let dchart = null;
function openDrawer(d) {
  const drawer = document.getElementById("drawer"), scrim = document.getElementById("scrim");
  const dist = d.distribution, tot = dist ? DIST.reduce((s, [k]) => s + dist[k], 0) : 0;
  const distFull = dist && tot ? `<div class="distbar">` + DIST.map(([k, c]) => { const p = dist[k] / tot * 100; return p > 0 ? `<i style="width:${p}%;background:${c.replace('var(--sb)', '#16c784')}">${dist[k]}</i>` : ""; }).join("") + `</div>
    <div class="muted" style="font-size:11px;margin-top:6px">Strong Buy · Buy · Hold · Sell · Strong Sell</div>` : `<div class="muted">No analyst coverage.</div>`;

  const peers = ALL.filter(x => x.sector === d.sector && x.symbol !== d.symbol)
    .sort((a, b) => (a.consensus ?? 9) - (b.consensus ?? 9)).slice(0, 5);
  const peerRows = peers.map(p => `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--line)">
    <span><b class="sym">${p.symbol}</b> <span class="muted">${esc((p.name || "").slice(0, 26))}</span></span>
    <span>${p.consensus == null ? '<span class="muted">—</span>' : `<span class="pill c${band(p.consensus)}">${p.consensus.toFixed(2)}</span>`}</span></div>`).join("");

  const kv = (k, v) => `<div class="i"><div class="k">${k}</div><div class="v">${v == null || v === "" ? "—" : v}</div></div>`;
  const ai = d.ai;
  const thesis = ai ? `<div class="dsec"><h4>AI Investment Theses</h4><div class="thesis">
      <div class="t bull"><h5 style="color:var(--pos)">▲ Bull case</h5><p>${esc(ai.bull)}</p></div>
      <div class="t bear"><h5 style="color:var(--neg)">▼ Bear case</h5><p>${esc(ai.bear)}</p></div></div>
      ${ai.catalysts ? `<div class="i" style="margin-top:12px"><div class="k">Key Catalysts</div><div class="v" style="font-size:12.5px">${esc(ai.catalysts)}</div></div>` : ""}
      ${ai.risks ? `<div class="i" style="margin-top:8px"><div class="k">Key Risks</div><div class="v" style="font-size:12.5px">${esc(ai.risks)}</div></div>` : ""}
    </div>` : "";

  drawer.innerHTML = `
    <div class="dh">
      <div>
        <h2>${esc(d.symbol)} ${d.consensus != null ? `<span class="pill c${band(d.consensus)}" style="font-size:13px;vertical-align:middle">${esc(d.label)} · ${d.consensus.toFixed(2)}</span>` : ""}</h2>
        <div class="co">${esc(d.name)} · ${esc(d.exchange)} · ${esc(d.sector || "—")} / ${esc(d.industry || "—")}</div>
        <div class="co">${(d.themes || []).map(t => `<span class="tag">${esc(t)}</span>`).join("")}</div>
      </div>
      <button class="close" id="dclose">×</button>
    </div>
    <div class="dbody">
      <div class="dsec"><div id="dchart"></div></div>
      <div class="dsec"><h4>Analyst Distribution · ${d.analysts || 0} analysts ${d.consensus_prev != null ? `· prev ${d.consensus_prev} → now ${d.consensus} (${d.consensus_dir})` : ""}</h4>${distFull}</div>
      <div class="dsec"><h4>Valuation & Quality</h4><div class="kv">
        ${kv("Market Cap", cap(d.market_cap))}${kv("Price", money(d.price))}${kv("Avg Target", money(d.price_target))}${kv("Implied Upside", pct(d.upside))}
        ${kv("Fwd P/E", f1(d.forward_pe))}${kv("PEG", f2(d.peg))}${kv("Div Yield", d.dividend_yield == null ? "" : d.dividend_yield + "%")}${kv("Rev Growth", pct(d.revenue_growth))}
        ${kv("EPS Growth", pct(d.eps_growth))}${kv("Gross Margin", d.gross_margin == null ? "" : d.gross_margin + "%")}${kv("Op Margin", d.operating_margin == null ? "" : d.operating_margin + "%")}${kv("ROE", d.roe == null ? "" : d.roe + "%")}
      </div></div>
      <div class="dsec"><h4>Technicals</h4><div class="kv">
        ${kv("RSI (14)", f1(d.rsi))}${kv("Trend", d.trend)}${kv("50 DMA", d.dma50_status)}${kv("200 DMA", d.dma200_status)}
        ${kv("1D", pct(d.changes && d.changes["1D"]))}${kv("1M", pct(d.changes && d.changes["1M"]))}${kv("YTD", pct(d.changes && d.changes.YTD))}${kv("1Y", pct(d.changes && d.changes["1Y"]))}
      </div></div>
      ${thesis}
      <div class="dsec"><h4>Sector Ranking</h4><div class="i">${d.sector || "—"}: rank <b>#${d.sector_rank || "—"}</b> of ${d.sector_size || "—"} by consensus</div></div>
      <div class="dsec"><h4>Sector Peers</h4>${peerRows || '<div class="muted">No peers in dataset.</div>'}</div>
    </div>`;

  drawer.classList.add("open"); drawer.setAttribute("aria-hidden", "false"); scrim.classList.add("open");
  document.getElementById("dclose").onclick = closeDrawer;
  if (d.sparkline && d.sparkline.length > 1) {
    if (dchart) dchart.dispose();
    dchart = echarts.init(document.getElementById("dchart"));
    const up = d.sparkline[d.sparkline.length - 1] >= d.sparkline[0];
    dchart.setOption({
      backgroundColor: "transparent", grid: { left: 44, right: 12, top: 12, bottom: 20 },
      tooltip: { trigger: "axis", backgroundColor: "#161b24", borderColor: "#2c3442", textStyle: { color: "#e8edf4" }, formatter: p => money(p[0].value) },
      xAxis: { type: "category", show: false, data: d.sparkline.map((_, i) => i) },
      yAxis: { type: "value", scale: true, axisLabel: { color: "#525b68", fontSize: 10, formatter: v => "$" + v.toFixed(0) }, splitLine: { lineStyle: { color: "#161b22" } } },
      series: [{ type: "line", data: d.sparkline, smooth: true, showSymbol: false, lineStyle: { color: up ? "#22c98a" : "#f0676b", width: 2 },
        areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: up ? "rgba(34,201,138,.28)" : "rgba(240,103,107,.28)" }, { offset: 1, color: "transparent" }] } } }]
    });
  }
}
function closeDrawer() {
  document.getElementById("drawer").classList.remove("open");
  document.getElementById("scrim").classList.remove("open");
  if (dchart) { dchart.dispose(); dchart = null; }
}

/* ---------------- persistence + toolbar ---------------- */
function saveState() {
  if (!API) return;
  try {
    localStorage.setItem(LS, JSON.stringify({
      cols: API.getColumnState(), hideNoCov: state.hideNoCov, compact: document.body.classList.contains("compact"),
    }));
  } catch (e) {}
  syncColsPopover();
}
function restoreState() {
  let s; try { s = JSON.parse(localStorage.getItem(LS)); } catch (e) {}
  if (!s) return;
  if (s.cols) API.applyColumnState({ state: s.cols, applyOrder: true });
  if (s.hideNoCov) { state.hideNoCov = true; document.getElementById("hideNoCov").classList.add("on"); API.onFilterChanged(); }
  if (s.compact) { document.body.classList.add("compact"); API.setGridOption("rowHeight", 30); document.getElementById("density").classList.add("on"); }
  syncColsPopover();
}

function toolbar() {
  const q = document.getElementById("q");
  q.addEventListener("input", () => { state.q = q.value; API.setGridOption("quickFilterText", q.value); API.refreshCells({ columns: ["symbol", "name"], force: true }); });
  document.addEventListener("keydown", e => {
    if (e.key === "/" && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    if (e.key === "Escape") { closeDrawer(); }
  });
  document.getElementById("scrim").onclick = closeDrawer;

  const hnc = document.getElementById("hideNoCov");
  hnc.onclick = () => { state.hideNoCov = !state.hideNoCov; hnc.classList.toggle("on", state.hideNoCov); API.onFilterChanged(); API.redrawRows(); saveState(); };

  const dens = document.getElementById("density");
  dens.onclick = () => { const on = document.body.classList.toggle("compact"); dens.classList.toggle("on", on); API.setGridOption("rowHeight", on ? 30 : 38); API.resetRowHeights(); saveState(); };

  const fs = document.getElementById("fs");
  fs.onclick = () => { const on = document.body.classList.toggle("fs"); fs.classList.toggle("on", on); setTimeout(() => API.sizeColumnsToFit && 0, 50); };

  document.getElementById("csv").onclick = () => API.exportDataAsCsv({ fileName: `consensus-${META.date || "export"}.csv`, allColumns: true });

  document.getElementById("reset").onclick = () => {
    state.sectors.clear(); state.themes.clear(); state.preset = null; state.hideNoCov = false; state.q = "";
    q.value = ""; API.setGridOption("quickFilterText", "");
    hnc.classList.remove("on"); syncPresetChips();
    API.applyColumnState({ state: [{ colId: "consensus", sort: "asc", sortIndex: 0 }, { colId: "analysts", sort: "desc", sortIndex: 1 }], defaultState: { sort: null } });
    API.setFilterModel(null); API.onFilterChanged();
    localStorage.removeItem(LS); syncColsPopover();
  };
}

/* ---------------- boot ---------------- */
async function boot() {
  try {
    const res = await fetch("data.json", { cache: "no-store" });
    META = await res.json();
  } catch (e) {
    document.getElementById("count").textContent = "Failed to load data.json";
    return;
  }
  ALL = META.stocks || [];
  document.getElementById("asof").textContent = META.date || "—";
  document.getElementById("footer").innerHTML =
    `The Consensus · ${ALL.length} stocks · generated ${esc(META.generated || META.date || "")} (UTC) · data via public Yahoo Finance endpoints · ` +
    `Sorting: click a header to sort, Ctrl/Shift-click to layer multiple sorts · Press “/” to search.`;

  cards();
  initGrid();
  buildPresets();
  buildColsPopover();
  toolbar();
  updateCount();

  const charts = [heatmap(), distChart(), sectorChart()];
  window.addEventListener("resize", () => charts.forEach(c => c && c.resize()));
}
boot();
