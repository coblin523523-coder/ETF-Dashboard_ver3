"""대시보드 공통 설정."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

# 추적 대상 ETF. 순서가 대시보드 탭 순서가 된다.
ETFS = [
    {"ticker": "456600", "name": "TIMEFOLIO 글로벌AI인공지능액티브", "short": "TIMEFOLIO AI"},
    {"ticker": "471040", "name": "KoAct 글로벌AI&로봇액티브", "short": "KoAct AI·로봇"},
    {"ticker": "466950", "name": "TIGER 글로벌AI액티브", "short": "TIGER AI"},
]

# 대시보드에 노출할 상위 종목 수
TOP_N = 10

# 스파크라인에 사용할 최근 영업일 수
SPARK_DAYS = 20

# CSV 컬럼 (pykrx get_etf_portfolio_deposit_file 기준)
PDF_COLUMNS = ["티커", "구성종목명", "계약수", "금액", "시가총액", "비중"]
