# 글로벌 AI ETF 구성종목 대시보드

pykrx로 매일 아침 ETF 3종의 구성종목(PDF, Portfolio Deposit File)을 수집해
**전일 대비 편입·편출·비중 증감**을 보여주는 정적 대시보드입니다.
PC를 켜둘 필요 없이 GitHub Actions가 대신 돌립니다.

| 코드 | ETF |
|---|---|
| 456600 | TIMEFOLIO 글로벌AI인공지능액티브 |
| 471040 | KoAct 글로벌AI&로봇액티브 |
| 466950 | TIGER 글로벌AI액티브 |

## 구조

```
scripts/collect.py   KRX에서 구성종목을 받아 data/ 에 CSV로 누적
scripts/payload.py   TOP10·편출입 히스토리·추이 집계
scripts/render.py    docs/index.html 생성
scripts/make_mock.py 가짜 데이터 생성 (화면 확인용)
.github/workflows/daily.yml  매일 07:00 KST 자동 실행
data/                날짜별 CSV가 쌓이는 곳 = 이력 그 자체
docs/index.html      대시보드 (GitHub Pages가 이 파일을 서빙)
```

화면 구성은 기존에 쓰던 `top10_dashboard.html` 형식을 그대로 따랐습니다.
상단 메트릭 4종(기준일·편입·편출·수집일수), 날짜 드롭다운이 달린 TOP10 표,
편출입 히스토리, 누적 편입·편출 전체보기, 일간/주간/월간 추이 차트가 동일하며
**맨 위에 ETF 3종을 전환하는 탭만 추가**했습니다.

## 설치 (처음 한 번)

### 1. 저장소 만들기

GitHub에서 새 저장소를 만듭니다. **Public** 으로 만드세요 —
Actions와 Pages를 무료로 쓰려면 공개 저장소여야 합니다.
이 폴더의 파일 전부를 그 저장소에 올립니다.

### 2. Actions에 쓰기 권한 주기

`Settings → Actions → General → Workflow permissions`
→ **Read and write permissions** 선택 → Save

이게 없으면 수집한 데이터를 저장소에 커밋하지 못하고 실패합니다.

### 3. Pages 켜기

`Settings → Pages`
→ Source: **Deploy from a branch**
→ Branch: **main** / 폴더: **/docs** → Save

몇 분 뒤 아래 주소가 열립니다.

```
https://coblin523523-coder.github.io/<저장소이름>/
```

### 4. (선택) KRX 계정 등록

KRX가 비로그인 조회를 막을 경우를 대비한 보험입니다.

`Settings → Secrets and variables → Actions → New repository secret`
→ `KRX_ID` / `KRX_PW` 두 개 등록

한 번 넣으면 다시 볼 수 없고, 로그에도 `***` 로 가려집니다.

### 5. 첫 실행

`Actions` 탭 → `일별 ETF 구성종목 수집` → **Run workflow**
→ backfill 값을 `30` 쯤으로 넣고 실행

**이 첫 실행이 가장 중요한 검증입니다.** 로그를 보면 세 가지 중 하나가 나옵니다.

- 과거 날짜까지 `N종목 저장` 이 찍힌다 → KRX가 소급 조회를 허용. 바로 이력이 생깁니다.
- 최근 하루이틀만 저장된다 → 소급은 불가. **오늘부터 하루씩 쌓입니다.** 내일부터 비교가 나옵니다.
- 전부 `조회 실패` → KRX가 GitHub 서버 IP를 막은 것. 4번의 KRX 계정을 등록하고 재시도하세요.

## 로컬에서 화면만 미리 보기

```bash
pip install -r requirements.txt
python scripts/make_mock.py    # 가짜 데이터 생성
python scripts/render.py       # docs/index.html 생성
```

실제 수집을 시작하기 전에 `data/` 안의 가짜 데이터는 지우세요.

## 실행 시각 바꾸기

`.github/workflows/daily.yml` 의 cron은 **UTC** 기준입니다.

```yaml
- cron: "0 22 * * 0-4"   # 22:00 UTC = 다음날 07:00 KST, 월~금
```

KST 시각에서 9시간을 빼면 UTC입니다. 9시간을 빼서 날짜가 하루 넘어가면
요일 필드도 함께 하루 당겨야 합니다.

## 알아둘 점

- **비중이 0으로 내려올 수 있습니다.** 해외 자산 편입 ETF는 KRX가 비중을 0으로 주는
  경우가 있어, 그때는 평가금액으로 비중을 환산하고 대시보드 상단에 그 사실을 표시합니다.
- **휴장일에는 아무것도 저장되지 않습니다.** 워크플로는 실패가 아니라 정상 종료합니다.
- **Actions cron은 60일간 저장소 활동이 없으면 자동 정지됩니다.** 다만 이 워크플로는
  매일 커밋을 하므로 스스로 활동을 만들어 사실상 문제되지 않습니다.
- 매일 `--backfill 5` 로 돌기 때문에 며칠 실패해도 다음 성공 실행에서 자동으로 메꿉니다.

## 면책

KRX 공시 자료를 가공한 정보 제공용 페이지입니다. 투자 판단의 근거로 삼기 전에
반드시 운용사 원 공시를 확인하세요.
