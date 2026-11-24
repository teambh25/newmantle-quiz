# Google Trends 수집 방식 변경 (trendspy → RSS 주기 수집)

> trendspy가 쓰는 Google Trends 비공개 API가 막혀 `recommend_answer` DAG의 트렌드 후보 생성이 실패하는 문제를 정리하고, 공식 RSS 피드를 주기적으로 수집해 Airflow Variable에 쌓아두는 방식으로 전환하는 계획을 기록한다.

## 1. Overview

`recommend_answer` DAG의 `get_trends` task는 trendspy로 Google Trends "Trending now"(최근 N시간, 검색량 순)를 가져온 뒤 트렌드별 뉴스 제목을 붙여서 Gemini 프롬프트(`prompts/trend`)에 넣는다.
2026년 10월 말부터 trendspy 호출이 간헐적으로 실패하기 시작했고, 2026-11-11에는 모든 요청이 실패하는 상태가 되었다.

## 2. 이슈 이력

### 2-1. 트렌드 조회 시 뉴스가 null로 옴 (해결: `c2bc7d3`, 2026-10-31)
- 증상: `trending_now(..., num_news=N)`으로 뉴스를 함께 요청하면 뉴스 필드가 null로 오는 경우가 생김
- 조치: 트렌드는 `num_news=0`으로 받고, 뉴스는 `trending_now_news_by_ids(news_tokens)`로 트렌드마다 따로 조회하도록 변경

### 2-2. 뉴스 조회 시 `IndexError` (해결: `9754633`)
```
trendspy/client.py, line 610, in trending_now_news_by_ids
    data = list(map(NewsArticle.from_api, data[0]))
IndexError: list index out of range
```
- 원인: Google이 해당 news token에 대해 빈 payload(`[]`)를 돌려줌. 스포츠 경기처럼 금방 지나가는 트렌드에서 자주 발생. trendspy가 빈 응답을 확인하지 않고 `data[0]`에 접근해서 발생
- 우리 코드의 문제: `except Exception: raise` 때문에 트렌드 하나에서 기사를 못 받으면 task 전체가 실패함
- 조치
  - `IndexError`는 "기사 없음"으로 보고 해당 트렌드만 건너뜀
  - 기존에는 상위 `limit`개로 먼저 자른 뒤 뉴스를 조회해서, 건너뛴 만큼 반환 개수가 줄었음 → 다음 순위 트렌드로 `limit`개를 채우도록 변경

### 2-3. 트렌드 조회 시 `TypeError` (임시 해결: `9754633`)
```
trendspy/client.py, line 575, in trending_now
    data = json.loads(data[0][2])
TypeError: the JSON object must be str, bytes or bytearray, not NoneType
```
- 원인: batchexecute 응답에서 데이터 자리(`[2]`)가 `null`로 옴. batchexecute는 서버에서 요청을 거절하면 HTTP 200을 주면서 데이터 자리를 비워 보냄
- 확인: `hours` 값별로 null 응답 비율을 비교하는 테스트(`airflow/dags/test.py`, 커밋하지 않음)를 돌렸더니 `hours=72`에서만 실패함. 72는 Trending now UI의 기간 선택지(4/24/48/168시간)에 없는 값
- 조치: `hours=72` → `hours=48`
- 남은 의문: 예전에는 72도 항상 실패하지는 않았음. 2-1의 null도 실제 원인은 72였을 가능성이 있음

### 2-4. 모든 기간에서 null 응답 (미해결, 이 문서의 대상)
- 증상: 2-3 조치 1주일 뒤, `test.py`를 돌리면 4/24/48/72/168시간 모두 null
- raw 응답:
  ```
  [["wrb.fr","i0OFE",null,null,null,[7],"generic"], ...]
  ```
  에러 코드 `7`은 gRPC 상태 코드로 `PERMISSION_DENIED`
- IP 밴인지 확인한 결과: **IP 밴은 아님**
  - 같은 IP에서 브라우저로 `https://trends.google.com/trending?geo=KR`을 열면 목록이 정상적으로 나옴
  - 같은 IP에서 같은 도메인의 RSS(`/trending/rss?geo=KR`)도 정상
  - IP 단위 제한이었다면 보통 HTTP 429나 캡차 페이지가 옴
