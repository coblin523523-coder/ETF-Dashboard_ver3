"""KRX 접속 없이 대시보드를 검증하기 위한 모의 데이터 생성기.

    python scripts/make_mock.py

data/ 에 가짜 CSV를 채워 넣고 render.py 를 돌리면 화면이 어떻게 보이는지 확인할 수 있다.
실제 수집을 시작하기 전에 data/ 폴더를 비우면 된다.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

import pandas as pd

from config import DATA_DIR, ETFS

random.seed(7)

UNIVERSE = [
    ("NVDA", "NVIDIA CORP"), ("MSFT", "MICROSOFT CORP"), ("AAPL", "APPLE INC"),
    ("GOOGL", "ALPHABET INC-CL A"), ("AMZN", "AMAZON.COM INC"), ("META", "META PLATFORMS INC"),
    ("AVGO", "BROADCOM INC"), ("TSM", "TAIWAN SEMICONDUCTOR"), ("AMD", "ADVANCED MICRO DEVICES"),
    ("PLTR", "PALANTIR TECHNOLOGIES"), ("MU", "MICRON TECHNOLOGY"), ("ARM", "ARM HOLDINGS"),
    ("CRM", "SALESFORCE INC"), ("ORCL", "ORACLE CORP"), ("VRT", "VERTIV HOLDINGS"),
    ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("042700", "한미반도체"),
    ("SNOW", "SNOWFLAKE INC"), ("NOW", "SERVICENOW INC"), ("DELL", "DELL TECHNOLOGIES"),
]


def business_days(n: int) -> list[str]:
    out, cur = [], datetime(2026, 8, 18)
    while len(out) < n:
        if cur.weekday() < 5:
            out.append(cur.strftime("%Y%m%d"))
        cur -= timedelta(days=1)
    return sorted(out)


def main() -> None:
    dates = business_days(22)

    for etf in ETFS:
        ticker = etf["ticker"]
        out_dir = DATA_DIR / ticker
        out_dir.mkdir(parents=True, exist_ok=True)

        pool = UNIVERSE.copy()
        random.shuffle(pool)
        holdings = pool[:16]
        weights = {t: random.uniform(1.5, 9.0) for t, _ in holdings}
        quotes = {}

        for i, date in enumerate(dates):
            # 비중을 조금씩 흔든다
            for t in list(weights):
                weights[t] = max(0.4, weights[t] * random.uniform(0.94, 1.06))

            # 마지막 날에는 편입/편출을 하나씩 일으켜 diff 로직을 검증한다
            if i == len(dates) - 1:
                dropped = random.choice(list(weights))
                del weights[dropped]
                spare = [x for x in UNIVERSE if x[0] not in weights and x[0] != dropped]
                if spare:
                    new_t, _ = random.choice(spare)
                    weights[new_t] = random.uniform(2.0, 5.5)

            names = dict(UNIVERSE)
            total = sum(weights.values())
            rows = [
                {
                    "티커": t,
                    "구성종목명": names[t],
                    "계약수": round(random.uniform(50, 5000), 2),
                    "금액": int(w / total * 1e10),
                    "시가총액": int(w / total * 1.02e10),
                    "비중": round(w / total * 96.5, 2),  # 나머지는 현금
                }
                for t, w in weights.items()
            ]
            rows.append({
                "티커": "KRW", "구성종목명": "원화예금", "계약수": 0,
                "금액": int(0.035 * 1e10), "시가총액": int(0.035 * 1e10), "비중": 3.5,
            })
            pd.DataFrame(rows).to_csv(out_dir / f"{date}.csv", index=False, encoding="utf-8-sig")
            quotes[date] = {"종가": round(random.uniform(11000, 16000), 0), "NAV": 0, "거래량": 0}

        (out_dir / "quotes.json").write_text(
            json.dumps(quotes, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"  모의 데이터 생성: {etf['name']} ({ticker}) {len(dates)}일")


if __name__ == "__main__":
    main()
