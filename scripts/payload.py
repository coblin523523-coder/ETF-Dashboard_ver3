"""수집된 CSV를 대시보드용 payload 로 가공한다.

집계 로직(TOP10, 편출입 히스토리, 쌩 신규 편입, 멤버십 기반 추이)은
사용자가 이미 쓰던 build_dashboard.py 의 구조를 그대로 따랐다.
입력만 엑셀 Raw 시트에서 pykrx CSV 로 바뀌었다.
"""

from __future__ import annotations

import collections
import datetime

import pandas as pd

from config import DATA_DIR

TOP_N = 10
DAILY_WINDOW = 20


def _iso(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


def _resolve_weight(df: pd.DataFrame) -> tuple[pd.Series, str]:
    """비중을 확정한다.

    해외 자산 편입 ETF는 KRX가 '비중'을 0으로 내려주는 경우가 있어
    비중 → 금액 → 시가총액 순으로 대체 계산하고 그 근거를 함께 돌려준다.
    """
    for col, label in (
        ("비중", "KRX 제공 비중"),
        ("금액", "평가금액 환산"),
        ("시가총액", "시가총액 환산"),
    ):
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        total = s.sum()
        if total > 0:
            return (s if col == "비중" else s / total * 100.0), label
    return pd.Series([0.0] * len(df), index=df.index), "산출 불가"


def load_records(ticker: str) -> tuple[list[dict], str]:
    """data/<ticker>/*.csv 전체를 레코드 목록으로 읽는다."""
    d = DATA_DIR / ticker
    if not d.exists():
        return [], ""

    records: list[dict] = []
    basis = ""
    for path in sorted(d.glob("*.csv")):
        date = _iso(path.stem)
        df = pd.read_csv(path, dtype={"티커": str})
        if df.empty:
            continue
        df["티커"] = df["티커"].fillna("").astype(str).str.strip()
        df["구성종목명"] = df["구성종목명"].fillna("").astype(str).str.strip()

        weights, basis = _resolve_weight(df)
        for (_, row), w in zip(df.iterrows(), weights):
            name = row["구성종목명"]
            code = row["티커"] or ("CASH" if name in ("원화예금", "현금") else name)
            records.append(
                {"date": date, "code": code, "name": name, "weight": float(w)}
            )
    return records, basis


def compute_trend_view(view_dates, top10_by_date, code_to_name) -> dict:
    """멤버십 기반 추이: 그 날짜의 TOP10에 실제로 있었던 구간만 값을 채운다."""
    member_codes, seen = [], set()
    for d in view_dates:
        for r in top10_by_date[d]:
            if r["code"] not in seen:
                seen.add(r["code"])
                member_codes.append(r["code"])

    series = {}
    for code in member_codes:
        vals = []
        for d in view_dates:
            m = next((x for x in top10_by_date[d] if x["code"] == code), None)
            vals.append(round(m["weight"], 2) if m else None)
        series[code_to_name.get(code, code)] = vals
    return {"dates": view_dates, "series": series}


def build_payload(records: list[dict]) -> dict | None:
    if not records:
        return None

    by_date = collections.defaultdict(list)
    for r in records:
        by_date[r["date"]].append(r)
    dates = sorted(by_date.keys())

    def top10(d):
        return sorted(by_date[d], key=lambda r: -r["weight"])[:TOP_N]

    latest = dates[-1]
    prev = dates[-2] if len(dates) >= 2 else None

    latest_top10 = top10(latest)
    prev_top10 = top10(prev) if prev else []
    prev_codes = {r["code"] for r in prev_top10}
    latest_codes = {r["code"] for r in latest_top10}
    prev_weight_map = {r["code"]: r["weight"] for r in by_date[prev]} if prev else {}

    # 날짜 드롭다운용: 모든 날짜의 TOP10을 미리 계산해 둔다
    all_top10 = {}
    for i, d in enumerate(dates):
        d_prev = {r["code"]: r["weight"] for r in by_date[dates[i - 1]]} if i > 0 else {}
        rows = []
        for rank, r in enumerate(top10(d), 1):
            pw = d_prev.get(r["code"])
            rows.append({
                "rank": rank, "code": r["code"], "name": r["name"],
                "weight": round(r["weight"], 2),
                "chg_bp": None if pw is None else round((r["weight"] - pw) * 100, 1),
                "is_new": i > 0 and pw is None,
            })
        all_top10[d] = rows

    entries = [r for r in latest_top10 if prev and r["code"] not in prev_codes]
    exits = [r for r in prev_top10 if r["code"] not in latest_codes]

    # 날짜별 편출입 히스토리
    history = []
    for i in range(1, len(dates)):
        pd_, cd = dates[i - 1], dates[i]
        pt, ct = top10(pd_), top10(cd)
        pcodes, ccodes = {r["code"] for r in pt}, {r["code"] for r in ct}
        ent = [{"code": r["code"], "name": r["name"], "weight": round(r["weight"], 2)}
               for r in ct if r["code"] not in pcodes]
        ext = [{"code": r["code"], "name": r["name"], "weight": round(r["weight"], 2)}
               for r in pt if r["code"] not in ccodes]
        if ent or ext:
            history.append({"date": cd, "prev_date": pd_, "entries": ent, "exits": ext})
    history.sort(key=lambda h: h["date"], reverse=True)

    # 쌩 신규 편입: 추적 기간 중 TOP10에 처음 들어온 종목.
    # 첫날부터 있던 종목은 그 이전 이력을 모르므로 제외한다.
    baseline = {r["code"] for r in top10(dates[0])}
    first_seen = {}
    for d in dates:
        for r in top10(d):
            first_seen.setdefault(r["code"], {
                "date": d, "code": r["code"], "name": r["name"],
                "weight": round(r["weight"], 2),
            })
    brand_new = [v for c, v in first_seen.items() if c not in baseline]
    brand_new.sort(key=lambda x: x["date"], reverse=True)

    all_exits_flat = [
        {"date": h["date"], "prev_date": h["prev_date"], "code": ex["code"],
         "name": ex["name"], "weight": ex["weight"]}
        for h in history for ex in h["exits"]
    ]

    top10_by_date = {d: top10(d) for d in dates}
    code_to_name = {}
    for d in dates:
        for r in by_date[d]:
            code_to_name[r["code"]] = r["name"]

    # 일간/주간/월간 토글 사이에서 종목 색이 흔들리지 않도록 전역 등장 순서를 고정
    order, seen_all = [], set()
    for d in dates:
        for r in top10_by_date[d]:
            if r["code"] not in seen_all:
                seen_all.add(r["code"])
                order.append(r["code"])

    daily_dates = dates[-DAILY_WINDOW:] if len(dates) > DAILY_WINDOW else dates[:]

    weekly, monthly = {}, {}
    for d in dates:
        dt = datetime.date.fromisoformat(d)
        wk = (dt.isocalendar()[0], dt.isocalendar()[1])
        if wk not in weekly or d < weekly[wk]:
            weekly[wk] = d
        mk = (dt.year, dt.month)
        if mk not in monthly or d < monthly[mk]:
            monthly[mk] = d

    return {
        "latest_date": latest,
        "prev_date": prev,
        "dates": dates,
        "top10": all_top10[latest],
        "entries": [{"code": r["code"], "name": r["name"], "weight": round(r["weight"], 2)} for r in entries],
        "exits": [{"code": r["code"], "name": r["name"], "weight": round(r["weight"], 2)} for r in exits],
        "history": history,
        "all_top10": all_top10,
        "trend_views": {
            "daily": compute_trend_view(daily_dates, top10_by_date, code_to_name),
            "weekly": compute_trend_view(sorted(weekly.values()), top10_by_date, code_to_name),
            "monthly": compute_trend_view(sorted(monthly.values()), top10_by_date, code_to_name),
        },
        "name_order": [code_to_name.get(c, c) for c in order],
        "brand_new_entries": brand_new,
        "all_exits_flat": all_exits_flat,
    }