- 결론: Google이 이 내부 API에 **브라우저 세션(쿠키·토큰)을 요구하도록 바뀐 것**으로 보임. 2-3에서 성공과 실패가 섞여 나오던 것도 이 변경이 서버별로 순차 배포되던 과정으로 볼 수 있음
- trendspy 저장소는 2025년 10월 이후 활동이 거의 없어서 라이브러리 쪽 수정을 기대하기 어려움

## 3. 해결 방안 검토

| 방안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **A. RSS 주기 수집 + 버퍼 적재 (채택)** | 2시간마다 RSS를 수집해 Airflow Variable에 쌓고, 추천 DAG는 최근 48시간을 사용 | 공식 공개 피드라 안정적. 뉴스 제목이 포함돼서 추가 호출 없음. 기존 동작(48시간, 검색량 순 상위 N개)을 거의 그대로 유지 | 도입 직후 48시간 동안은 데이터가 부족함. 피드에 짧게 떴다 사라진 트렌드는 놓칠 수 있음 |
| B. 실행할 때 RSS 한 번 호출 | `fetch_google_trends`를 RSS 호출 한 번으로 교체 | 변경이 가장 작음 | RSS는 최근 약 2시간, 10개만 제공. 후보가 크게 빈약해짐 |
| C. 트렌드 소스 제거 | Gemini + Google Search(common sense 후보)에 맡김 | 외부 의존성 감소 | 실제 검색량이라는 근거가 사라짐 |
| D. 브라우저 흉내 | 페이지에서 쿠키·토큰을 추출해 batchexecute 호출, 또는 Playwright 같은 headless 브라우저 사용 | 기존 데이터(기간 지정)를 그대로 얻음 | Google이 의도적으로 막은 접근을 우회하는 방식이라 다시 막힐 가능성이 큼. headless는 이미지가 무거워지고 자동화 감지에 걸릴 수 있음 |

### RSS 피드 확인 결과 (2026-11-11)
- URL: `https://trends.google.com/trending/rss?geo=KR`
- item 10개, `pubDate` 범위는 약 2시간. 최신순으로 정렬되어 있고 검색량 순이 아님
- item마다 들어 있는 필드: `title`, `ht:approx_traffic`(예: `"2000+"`), `pubDate`, `ht:news_item` 3개(`ht:news_item_title`, `ht:news_item_url`, `ht:news_item_source`)
- 기존 trendspy 결과에 있던 연관 키워드(`trend_keywords`)는 없음
- `xsmb`(베트남 복권)처럼 한국어 게임과 관계없는 키워드도 섞여 있음

### 저장소: Airflow Variable
트렌드 데이터는 추천에만 쓰고, 48시간이 지나면 필요 없는 일회성 데이터라서 별도 테이블은 만들지 않는다.

| | Airflow Variable (채택) | 파일 (`data/trends/buffer.json`) | DB 테이블 |
|---|---|---|---|
| 추가 설정 | 없음 | 볼륨 마운트 추가 + 컨테이너 재생성 | 테이블 생성, 운영 DB에 DDL 직접 실행 |
| 데이터 유지 | Airflow 메타 DB에 저장되어 컨테이너를 재생성해도 남음 | 마운트한 경우에만 남음 | 남음 |
| 확인 | Airflow UI(Admin → Variables) | 호스트에서 바로 확인 | psql |
| 쓰기 안전성 | DB 트랜잭션이라 쓰다가 끊겨도 깨지지 않음 | 쓰다가 끊기면 JSON이 깨질 수 있음 (임시 파일 + rename 필요) | 안전 |
| 적합한 경우 | 일회성 버퍼 | 일회성 버퍼 | 트렌드 이력을 분석하거나 다른 곳에서도 쓸 때 |

데이터 크기: RSS는 한 번에 10개이고, 2시간마다 48시간 동안 수집하면 최대 240개다. 중복을 합치면 실제로는 더 적어서 Variable 크기는 문제가 없다.

