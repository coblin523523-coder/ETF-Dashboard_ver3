"""KRX 접근 상태를 한 번에 판별하는 진단 스크립트.

    python scripts/diag.py

KRX 정보데이터시스템은 2025년 12월부터 회원제(KRX Data Marketplace)로 바뀌어
비로그인 요청에는 HTTP 400 + 본문 "LOGOUT" 을 돌려준다.
따라서 확인해야 할 것은 두 가지다.

  1. 비로그인 상태에서 정확히 어떤 거절을 받는가
  2. KRX_ID / KRX_PW 로 로그인하면 실제로 데이터가 내려오는가
"""

from __future__ import annotations

import os
import sys

import requests

from isin import ticker_to_isin

BASE = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

TICKERS = [
    ("456600", "TIMEFOLIO 글로벌AI인공지능액티브"),
    ("471040", "KoAct 글로벌AI&로봇액티브"),
    ("466950", "TIGER 글로벌AI액티브"),
]
PROBE_DATE = "20260814"


def describe(resp: requests.Response) -> dict | None:
    body = (resp.text or "").strip()
    print(f"    상태코드 : {resp.status_code}")
    print(f"    응답길이 : {len(body)}자")
    print(f"    응답앞부분: {body[:200] if body else '(빈 응답)'}")
    if body.upper() == "LOGOUT":
        print("    -> 로그인 세션이 없다는 거절입니다.")
        return None
    try:
        return resp.json()
    except Exception as exc:
        print(f"    -> JSON 파싱 실패: {exc}")
        return None


def report_rows(data: dict, label: str) -> bool:
    rows = data.get("output") or []
    if not rows:
        print("    JSON은 왔지만 output 이 비었습니다.")
        return False

    print(f"    ***** 구성종목 {len(rows)}개 수신 성공 *****")
    weights = []
    for row in rows[:5]:
        rto = row.get("COMPST_RTO", "0")
        weights.append(rto)
        print(f"      {str(row.get('COMPST_ISU_NM', '?'))[:32]:<32} 비중 {rto}")

    try:
        total = sum(float(str(r.get("COMPST_RTO", "0")).replace(",", "") or 0) for r in rows)
    except Exception:
        total = 0.0
    print(f"    비중 합계 = {total:.2f}%  ->  {'정상' if total > 0 else '0! 금액으로 환산 필요'}")
    return True


def main() -> None:
    print("=" * 66)
    print(" KRX 접근 진단")
    print("=" * 66)

    # ── 1. 비로그인 상태 확인 ──────────────────────────────────
    print("\n[1] 비로그인 상태로 요청")
    plain = requests.Session()
    try:
        r = plain.post(BASE, data={"bld": "dbms/MDC/STAT/standard/MDCSTAT05001",
                                   "trdDd": PROBE_DATE,
                                   "isuCd": ticker_to_isin("456600")},
                       headers=HEADERS, timeout=20)
        describe(r)
    except Exception as exc:
        print(f"    요청 자체 실패: {type(exc).__name__}: {exc}")
        print("\n    네트워크 레벨 차단입니다. 계정으로도 해결되지 않습니다.")
        return

    # ── 2. 로그인 ─────────────────────────────────────────────
    print("\n[2] KRX 로그인")
    if not (os.getenv("KRX_ID") and os.getenv("KRX_PW")):
        print("    KRX_ID / KRX_PW 가 설정되어 있지 않습니다.")
        print("    -> data.krx.co.kr 에서 회원가입 후 저장소 Secrets 에 등록하세요.")
        print("\n" + "=" * 66)
        print(" 결론: KRX가 회원제로 바뀌어 로그인 없이는 불가합니다.")
        print("=" * 66)
        return

    try:
        from pykrx.website.comm.auth import build_krx_session
        krxs = build_krx_session()
    except Exception as exc:
        print(f"    로그인 중 오류: {type(exc).__name__}: {exc}")
        krxs = None

    if not krxs:
        print("\n    로그인 실패. 아이디/비밀번호를 확인하세요.")
        print("    (KRX는 일정 기간마다 비밀번호 변경을 강제하기도 합니다)")
        return
    print("    로그인 성공.")

    # ── 3. 로그인 세션으로 PDF 조회 ───────────────────────────
    print(f"\n[3] 로그인 세션으로 PDF 조회 (기준일 {PROBE_DATE})")
    ok_count = 0
    for ticker, label in TICKERS:
        print(f"\n  ── {label} ({ticker} / {ticker_to_isin(ticker)})")
        try:
            r = krxs.session.post(
                BASE,
                data={"bld": "dbms/MDC/STAT/standard/MDCSTAT05001",
                      "trdDd": PROBE_DATE, "isuCd": ticker_to_isin(ticker)},
                headers=HEADERS, timeout=20,
            )
            data = describe(r)
            if data and report_rows(data, label):
                ok_count += 1
        except Exception as exc:
            print(f"    실패: {type(exc).__name__}: {exc}")

    # ── 4. 과거 소급 ──────────────────────────────────────────
    print("\n[4] 과거 날짜 소급 조회 (456600)")
    for probe in ("20260601", "20260401", "20260102"):
        try:
            r = krxs.session.post(
                BASE,
                data={"bld": "dbms/MDC/STAT/standard/MDCSTAT05001",
                      "trdDd": probe, "isuCd": ticker_to_isin("456600")},
                headers=HEADERS, timeout=20,
            )
            data = r.json() if r.status_code == 200 else None
            n = len(data.get("output") or []) if data else 0
            print(f"    {probe} : {f'가능 - {n}종목' if n else '불가'}")
        except Exception:
            print(f"    {probe} : 불가")

    print("\n" + "=" * 66)
    print(f" 결론: 3종 중 {ok_count}종 수신 성공")
    print("=" * 66)


if __name__ == "__main__":
    sys.exit(main())
