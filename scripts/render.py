"""payload 를 단일 HTML 대시보드로 렌더링한다 -> docs/index.html

레이아웃·색·구성은 기존에 쓰던 top10_dashboard.html 형식을 그대로 따르고,
ETF 3종을 상단 탭으로 전환할 수 있게 확장했다.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from config import DOCS_DIR, ETFS
from payload import build_payload, load_records

KST = ZoneInfo("Asia/Seoul")

PALETTE = [
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7",
    "#e34948", "#8a8a8a", "#7f77dd", "#0f6e56", "#993c1d", "#185fa5", "#c98500",
    "#993556", "#27500a", "#3c3489", "#791f1f", "#5f5e5a", "#26215c",
]

CSS = """
  :root {
    --bg: #fafaf9; --card: #ffffff; --border: #e5e3dd; --text: #1a1a19;
    --text-secondary: #6b6a64; --text-muted: #96958e; --accent: #2a78d6;
    --up: #1baf7a; --down: #e34948; --in-bg: #e1f5ee; --in-text: #085041;
    --out-bg: #fcebeb; --out-text: #791f1f;
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 2rem; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Pretendard, sans-serif; }
  .wrap { max-width: 900px; margin: 0 auto; }
  h1 { font-size: 20px; font-weight: 600; margin: 0 0 4px; }
  .sub { color: var(--text-secondary); font-size: 13px; margin: 0 0 24px; }
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .metric { background: var(--card); border: 0.5px solid var(--border); border-radius: 10px; padding: 14px 16px; }
  .metric .label { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
  .metric .value { font-size: 22px; font-weight: 600; }
  .card { background: var(--card); border: 0.5px solid var(--border); border-radius: 12px; padding: 1.25rem; margin-bottom: 20px; }
  .card h2 { font-size: 15px; font-weight: 600; margin: 0 0 14px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; color: var(--text-secondary); font-weight: 500; font-size: 12px;
    padding: 6px 8px; border-bottom: 1px solid var(--border); }
  td { padding: 8px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .code { font-size: 11px; color: var(--text-muted); }
  .up { color: var(--up); }
  .down { color: var(--down); }
  .pill { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; margin: 3px 6px 3px 0; }
  .pill.in { background: var(--in-bg); color: var(--in-text); }
  .pill.out { background: var(--out-bg); color: var(--out-text); }
  .muted { color: var(--text-muted); font-size: 13px; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-bottom: 10px; font-size: 12px; color: var(--text-secondary); align-items: center; }
  .legend span { display: flex; align-items: center; gap: 4px; }
  .legend-item { display: flex; align-items: center; gap: 5px; cursor: pointer; user-select: none; }
  .legend-all { display: flex; align-items: center; gap: 5px; cursor: pointer; user-select: none;
    padding-right: 12px; border-right: 0.5px solid var(--border); font-weight: 600; color: var(--text); }
  .legend-cb, #legendAll { cursor: pointer; }
  .sw { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }
  .hist-row { padding: 10px 0; border-bottom: 0.5px solid var(--border); }
  .hist-row:last-of-type { border-bottom: none; }
  .hist-date { font-size: 13px; font-weight: 600; margin: 0 0 6px; }
  .more-btn { margin-top: 10px; width: 100%; padding: 8px; border-radius: 8px;
    border: 0.5px solid var(--border); background: var(--bg); color: var(--text);
    font-size: 13px; cursor: pointer; }
  .more-btn:hover { background: var(--card); }
  .view-toggle { display: inline-flex; background: var(--bg); border: 0.5px solid var(--border);
    border-radius: 8px; padding: 3px; gap: 2px; }
  .view-toggle button { border: none; background: transparent; padding: 5px 12px; font-size: 12px;
    border-radius: 6px; cursor: pointer; color: var(--text-secondary); font-family: inherit; }
  .view-toggle button.active { background: var(--card); color: var(--text); font-weight: 600;
    box-shadow: 0 1px 2px rgba(0,0,0,0.06); }
  .summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media (max-width: 600px) { .summary-grid { grid-template-columns: 1fr; } }
  .summary-grid h3 { font-size: 13px; font-weight: 600; margin: 0 0 8px; }
  .scroll-list { max-height: 320px; overflow-y: auto; border: 0.5px solid var(--border);
    border-radius: 8px; padding: 4px 10px; }
  .flat-row { display: flex; align-items: center; gap: 10px; font-size: 12px;
    padding: 7px 0; border-bottom: 0.5px solid var(--border); }
  .flat-row:last-child { border-bottom: none; }
  .fr-date { color: var(--text-muted); width: 78px; flex-shrink: 0; }
  .fr-name { flex: 1; }
  .fr-weight { width: 56px; text-align: right; font-variant-numeric: tabular-nums; }
  footer { text-align: center; font-size: 11px; color: var(--text-muted); margin-top: 24px; }

  /* ETF 전환 탭 */
  .etf-tabs { display: flex; gap: 6px; margin-bottom: 18px; overflow-x: auto; padding-bottom: 2px; }
  .etf-tabs button { flex: 0 0 auto; border: 0.5px solid var(--border); background: var(--card);
    color: var(--text-secondary); padding: 8px 14px; border-radius: 999px; font-size: 13px;
    cursor: pointer; font-family: inherit; white-space: nowrap; }
  .etf-tabs button.active { background: var(--accent); border-color: var(--accent);
    color: #fff; font-weight: 600; }
  .warn { background: #fff8e6; border: 0.5px solid #f0d089; color: #6b5312;
    border-radius: 10px; padding: 10px 13px; font-size: 12.5px; margin-bottom: 18px; }
  .empty-state { text-align: center; padding: 40px 16px; color: var(--text-secondary); font-size: 13px; }

  /* 좁은 화면 */
  @media (max-width: 600px) {
    body { padding: 1rem 0.85rem 2rem; }
    h1 { font-size: 17px; }
    .metric .value { font-size: 19px; }
    .card { padding: 1rem; }
    table { font-size: 12.5px; }
    td, th { padding: 7px 5px; }
  }
"""

JS_TEMPLATE = """
const ETFS = __ETFS__;
const PAYLOADS = __PAYLOADS__;
const NAME_COLORS = __NAME_COLORS__;
const BASES = __BASES__;
const GRAY = '#d3d1c7';
const VISIBLE_HISTORY = 5;

let currentTicker = ETFS[0].ticker;
let currentView = 'daily';
let trendChart = null;

const esc = (s) => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const el = (id) => document.getElementById(id);

/* ---------- ETF 탭 ---------- */
function buildTabs() {
  el('etfTabs').innerHTML = ETFS.map(e =>
    `<button type="button" data-ticker="${e.ticker}" class="${e.ticker === currentTicker ? 'active' : ''}">${esc(e.short)}</button>`
  ).join('');
  document.querySelectorAll('#etfTabs button').forEach(btn => {
    btn.addEventListener('click', () => {
      currentTicker = btn.dataset.ticker;
      document.querySelectorAll('#etfTabs button').forEach(b => b.classList.toggle('active', b === btn));
      renderEtf();
    });
  });
}

/* ---------- TOP10 표 ---------- */
function renderTop10(date) {
  const p = PAYLOADS[currentTicker];
  const rows = p.all_top10[date] || [];
  el('top10DateLabel').textContent = date;
  el('top10Body').innerHTML = rows.map(r => {
    const cls = (r.chg_bp || 0) > 0 ? 'up' : ((r.chg_bp || 0) < 0 ? 'down' : '');
    const chg = r.is_new ? '신규'
      : (r.chg_bp !== null ? (r.chg_bp > 0 ? '+' : '') + r.chg_bp.toFixed(0) + 'bp' : '-');
    return `<tr>
      <td>${r.rank}</td>
      <td>${esc(r.name)}<div class="code">${esc(r.code)}</div></td>
      <td class="num">${r.weight.toFixed(2)}%</td>
      <td class="num ${cls}">${chg}</td>
    </tr>`;
  }).join('');
}

/* ---------- 편출입 히스토리 ---------- */
function pills(items, cls) {
  if (!items.length) return '<span class="muted">변동 없음</span>';
  return items.map(it => `<span class="pill ${cls}">${esc(it.name)} (${it.weight.toFixed(2)}%)</span>`).join('');
}

function renderHistory() {
  const p = PAYLOADS[currentTicker];
  if (!p.history.length) {
    el('historyBody').innerHTML = '<p class="muted">최근 변동 내역 없음</p>';
    el('histMoreWrap').innerHTML = '';
    return;
  }
  el('historyBody').innerHTML = p.history.map((h, i) => `
    <div class="hist-row${i >= VISIBLE_HISTORY ? ' hidden-row' : ''}"${i >= VISIBLE_HISTORY ? ' style="display:none;"' : ''}>
      <p class="hist-date">${h.date} <span class="muted">(${h.prev_date} 대비)</span></p>
      <div style="margin-bottom:4px;">${pills(h.entries, 'in')}</div>
      <div>${pills(h.exits, 'out')}</div>
    </div>`).join('');

  const remaining = Math.max(0, p.history.length - VISIBLE_HISTORY);
  el('histMoreWrap').innerHTML = remaining > 0
    ? `<button class="more-btn" id="histMoreBtn">더보기 (${remaining}건)</button>` : '';
  if (remaining > 0) {
    el('histMoreBtn').addEventListener('click', function () {
      document.querySelectorAll('.hidden-row').forEach(x => x.style.display = 'block');
      this.style.display = 'none';
    });
  }
}

/* ---------- 누적 편입·편출 ---------- */
function flatRows(items, emptyMsg) {
  if (!items.length) return `<p class="muted">${emptyMsg}</p>`;
  return items.map(it => `
    <div class="flat-row">
      <span class="fr-date">${it.date}</span>
      <span class="fr-name">${esc(it.name)}<span class="code" style="margin-left:6px;">${esc(it.code)}</span></span>
      <span class="fr-weight">${it.weight.toFixed(2)}%</span>
    </div>`).join('');
}

function renderCumulative() {
  const p = PAYLOADS[currentTicker];
  el('brandNewTitle').textContent = `쌩 신규 편입 (${p.brand_new_entries.length}건)`;
  el('brandNewList').innerHTML = flatRows(p.brand_new_entries, '전체 기간 중 신규 편입 없음');
  el('allExitsTitle').textContent = `전체 편출 (${p.all_exits_flat.length}건)`;
  el('allExitsList').innerHTML = flatRows(p.all_exits_flat, '전체 기간 중 편출 없음');
}

/* ---------- 추이 차트 ---------- */
function sortNamesAlpha(names) {
  return names.slice().sort((a, b) => {
    if (a === '현금' || a === '원화예금') return -1;
    if (b === '현금' || b === '원화예금') return 1;
    return a.localeCompare(b, 'ko');
  });
}

function buildDatasets(view) {
  const colors = NAME_COLORS[currentTicker];
  const series = PAYLOADS[currentTicker].trend_views[view].series;
  return sortNamesAlpha(Object.keys(series)).map(name => ({
    label: name, data: series[name],
    borderColor: colors[name] || GRAY, backgroundColor: colors[name] || GRAY,
    spanGaps: false, tension: 0.25, pointRadius: 2, borderWidth: 2,
  }));
}

function buildLegend(datasets) {
  el('trendLegend').innerHTML =
    '<label class="legend-all"><input type="checkbox" id="legendAll" checked> 전체</label>' +
    datasets.map((d, i) =>
      `<label class="legend-item" data-idx="${i}"><input type="checkbox" class="legend-cb" data-idx="${i}" checked><span class="sw" style="background:${d.borderColor}"></span>${esc(d.label)}</label>`
    ).join('');

  el('legendAll').addEventListener('change', (e) => {
    document.querySelectorAll('.legend-cb').forEach(cb => { cb.checked = e.target.checked; });
    applySelection();
  });
  document.querySelectorAll('.legend-cb').forEach(cb => cb.addEventListener('change', applySelection));
  document.querySelectorAll('.legend-item').forEach(label => {
    label.addEventListener('click', (e) => {
      if (e.target.classList.contains('legend-cb')) return;
      e.preventDefault();
      const cb = label.querySelector('.legend-cb');
      cb.checked = !cb.checked;
      applySelection();
    });
  });
}

function applySelection() {
  const colors = NAME_COLORS[currentTicker];
  const checked = Array.from(document.querySelectorAll('.legend-cb')).map(cb => cb.checked);
  trendChart.data.datasets.forEach((ds, i) => {
    const on = checked[i];
    const orig = colors[ds.label] || GRAY;
    ds.borderColor = on ? orig : GRAY;
    ds.backgroundColor = on ? orig : GRAY;
    ds.order = on ? 0 : 1;
  });
  trendChart.update();
  el('legendAll').checked = checked.every(c => c);
}

function renderView(view) {
  currentView = view;
  if (typeof Chart === 'undefined') {
    // 차트 라이브러리를 못 불러온 경우(오프라인 등)에도 나머지 화면은 살아 있어야 한다.
    el('trendLegend').innerHTML =
      '<span class="muted">차트 라이브러리를 불러오지 못했습니다. 인터넷 연결을 확인하세요.</span>';
    return;
  }
  const datasets = buildDatasets(view);
  const labels = PAYLOADS[currentTicker].trend_views[view].dates;
  buildLegend(datasets);
  if (trendChart) {
    trendChart.data.labels = labels;
    trendChart.data.datasets = datasets;
    trendChart.update();
    return;
  }
  trendChart = new Chart(el('trendChart'), {
    type: 'line',
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { ticks: { callback: (v) => v + '%' } },
                x: { ticks: { autoSkip: true, maxRotation: 45 } } },
      interaction: { mode: 'index', intersect: false },
      onClick: (evt, _e, chart) => {
        const pts = chart.getElementsAtEventForMode(evt, 'index', { intersect: false }, true);
        if (!pts.length) return;
        const pos = Chart.helpers.getRelativePosition(evt, chart);
        let bestIdx = null, bestDist = Infinity;
        pts.forEach(p => {
          const e2 = chart.getDatasetMeta(p.datasetIndex).data[p.index];
          if (!e2 || e2.skip || typeof e2.y !== 'number' || isNaN(e2.y)) return;
          const dist = Math.abs(e2.y - pos.y);
          if (dist < bestDist) { bestDist = dist; bestIdx = p.datasetIndex; }
        });
        if (bestIdx === null) return;
        const cb = document.querySelector(`.legend-cb[data-idx="${bestIdx}"]`);
        if (cb) { cb.checked = !cb.checked; applySelection(); }
      }
    }
  });
}

/* ---------- ETF 하나를 통째로 다시 그린다 ---------- */
function renderEtf() {
  const meta = ETFS.find(e => e.ticker === currentTicker);
  const p = PAYLOADS[currentTicker];

  el('title').textContent = `${meta.name} (${meta.ticker}) — Top10 대시보드`;

  if (!p) {
    el('subtitle').textContent = '수집된 데이터가 아직 없습니다';
    el('content').style.display = 'none';
    el('emptyState').style.display = 'block';
    return;
  }
  el('content').style.display = '';
  el('emptyState').style.display = 'none';

  el('subtitle').textContent = p.prev_date
    ? `기준일 ${p.latest_date} · 전일 ${p.prev_date} 대비`
    : `기준일 ${p.latest_date} · 비교할 이전 영업일 없음`;

  const basis = BASES[currentTicker];
  el('basisWarn').style.display = (basis && basis !== 'KRX 제공 비중') ? 'block' : 'none';
  el('basisWarn').innerHTML =
    `⚠ 비중 산출 근거: <b>${esc(basis)}</b> — KRX가 이 ETF의 비중을 0으로 내려주어 대체 계산했습니다.`;

  el('mDate').textContent = p.latest_date;
  el('mIn').textContent = p.entries.length + '건';
  el('mOut').textContent = p.exits.length + '건';
  el('mDays').textContent = p.dates.length + '일';

  const sel = el('top10DateSelect');
  sel.innerHTML = p.dates.slice().reverse()
    .map(d => `<option value="${d}"${d === p.latest_date ? ' selected' : ''}>${d}</option>`).join('');
  renderTop10(p.latest_date);

  renderHistory();
  renderCumulative();

  if (trendChart) { trendChart.destroy(); trendChart = null; }
  renderView(currentView);
}

/* ---------- 초기화 ---------- */
buildTabs();
el('top10DateSelect').addEventListener('change', (e) => renderTop10(e.target.value));
document.querySelectorAll('#viewToggle button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#viewToggle button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderView(btn.dataset.view);
  });
});
renderEtf();
"""


def render(payloads: dict, bases: dict) -> str:
    etf_meta = [{"ticker": e["ticker"], "name": e["name"], "short": e["short"]} for e in ETFS]

    name_colors = {}
    for e in ETFS:
        p = payloads.get(e["ticker"])
        order = p["name_order"] if p else []
        name_colors[e["ticker"]] = {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(order)}

    js = (
        JS_TEMPLATE
        .replace("__ETFS__", json.dumps(etf_meta, ensure_ascii=False))
        .replace("__PAYLOADS__", json.dumps(payloads, ensure_ascii=False))
        .replace("__NAME_COLORS__", json.dumps(name_colors, ensure_ascii=False))
        .replace("__BASES__", json.dumps(bases, ensure_ascii=False))
    )
    generated = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>글로벌 AI ETF Top10 대시보드</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="etf-tabs" id="etfTabs"></div>

  <h1 id="title"></h1>
  <p class="sub" id="subtitle"></p>

  <div class="warn" id="basisWarn" style="display:none;"></div>

  <div id="emptyState" class="empty-state" style="display:none;">
    수집된 데이터가 아직 없습니다. 첫 수집이 성공하면 이 자리에 Top10이 나타납니다.
  </div>

  <div id="content">
    <div class="metrics">
      <div class="metric"><div class="label">기준일</div><div class="value" id="mDate"></div></div>
      <div class="metric"><div class="label">편입</div><div class="value" id="mIn"></div></div>
      <div class="metric"><div class="label">편출</div><div class="value" id="mOut"></div></div>
      <div class="metric"><div class="label">수집일수</div><div class="value" id="mDays"></div></div>
    </div>

    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
        <h2 style="margin:0;">구성종목 TOP 10 (기준일 <span id="top10DateLabel"></span>)</h2>
        <select id="top10DateSelect" style="font-size:13px; padding:5px 8px; border-radius:8px; border:0.5px solid var(--border); background:var(--card); color:var(--text);"></select>
      </div>
      <table>
        <thead><tr><th>순위</th><th>종목명</th><th style="text-align:right">비중</th><th style="text-align:right">전일대비</th></tr></thead>
        <tbody id="top10Body"></tbody>
      </table>
    </div>

    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <h2 style="margin:0;">TOP10 편출입 히스토리 (최신순)</h2>
        <div style="display:flex; gap:12px; font-size:11px; color:var(--text-secondary);">
          <span style="display:flex; align-items:center; gap:4px;"><span class="sw" style="background:var(--up);"></span>편입</span>
          <span style="display:flex; align-items:center; gap:4px;"><span class="sw" style="background:var(--down);"></span>편출</span>
        </div>
      </div>
      <div id="historyBody"></div>
      <div id="histMoreWrap"></div>
    </div>

    <div class="card">
      <h2>누적 편입 · 편출 전체보기</h2>
      <p class="muted" style="margin:-8px 0 14px;">쌩 신규 편입 = 전체 기간 중 TOP10에 처음 들어온 종목 (재편입 제외) · 전체 편출 = 전체 기간의 편출 이력 전부</p>
      <div class="summary-grid">
        <div>
          <h3 id="brandNewTitle"></h3>
          <div class="scroll-list" id="brandNewList"></div>
        </div>
        <div>
          <h3 id="allExitsTitle"></h3>
          <div class="scroll-list" id="allExitsList"></div>
        </div>
      </div>
    </div>

    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; flex-wrap:wrap; gap:8px;">
        <h2 style="margin:0;">시점별 TOP10 종목 비중 추이</h2>
        <div class="view-toggle" id="viewToggle">
          <button type="button" data-view="daily" class="active">일간</button>
          <button type="button" data-view="weekly">주간</button>
          <button type="button" data-view="monthly">월간</button>
        </div>
      </div>
      <p class="muted" style="margin:2px 0 14px;">각 날짜에 실제로 TOP10에 있었던 구간만 표시 (TOP10에서 빠지면 선이 끊김) · 일간=최근 20영업일, 주간=매주 첫 영업일, 월간=매월 첫 영업일</p>
      <div class="legend" id="trendLegend"></div>
      <div style="position:relative; height:340px;">
        <canvas id="trendChart" role="img" aria-label="선택한 기간 단위로 실제 TOP10에 포함되었던 구간만 표시한 종목 비중 추이 선 그래프"></canvas>
      </div>
    </div>
  </div>

  <footer>KRX 공시 PDF 기준 자동 생성 · pykrx · {generated} KST</footer>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>{js}</script>
</body>
</html>
"""


def main() -> int:
    payloads, bases = {}, {}
    for etf in ETFS:
        records, basis = load_records(etf["ticker"])
        payloads[etf["ticker"]] = build_payload(records)
        bases[etf["ticker"]] = basis

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(render(payloads, bases), encoding="utf-8")
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"[렌더 완료] {DOCS_DIR / 'index.html'}")
    for etf in ETFS:
        p = payloads[etf["ticker"]]
        if not p:
            print(f"  - {etf['name']}: 데이터 없음")
        else:
            print(f"  - {etf['name']}: 기준일 {p['latest_date']} · "
                  f"수집 {len(p['dates'])}일 · 편입 {len(p['entries'])} / 편출 {len(p['exits'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