### RSS 파싱은 trendspy 대신 직접 구현
trendspy에도 `trending_now_by_rss()`가 있지만 직접 구현한다.
- `requests` + `xml.etree.ElementTree`로 20줄 정도면 충분함
- 필요한 `pubDate`, `approx_traffic`, 뉴스 제목을 확실하게 다룰 수 있음. 검색량 문자열을 숫자로 바꾸는 것도 직접 처리
- 관리가 거의 멈춘 의존성을 제거할 수 있음
- 라이브러리 내부 예외(`IndexError`, `TypeError`) 없이, HTTP 상태 확인과 파싱 실패 처리를 직접 정할 수 있음

## 4. 구현 계획

### 4-1. 전체 흐름
```
[collect_trends DAG, 2시간마다]
  RSS 요청 → 파싱 → 품질 필터 → (Variable 읽기 → 48시간 지난 항목 삭제 → 병합 → Variable 쓰기)

[recommend_answer DAG, 일·수·금 17시]
  Variable 읽기 → 48시간 이내 항목만 → 검색량 순 상위 20개 → 프롬프트 입력 형식으로 변환
```

### 4-2. 버퍼 형식 (Variable `trend_buffer`)
키워드를 key로 하는 JSON dict:
```json
{
  "이종석": {
    "keyword": "이종석",
    "traffic": 2000,
    "news": ["뉴스 제목1", "뉴스 제목2", "뉴스 제목3"],
    "first_seen": "2026-11-11T11:30:00+00:00",
    "last_seen": "2026-11-11T13:00:00+00:00"
  }
}
```
- key: 정규화한 키워드 (4-3). `keyword`에는 프롬프트에 넣을 원래 표기를 저장 (가장 최근 수집 기준)
- `first_seen`: 처음 수집된 시각 (디버깅용)
- `last_seen`: 마지막으로 RSS에서 확인된 시각 (48시간 판단 기준)
- 시각은 모두 UTC ISO 문자열로 저장

### 4-3. 중복 처리
RSS에 있던 트렌드는 약 2시간 동안 피드에 남아 있어서, 같은 트렌드가 연속된 수집에서 다시 나올 수 있다. 같은 키워드가 다시 들어오면 새 항목을 만들지 않고 기존 항목을 갱신한다.

| 필드 | 갱신 규칙 | 이유 |
|---|---|---|
| key | 앞뒤 공백 제거, 연속 공백을 하나로, 영문 소문자화 후 비교 | `창원 LG 대 서울 SK`와 `창원 lg 대 서울 sk`를 같은 트렌드로 처리 |
| `traffic` | 기존 값과 새 값 중 큰 값 | 트렌드가 진행되며 `200+` → `2000+`로 커질 수 있음 |
| `news` | 새 뉴스가 있으면 교체, 비어 있으면 기존 값 유지 | 최신 기사를 쓰되 정보가 사라지지 않게 함 |
| `first_seen` | 기존 값 유지 | |
| `last_seen` | 이번 수집 시각으로 갱신 | 계속 화제인 트렌드는 삭제되지 않게 함 |

### 4-4. 수집할 때 거르는 기준
검색량 순으로 상위 N개만 남기는 방식은 쓰지 않는다.
- RSS는 원래 한 번에 10개뿐이라, 미리 잘라도 크기 이득이 거의 없음
- 추천 DAG가 최종적으로 검색량 순 상위 20개를 뽑으니 같은 일을 두 번 하게 됨
- 처음 잡혔을 때 `200+`였다가 다음 수집에서 크게 커지는 트렌드가 첫 수집에서 빠질 수 있음

대신 품질 기준으로만 거른다.
- 영어로만 된 키워드 제외 (기존 `common.utils.is_english_only` 사용)
- 뉴스 제목이 하나도 없는 항목 제외 (프롬프트에 넣을 근거가 없음)

### 4-5. 설정 (`common/configs.py`)
- `TREND_RSS_URL = "https://trends.google.com/trending/rss"`
- `TREND_BUFFER_VARIABLE = "trend_buffer"`
- `TREND_WINDOW_HOURS = 48`: 버퍼 유지 기간이자 추천에 사용할 범위
- `TREND_LIMIT = 20`: 프롬프트에 넣을 트렌드 수

