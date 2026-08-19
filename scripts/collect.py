"""ETF 구성종목(PDF, Portfolio Deposit File)을 매일 수집해 data/ 에 누적 저장한다.

사용법
------
    python scripts/collect.py                 # 오늘(KST) 기준 수집
    python scripts/collect.py --date 20260817 # 특정일 수집
    python scripts/collect.py --backfill 30   # 과거 30 영업일 소급 수집 시도

과거 소급(backfill)이 되는지는 KRX가 응답을 주느냐에 달려 있다.
처음 한 번 --backfill 을 돌려보고, 데이터가 쌓이면 그날부터 비교가 가능하다.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from pykrx import stock

from config import DATA_DIR, ETFS, PDF_COLUMNS

KST = ZoneInfo("Asia/Seoul")


def today_kst() -> str:
    return datetime.now(KST).strftime("%Y%m%d")


def now_kst_iso() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def business_days_back(end: str, count: int) -> list[str]:
    """end 로부터 과거로 거슬러 올라가며 주말을 제외한 날짜 문자열 목록을 만든다.

    공휴일은 걸러내지 못하지만, 휴장일은 KRX가 빈 응답을 주므로 수집 단계에서
    자연히 걸러진다.
    """
    days: list[str] = []
    cursor = datetime.strptime(end, "%Y%m%d")
    while len(days) < count:
        if cursor.weekday() < 5:  # 0=월 ... 4=금
            days.append(cursor.strftime("%Y%m%d"))
        cursor -= timedelta(days=1)
    return days


def fetch_pdf(date: str, ticker: str) -> pd.DataFrame | None:
    """특정일·특정 ETF의 구성종목을 조회한다. 실패하거나 비면 None."""
    try:
        df = stock.get_etf_portfolio_deposit_file(date, ticker)
    except Exception as exc:  # 네트워크·파싱 오류 모두 여기로
        print(f"    [!] {ticker} {date} 조회 실패: {type(exc).__name__}: {exc}")
        return None

    if df is None or df.empty:
        return None

    df = df.reset_index()
    for col in PDF_COLUMNS:
        if col not in df.columns:
            print(f"    [!] {ticker} {date} 예상 컬럼 없음: {col}")
            return None
    return df[PDF_COLUMNS]


def fetch_quote(date: str, ticker: str) -> dict:
    """ETF 자체의 종가·NAV. 실패해도 대시보드는 동작해야 하므로 조용히 넘어간다."""
    try:
        df = stock.get_etf_ohlcv_by_date(date, date, ticker)
        if df is None or df.empty:
            return {}
        row = df.iloc[-1]
        return {
            "종가": float(row.get("종가", 0) or 0),
            "NAV": float(row.get("NAV", 0) or 0),
            "거래량": float(row.get("거래량", 0) or 0),
        }
    except Exception:
        return {}


def save(ticker: str, date: str, df: pd.DataFrame, quote: dict) -> None:
    out_dir = DATA_DIR / ticker
    out_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_dir / f"{date}.csv", index=False, encoding="utf-8-sig")

    if quote:
        quote_path = out_dir / "quotes.json"
        quotes = {}
        if quote_path.exists():
            quotes = json.loads(quote_path.read_text(encoding="utf-8"))
        quotes[date] = quote
        quote_path.write_text(
            json.dumps(quotes, ensure_ascii=False, indent=1), encoding="utf-8"
        )


def collect_one_day(date: str, force: bool = False) -> int:
    """하루치를 수집한다. 저장에 성공한 ETF 개수를 반환."""
    saved = 0
    for etf in ETFS:
        ticker, name = etf["ticker"], etf["name"]
        target = DATA_DIR / ticker / f"{date}.csv"
        if target.exists() and not force:
            print(f"    - {name} ({ticker}) {date}: 이미 있음, 건너뜀")
            saved += 1
            continue

        df = fetch_pdf(date, ticker)
        if df is None:
            print(f"    - {name} ({ticker}) {date}: 데이터 없음 (휴장일이거나 미제공)")
            continue

        save(ticker, date, df, fetch_quote(date, ticker))
        print(f"    - {name} ({ticker}) {date}: {len(df)}종목 저장")
        saved += 1
        time.sleep(0.6)  # KRX 서버 배려
    return saved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="수집 기준일 YYYYMMDD (기본: 오늘 KST)")
    parser.add_argument(
        "--backfill", type=int, default=0, help="과거 N 영업일까지 소급 수집 시도"
    )
    parser.add_argument("--force", action="store_true", help="이미 있는 날도 다시 받기")
    args = parser.parse_args()

    end = args.date or today_kst()
    print(f"[수집 시작] 기준일 {end} / 현재 {now_kst_iso()}")

    if args.backfill > 0:
        dates = business_days_back(end, args.backfill)
        print(f"  소급 수집: {dates[-1]} ~ {dates[0]} ({len(dates)}일)")
    else:
        dates = [end]

    total = 0
    for date in dates:
        print(f"  · {date}")
        total += collect_one_day(date, force=args.force)

    print(f"[수집 완료] 저장/확인된 (ETF×일자) 건수: {total}")

    if total == 0:
        print(
            "\n수집된 데이터가 하나도 없습니다.\n"
            "  - 오늘이 휴장일이면 정상입니다.\n"
            "  - 그게 아니라면 KRX 접근이 막혔을 수 있습니다. "
            "저장소 Secrets 에 KRX_ID / KRX_PW 를 넣어보세요."
        )
        # 휴장일에 워크플로가 빨갛게 실패하지 않도록 0으로 끝낸다.
    return 0


if __name__ == "__main__":
    sys.exit(main())
