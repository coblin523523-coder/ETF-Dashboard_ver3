"""티커 -> ISIN 변환.

pykrx 의 get_etx_isin() 은 KRX의 전체 종목 목록을 내려받아 매핑하는데,
그 사전 조회가 막히면 (_get_tickers 실패) 아무것도 할 수 없게 된다.
한국 상장 ETF의 ISIN은 규칙이 정해져 있으므로 직접 계산해서 그 단계를 건너뛴다.

    KR7 + 종목코드(6) + 00 + 체크디지트(1)

체크디지트는 ISO 6166 표준(Luhn) 방식이다.
검증: 456600 -> KR7456600006, 005930 -> KR7005930003 (삼성전자)
"""

from __future__ import annotations


def _check_digit(base: str) -> str:
    converted = ""
    for ch in base:
        converted += str(ord(ch) - 55) if ch.isalpha() else ch

    total, double = 0, True
    for ch in reversed(converted):
        d = int(ch)
        if double:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        double = not double
    return str((10 - total % 10) % 10)


def ticker_to_isin(ticker: str) -> str:
    ticker = str(ticker).strip().zfill(6)
    base = f"KR7{ticker}00"
    return base + _check_digit(base)


if __name__ == "__main__":
    for t in ("456600", "471040", "466950", "005930"):
        print(t, "->", ticker_to_isin(t))