### 4-6. RSS 수집·파싱 (`answer_recommendation/candidate_generation/trend_words.py`)
trendspy 코드를 제거하고 아래 함수로 교체한다. Variable 읽기·쓰기를 제외한 로직은 **Airflow를 import하지 않는 순수 함수**로 작성해서 단위 테스트를 쉽게 한다.

| 함수 | 역할 |
|---|---|
| `fetch_trend_rss(geo="KR") -> str` | HTTP GET, timeout 설정, `raise_for_status()` |
| `parse_trend_rss(xml) -> list[dict]` | `{keyword, traffic, news}` 리스트 반환 |
| `parse_traffic(text) -> int` | `"2000+"` 같은 형식에서 `+`를 떼고 숫자로 변환. 알 수 없는 형식이면 예외를 던져 수집 task를 실패시킴(형식 변경을 알림으로 인지) |
| `normalize_keyword(keyword) -> str` | 중복 판단용 key 생성 (4-3) |
| `filter_trends(trends) -> list[dict]` | 품질 기준으로 거름 (4-4) |
| `prune_buffer(buffer, now, hours) -> dict` | `last_seen`이 `now - hours`보다 오래된 항목 삭제 |
| `merge_trends(buffer, trends, now) -> dict` | 4-3 규칙으로 병합 |
| `select_top_trends(buffer, now, hours, limit) -> list[dict]` | 48시간 이내 항목을 검색량 순으로 정렬해 상위 `limit`개를 프롬프트 입력 형식(`{"keywords": [...], "news": [...]}`)으로 반환 |

`now`는 인자로 받는다. 테스트에서 시각을 고정할 수 있다. 수집 DAG는 실제 수집 시각(`pendulum.now("UTC")`)을 넘기고, 추천 DAG는 `data_interval_end`를 넘긴다.

### 4-7. 수집 DAG (`answer_recommendation/collect_trends_dag.py`)
- `dag_id="collect_trends"`, `schedule="0 */2 * * *"`(2시간마다), `catchup=False`
- task 하나로 처리: RSS 수집·파싱·필터 → Variable을 **한 번** 읽기 → `prune_buffer` → `merge_trends` → Variable에 **한 번** 쓰기
  - RSS를 먼저 받는 이유: 요청이 실패하면 Variable을 읽지도 않고 끝나며, 읽기와 쓰기 사이 간격도 짧아짐
  - task를 나누지 않는 이유: 버퍼를 XCom으로 넘길 필요가 없고, 읽기와 쓰기 사이에 다른 실행이 끼어들 여지를 줄임
  - Variable에 쓰는 곳은 이 DAG뿐이고 `catchup=False`라 동시에 실행될 일이 없음. 그래도 확실하게 하려면 `max_active_runs=1` 설정
- RSS 요청이 실패하면 Variable을 건드리지 않고 task를 실패시킴. retries 2, retry_delay 5분
- `on_failure_callback`은 다른 DAG처럼 `notifications.notify_failure` 사용
- Variable이 아직 없으면(첫 실행) 빈 dict로 시작

### 4-8. 추천 DAG 변경 (`recommend_answer_dag.py`)
- `get_trends`: Variable을 읽기만 하고, `select_top_trends(buffer, data_interval_end, TREND_WINDOW_HOURS, TREND_LIMIT)`로 조회
  - 수집 DAG가 멈춰서 오래된 항목이 남아 있을 수 있으므로, 읽을 때도 48시간 기준으로 한 번 더 거름
- 프롬프트 입력 형식은 유지함. RSS에는 연관 키워드가 없으므로 `keywords`는 `[keyword]` 하나만 들어감
- 결과가 0개이면 기존처럼 `ValueError`로 실패시킴
- 과거 날짜로 다시 실행할 때의 한계: 버퍼에는 수집 시점 기준 최근 48시간 데이터만 남아 있음. 따라서 clear나 수동 트리거로 과거 `data_interval_end`를 지정해도 그 시점의 트렌드를 복원할 수 없고, **실행하는 시점의 버퍼**가 그대로 쓰임. 48시간 기준은 하한(오래된 항목 제외)에만 적용되고 상한은 없어서, 기준 시각 이후에 수집된 항목도 포함됨

