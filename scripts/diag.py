"""KRX가 왜 응답하지 않는지 한 번에 판별하는 진단 스크립트.

    python diag.py

순서대로 확인한다.
  1. data.krx.co.kr 에 HTTP로 닿기는 하는가 (상태코드·응답 앞부분)
  2. pykrx 가 쓰는 JSON 엔드포인트가 JSON을 주는가
  3. ISIN 사전 조회를 건너뛰고 PDF를 직접 부르면 되는가
  4. KRX 로그인 자격이 있으면 결과가 달라지는가
"""

from __future__ import annotations

import json
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

TICKERS = ["456600", "471040", "466950"]


def show_response(resp: requests.Response, label: str) -> dict | None:
    print(f"    상태코드 : {resp.status_code}")
    print(f"    컨텐츠타입: {resp.headers.get('Content-Type', '(없음)')}")
    body = resp.text or ""
    print(f"    응답길이 : {len(body)}자")
    preview = body[:300].replace("\n", " ").replace("\r", "")
    print(f"    응답앞부분: {preview if preview else '(빈 응답)'}")
    try:
        data = resp.json()
        print(f"    -> JSON 파싱 성공. 최상위 키: {list(data.keys())[:8]}")
        return data
    except Exception as exc:
        print(f"    -> JSON 파싱 실패: {exc}")
        return None


def post(payload: dict, session: requests.Session) -> requests.Response:
    return session.post(BASE, data=payload, headers=HEADERS, timeout=20)


def main() -> None:
    print("=" * 66)
    print(" KRX 접근 진단")
    print("=" * 66)

    session = requests.Session()

    # ── 1. 최소 요청: 도메인에 닿는가 ──────────────────────────
    print("\n[1] data.krx.co.kr 도달 확인 (ETF 전종목 시세)")
    try:
        r = post({"bld": "dbms/MDC/STAT/standard/MDCSTAT04301",
                  "trdDd": "20260814", "share": "1", "money": "1"}, session)
        show_response(r, "전종목시세")
    except Exception as exc:
        print(f"    요청 자체 실패: {type(exc).__name__}: {exc}")
        print("\n    네트워크 레벨에서 차단되었습니다. 여기서 끝입니다.")
        return

    # ── 2. PDF 엔드포인트를 ISIN으로 직접 호출 ────────────────
    print("\n[2] PDF 엔드포인트 직접 호출 (ISIN 사전조회 건너뜀)")
    for ticker in TICKERS:
        code = ticker_to_isin(ticker)
        print(f"\n  ── {ticker} (ISIN {code})")
        try:
            r = post({"bld": "dbms/MDC/STAT/standard/MDCSTAT05001",
                      "trdDd": "20260814", "isuCd": code}, session)
            data = show_response(r, ticker)
            if data and data.get("output"):
                rows = data["output"]
                print(f"    ***** 구성종목 {len(rows)}개 수신 성공 *****")
                for row in rows[:3]:
                    print(f"      {row.get('COMPST_ISU_NM', '?')[:30]:<30} "
                          f"비중 {row.get('COMPST_RTO', '?')}")
            elif data:
                print("    JSON은 왔지만 output이 비었습니다.")
        except Exception as exc:
            print(f"    실패: {type(exc).__name__}: {exc}")

    # ── 3. 로그인 자격 여부 ───────────────────────────────────
    print("\n[3] KRX 로그인 자격")
    if os.getenv("KRX_ID") and os.getenv("KRX_PW"):
        print("    KRX_ID / KRX_PW 가 설정되어 있습니다. pykrx 로그인 경로를 시도합니다.")
        try:
            from pykrx.website.comm.auth import build_krx_session
            s = build_krx_session()
            print(f"    로그인 세션: {'성공' if s else '실패'}")
        except Exception as exc:
            print(f"    로그인 시도 중 오류: {type(exc).__name__}: {exc}")
    else:
        print("    설정되어 있지 않습니다. (Secrets 에 KRX_ID / KRX_PW 등록 시 여기서 재확인됩니다)")

    print("\n" + "=" * 66)
    print(" [2]번에서 '구성종목 N개 수신 성공' 이 보이면 pykrx로 갈 수 있습니다.")
    print(" 전부 실패했다면 KRX가 이 서버(해외 IP)를 막고 있는 것입니다.")
    print("=" * 66)


if __name__ == "__main__":
    sys.exit(main())