### 4-9. 의존성 정리
- `docker/airflow.Dockerfile`에서 `trendspy` 제거 후 이미지 재빌드
- `airflow/dags/test.py`(hours별 null 비율 테스트)는 더 이상 필요 없으므로 삭제

### 4-10. 배포 순서
1. 수집 DAG 배포 및 활성화 → 48시간 동안 버퍼 적재
2. 추천 DAG 변경 배포. 그 전에 적재가 덜 된 상태로 추천 DAG가 실행되면 트렌드가 적게 들어가지만, 0개가 아니면 정상 동작함
3. trendspy 제거 후 이미지 재빌드

## 5. 테스트 계획

### 5-1. 단위 테스트 (pytest, Airflow 불필요)
위치: `airflow/tests/test_trend_words.py` (`conftest.py`에서 `airflow/dags`를 `sys.path`에 추가)

| 대상 | 케이스 |
|---|---|
| `parse_trend_rss` | 실제 RSS 응답을 저장한 fixture → 10개 item, 각 필드 값과 타입 확인 |
| | `news_item`이 없거나 제목이 빈 item → `news`가 빈 리스트 |
| | 깨진 XML → 예외 발생 |
| `parse_traffic` | `"200+"`→200, `"2000+"`→2000, 알 수 없는 형식→`ValueError` |
| `normalize_keyword` | 대소문자, 앞뒤 공백, 연속 공백이 달라도 같은 key |
| `filter_trends` | 영어로만 된 키워드, 뉴스가 없는 항목 제외 |
| `prune_buffer` | 정확히 48시간 경계, 그 전후 항목이 각각 남거나 지워지는지 |
| `merge_trends` | 새 키워드 → 추가 (`first_seen` = `last_seen` = now) |
| | 기존 키워드 → `traffic`은 큰 값, `last_seen` 갱신, `first_seen` 유지 |
| | 새 뉴스가 비어 있으면 기존 뉴스 유지 |
| | 같은 입력으로 두 번 병합해도 결과 동일 (`last_seen` 제외) |
| `select_top_trends` | 검색량 내림차순, `limit`개 제한, 48시간 지난 항목 제외, 출력 형식 확인 |
| | 빈 버퍼 → 빈 리스트 |

외부 HTTP는 호출하지 않고, fixture XML만 사용한다.

### 5-2. DAG 수동 실행
```bash
# 수집 DAG 한 번 실행
docker exec -it newmantle-quiz-airflow-scheduler-1 airflow dags test collect_trends

# 버퍼 확인
docker exec -it newmantle-quiz-airflow-scheduler-1 airflow variables get trend_buffer

# 한 번 더 실행해서 중복이 합쳐지는지 확인 (키 개수가 RSS 10개씩 단순 증가하지 않아야 함)
docker exec -it newmantle-quiz-airflow-scheduler-1 airflow dags test collect_trends

# 추천 DAG의 트렌드 단계만 실행
docker exec -it newmantle-quiz-airflow-scheduler-1 \
  airflow tasks test recommend_answer generate_candidate.get_trends_words.get_trends
```
- `get_trends` 출력이 기존 프롬프트 입력 형식과 같은지 확인
- 이어서 `extract_trend_words`까지 실행해서 Gemini 응답이 정상인지 확인
- RSS 요청이 실패하는 상황(잘못된 URL로 임시 변경)에서 Variable이 바뀌지 않는지 확인

### 5-3. 운영 모니터링 (배포 후 1주)
- 수집 DAG 성공률. 실패가 연속으로 나는지 확인
- **수집 누락 여부:** 연속된 두 수집 사이에 겹치는 키워드가 거의 없다면, RSS에 트렌드가 남아 있는 시간이 2시간보다 짧다는 뜻이라 주기를 1시간으로 줄여야 함
- 48시간 동안 버퍼에 쌓이는 키워드 수 (목표: `TREND_LIMIT`의 2배 이상)
- `recommend_answer` 실행 로그에서 `get_trends` 결과 개수, 최종 추천된 인기검색어 태그 단어의 품질
