# Decisions — 게임 이벤트 로그 수집 구조 변경

> 영향도: foundation(스펙 간) · significant(여러 부분) · local(단일 단위)
> 출처: user-suggested(사람 제안·사람 선택) · ai-suggested(AI 제안·사람 선택) · ai-selected(AI 제안·AI 선택)
> 상태: active · superseded by Dec-N · revoked

---

### Dec-1. 압축을 수집 DAG가 맡는다
영향도: foundation · 출처: user-suggested

문제 — 재시작으로 생기는 미압축 `.jsonl`을 어디서 처리할 것인가
옵션
  (A) 서버에서 재시작 원인을 없앤다 (등록 중 워커 kill 방지)
  (B) 서버 시작 시 남은 `.jsonl`을 압축한다
  (C) 서버는 파일만 남기고, DAG가 압축해서 가져온다
선택 — C
근거 — 재시작은 등록 부하 외에도 배포·장애·재부팅으로 생기므로 원인을 없애도 고아 파일은 남는다. A는 근본 해결이지만 서버 구조 변경이 필요해 오래 걸리고, B는 시작 시점에 다른 워커가 쓰고 있는 파일을 구분해야 해 복잡하다. C는 재시작 사유와 무관하게 동작한다.
영향 — Phase 1, Phase 3, Dec-2, Dec-4. A는 quiz-upsert-load.md에서 별도 진행
상태 — active

### Dec-2. SSH `gzip -c` stdout으로 전송
영향도: significant · 출처: user-suggested

문제 — 압축된 상태로 어떻게 전송할 것인가 (목적: 전송량 + 로컬 저장공간)
옵션
  (A) SFTP로 원본을 받아 로컬에서 압축
  (B) 서버에서 압축 파일을 만든 뒤 SFTP로 받고 서버 파일 삭제
  (C) SSH로 `gzip -c` 실행, stdout을 로컬 파일로 바로 저장
선택 — C
근거 — A는 전송량이 줄지 않는다(11/17 기준 11.9MB vs 약 0.9MB). B는 서버에 임시 파일이 생겨 이름 충돌·정리가 필요하다. C는 서버에 아무것도 남기지 않고 전송·저장 모두 압축 상태다. 서버에 `gzip`은 있고 `zip`은 없다.
영향 — Phase 1
상태 — active

### Dec-3. 로컬 저장 형식을 `.jsonl.gz`로 통일
영향도: significant · 출처: ai-suggested

문제 — 로컬 로그를 어떤 압축 형식으로 통일할 것인가 (조건: 스크립트로 다루기 쉽고 파이썬에서 읽기 쉬울 것)
옵션
  (A) `.jsonl.zip` 유지
  (B) `.jsonl.gz`
선택 — B
근거 — 셸에서 `gzip -c`, `zcat`, `zgrep`이 기본 제공되고, `pd.read_json(path, lines=True)`가 확장자로 gzip을 자동 인식해 `ZipFile` 루프가 필요 없다. 로그는 파일 하나가 스트림 하나라 아카이브 형식이 필요 없고 압축률은 같다(deflate). A는 서버에 `zip`이 없어 `gzip -c` 전송과 맞지 않는다. 로컬 파일명은 `<서버 파일명>.gz`로 한다.
영향 — Phase 1, Phase 2, Backlog(마이그레이션)
상태 — active

### Dec-4. 서버 loguru 압축 제거
영향도: significant · 출처: user-suggested

문제 — DAG가 압축을 맡은 뒤 서버 압축을 어떻게 할 것인가
옵션
  (A) `compression="zip"` 유지, DAG가 zip과 `.jsonl`을 계속 둘 다 처리
  (B) `compression="gz"`로 변경
  (C) 압축 제거, 모든 파일을 `.jsonl`로 남김
선택 — C
근거 — 로테이션된 파일과 고아 파일이 같은 형태가 되어 수집 경로가 하나로 합쳐진다. 비압축 원본은 zip의 약 14배지만 retention 1달 기준 최대 약 1.2GB(최근 약 250MB)라 서버 디스크로 충분하다. A는 수집 경로가 둘로 남고, B도 고아 파일은 여전히 `.jsonl`이라 경로가 둘이다.
영향 — Phase 3, Phase 1(전환기 zip 처리)
상태 — active

### Dec-5. 서버 로그 파일명에 PID를 넣는다
영향도: significant · 출처: user-suggested

문제 — 워커 2개가 같은 파일에 각자 sink를 가져 생기는 22바이트 빈 zip·중복 파일·이중 rotation을 어떻게 정리할 것인가
옵션
  (A) 그대로 둔다 (로그 손실은 아님)
  (B) 워커를 1개로 줄인다
  (C) 파일명에 PID를 넣어 워커별로 파일을 분리한다
선택 — C
근거 — A는 중복 파일이 집계를 부풀리고 원인 추적을 어렵게 한다. B는 워커 수를 유지한다는 제약에 어긋난다(Dec-10). C는 워커끼리 파일을 공유하지 않아 이중 rotation 자체가 없어진다. loguru 경로 포맷은 `{time}`만 치환하므로 PID는 `os.getpid()`로 직접 넣는다.
영향 — Phase 3, Dec-6(retention이 이전 PID 파일을 못 지우는 문제), Phase 1(파일명이 날짜로 시작하는 규칙은 유지되어 매칭 변경 없음)
상태 — active

### Dec-6. retention을 디렉터리 전체 정리 함수로 교체
영향도: local · 출처: ai-suggested

문제 — PID가 파일명에 들어가면 loguru retention이 현재 PID 파일만 찾게 되는데, 재시작으로 바뀐 이전 PID 파일은 누가 지울 것인가
옵션
  (A) 서버 cron으로 `find -mtime +30 -delete`
  (B) DAG가 수집 후 서버 파일 삭제
  (C) loguru `retention`에 함수를 넘기고, 넘겨받은 목록 대신 `logs/events/*.jsonl*` 전체를 mtime으로 정리
선택 — C
근거 — A는 호스트 설정이 늘어난다. B는 수집 DAG가 서버 상태를 바꾸게 되어 실패·재실행 시 위험하고, 데스크톱 DAG가 멈추면 서버 디스크가 계속 찬다. C는 기존 rotation 주기(매일)에 그대로 실린다. 두 워커가 같은 파일을 지우려 할 수 있어 `FileNotFoundError`는 무시한다. 전제(retention glob이 PID를 literal로 쓴다)는 loguru 소스로 확인 필요.
영향 — Phase 3, Verification(loguru 동작 확인)
상태 — active (정리 기준 mtime → 파일명 날짜는 Dec-18)

### Dec-7. rotation 방식과 파일명 날짜 규칙 유지
영향도: local · 출처: ai-suggested

문제 — 수집 구조를 바꾸는 김에 rotation 방식이나 파일명 날짜(UTC → KST)도 바꿀 것인가
옵션
  (A) 유지
  (B) 파일명을 KST 날짜로 변경
선택 — A
근거 — DAG 압축과 PID 분리로 rotation 때문에 생기던 문제(동일 이름 rename, 미압축)는 영향이 없어진다. B는 기존 로컬 파일과 날짜 규칙이 달라지고(TZ 변경·전환기 처리·기존 파일 rename 필요), 이득이 작다. 퀴즈 D는 KST D와 D+1 이틀 동안 플레이 가능해(`is_expired`: `today - date >= 2`) 이벤트 날짜와 `date` 필드가 원래 1:1이 아니다(전날 퀴즈 이벤트 0.1~0.5%, 11/07·11/10 파일 기준). 어떤 파일명 규칙이든 파일을 하루 넓게 읽고 `date` 필드로 필터해야 하므로(Backlog), KST 파일명의 이득은 가독성뿐이다.
영향 — 외부 제약, Phase 1(날짜 조건 계산 그대로)
상태 — active

### Dec-8. 수집 대상은 파일명 날짜 범위로만 고른다 (mtime 조건 없음)
영향도: local · 출처: ai-selected

문제 — 아직 기록 중인 파일을 받지 않으려면 어떤 조건으로 고를 것인가
옵션
  (A) 날짜 범위 + mtime 1일 이상 지난 파일
  (B) 날짜 범위만
선택 — B
근거 — 파일명 D인 파일은 늦어도 D+1 15:00Z에 rotation되어 기록이 끝나고, DAG 범위는 실행 시점 기준 2일 전까지라 범위 안 파일은 모두 기록이 끝난 상태다(11/17 파일이 다음 날 11:08Z까지 기록된 사례도 범위 안). A는 범위 마지막 날 파일이 실행 시점에 약 16시간밖에 지나지 않아 빠지고, 다음 주에는 범위가 넘어가 영영 수집되지 않는다.
영향 — Phase 1
상태 — superseded by Dec-12

### Dec-9. KST 하루 단위로 파일을 재분할하지 않는다
영향도: local · 출처: user-suggested

문제 — 로컬 파일을 KST 하루 단위로 다시 나눌 것인가
옵션
  (A) 수집 시 KST 날짜별로 재분할
  (B) 서버 파일 단위 그대로 저장
선택 — B
근거 — 분석 기준은 이벤트 시각이 아니라 `date` 필드(퀴즈 날짜)라 파일 경계를 맞춰도 이득이 작다. A는 새 로그가 들어올 때마다 해당 날짜를 다시 만드는 비용(원본/파생 분리, 재생성 로직)이 더 크다.
영향 — Phase 1, Backlog(마이그레이션)
상태 — active

### Dec-10. 워커 수 유지, 서버 근본 원인은 이 작업에서 다루지 않는다
영향도: significant · 출처: user-suggested

문제 — 워커 kill과 sink 중복을 워커 수 축소 등 서버 쪽 조치로 함께 해결할 것인가
옵션
  (A) 워커 2 → 1, swap 측정(`vmstat`) 등 서버 조치를 이번에 함께 진행
  (B) 이번 작업은 로그 수집 응급처치만, 서버 근본 원인은 별도 진행
선택 — B
근거 — 서버 쪽은 업로드 구조 변경이나 Redis 대체 같은 아키텍처 변경까지 검토 중이라 범위가 크다. 구조를 바꿔도 재시작이 있으면 고아 파일은 생기므로 수집 쪽 처리는 어차피 필요하다.
영향 — Scope(Out), quiz-upsert-load.md
상태 — active

### Dec-11. 서버·DAG 변경을 한 폴더의 문서로 관리
영향도: local · 출처: user-suggested

문제 — 서버와 DAG가 맞물리는 변경을 문서로 어떻게 나눌 것인가
옵션
  (A) 각 저장소에 따로 작성
  (B) 한 곳(quiz 저장소 `docs/specs/event-log-collection/`)에 함께 쓰고 양쪽 문서에서 링크
선택 — B
근거 — 두 쪽을 묶는 것은 파일 이름·형식·보관이라는 하나의 약속이라, 나눠 쓰면 한쪽만 바뀌기 쉽다. 이번 작업의 목적이 로그 결손 방지이고 코드도 DAG 쪽이 많아 quiz 저장소에 둔다.
영향 — 결손 분석도 plan.md Context로 합침(별도 분석 문서 삭제). quiz-upsert-load.md에서 링크
상태 — active

### Dec-12. 수집 대상은 "기록이 끝났고 아직 안 받은 파일 전부"
영향도: significant · 출처: ai-suggested

문제 — 매 실행에서 어떤 서버 파일을 가져올 것인가
옵션
  (A) 날짜 범위: `data_interval_end - 2일`부터 7일치 (기존 방식, Dec-8)
  (B) 파일명 날짜 ≤ 실행일(UTC) - 2일이면서 로컬에 아직 없는 파일 전부
선택 — B
근거 — 파일명 D는 PID·재시작과 무관하게 늦어도 D+1 15:00Z에 rotation되고, loguru는 기록 직전에 rotation을 확인하므로 지난 날짜 이름의 파일에 새 로그가 붙지 않는다. DAG가 일요일 07:00Z에 돌아 1일 전 파일은 아직 작성 중이라 2일 전까지로 자른다(Dec-8의 날짜 논리 유지, mtime 조건 없음). B는 데스크톱이 꺼져 있었거나 실행이 실패해도 서버 보관 기간(1달) 안이면 다음 실행에서 자동으로 채워져 catchup·범위 지정 스크립트가 필요 없다. A는 빠진 실행을 사람이 재실행해야 한다. "이미 받음" 판단에 기존 `.zip`도 포함해 같은 내용을 `.gz`로 중복 저장하지 않는다.
영향 — Phase 1, Verification, `fetch_game_event_logs_range.py` 불필요
상태 — active

### Dec-13. 파일 단위 실패는 끝까지 진행한 뒤 task 실패
영향도: local · 출처: ai-suggested

문제 — 파일 하나의 수집(SSH 끊김, gzip 종료 코드, 무결성 검사)이 실패하면 DAG를 어떻게 처리할 것인가
옵션
  (A) 첫 실패에서 즉시 task 실패
  (B) 실패한 파일은 임시 파일만 지우고 건너뛴 뒤, 끝에서 실패 목록이 있으면 task 실패
  (C) 경고 로그만 남기고 성공 처리
선택 — B
근거 — "안 받은 파일 전부" 방식(Dec-12)이라 실패한 파일은 다음 실행에서 자동으로 다시 대상이 되므로 다른 파일을 막을 이유가 없다. A는 파일 하나가 계속 실패하면 나머지도 못 받는다. C는 실패가 이어져도 UI에 성공으로 보여 서버 보관 기간(1달)을 넘길 위험이 있다. 임시 파일 → `os.replace` 구조라 실패해도 최종 이름의 불완전 파일이 남지 않는다.
영향 — Phase 1, Dec-12
상태 — active

### Dec-14. 수집 DAG를 매일 실행
영향도: local · 출처: ai-suggested

문제 — 수집 주기를 주 1회로 유지할 것인가
옵션
  (A) 주 1회(일요일 16:00 KST) 유지
  (B) 매일 실행
선택 — B
근거 — "안 받은 파일 전부"(Dec-12)라 자주 돌려도 같은 파일을 다시 받지 않고, 받을 게 없으면 목록 조회만 하고 끝난다. 데이터 지연이 최대 약 9일에서 2~3일로 줄고, 데스크톱이 꺼진 날이 있어도 서버 보관 기간(1달) 안에 기회가 약 30번(주 1회면 약 4번) 있다.
  실행 시각은 기존 16:00 KST 유지. 데스크톱이 켜져 있는 KST 09~24시는 모두 rotation(00:00 KST) 전이라 어느 시각을 골라도 날짜 조건은 "실행일(UTC) - 2일"이 필요하고, 17시 퀴즈 등록 전이라 등록 부하와도 겹치지 않는다. 빠진 실행은 다음 실행이 채우므로 `catchup`은 끈다.
영향 — Phase 1, 외부 제약
상태 — active

### Dec-15. 새 로깅은 새 경로에서 시작하고, 기존 로그는 일회성으로 옮긴다
영향도: significant · 출처: user-suggested

문제 — 기존 로그(서버 기존 경로 + 로컬 `.zip`)를 새 형식으로 언제·어떻게 정리할 것인가. "이미 받음" 판단(Dec-12)이 로컬 파일 이름에 의존해, 로컬에서 중복을 지우면 서버에 남은 같은 zip을 DAG가 다시 받는 문제가 있다
옵션
  (A) 서버에서 zip이 다 사라진 뒤(압축 제거 후 1달) 마이그레이션
  (B) 받은 파일 목록(manifest)을 따로 저장해 "이미 받음"을 판단
  (C) 아무 때나 하고, 다시 받은 중복은 다음에 또 정리
  (D) 서버는 새 경로에 새 sink를 두고, DAG는 새 경로만 수집해 로컬 새 경로에 저장. 기존 경로들은 일회성으로 `.gz` 변환·중복 제거 후 로컬 새 경로로 이동
선택 — D
근거 — DAG가 기존 경로를 보지 않으므로 중복이 되살아날 일이 없고, 전환기 `.zip` 처리·기존 `.zip` 확인이 DAG에서 빠진다. 분석 스크립트도 `.gz`만 읽으면 된다. 기존 경로는 sink가 없어지면서 고정되므로 마이그레이션 기한도 없다. A는 1달을 기다려야 하고, B는 manifest와 실제 로컬 상태가 어긋나는 문제를 따로 관리해야 하며, C는 정리를 반복한다. 경로 이름은 정하지 않고, 기존 경로와 확실히 구분되게(접두어가 겹치지 않게) 짓는다는 조건만 둔다.
영향 — Phase 1~4, Dec-12("이미 받음" 판단이 로컬 새 경로의 `.gz`만 확인하도록 단순화, 전환기 `.zip` 처리 제거), Dec-3(서버 zip의 로컬 변환은 마이그레이션에서만)
상태 — active

### Dec-16. 로컬도 새 경로를 만든다
영향도: local · 출처: user-suggested

문제 — 로컬 저장 경로를 새로 만들 것인가, 기존 `data/game-event-logs/`를 그대로 쓸 것인가
옵션
  (A) 새 경로를 만들고 airflow compose에 마운트 추가
  (B) 기존 경로 유지, 마이그레이션 때 기존 `.zip`을 legacy 폴더로 옮김
선택 — A
근거 — 기존 파일과 새 파일이 한 폴더에 섞이지 않아 마이그레이션 실수(덮어쓰기·잘못 지우기)가 새 파일에 닿지 않는다. 기존 경로는 마이그레이션이 검증될 때까지 원본 그대로 백업 역할을 한다. B는 compose 변경이 없지만 전환기에 `.zip`과 `.gz`가 한 폴더에 섞인다. airflow는 `./data/game-event-logs`만 마운트하므로(`data/` 전체 마운트는 `word-embedder`뿐) 마운트 한 줄 추가와 airflow 재시작이 필요하다.
영향 — Phase 2(compose 마운트), Phase 3(백업 단계 = 기존 경로 유지), Phase 4(분석 스크립트 경로)
상태 — active (폴더 배치는 Dec-19)

### Dec-17. 수집 DAG는 새 dag_id로 새로 만든다
영향도: local · 출처: ai-suggested

문제 — 기존 `fetch_game_event_logs`를 고칠 것인가, 새 DAG를 만들 것인가
옵션
  (A) 기존 DAG 수정 (같은 dag_id)
  (B) 새 dag_id로 새 DAG, 기존 DAG는 삭제
선택 — B
근거 — 읽는 경로, 저장 경로, 형식, 스케줄(주 1회 → 매일), catchup, 대상 선정 방식이 모두 바뀐다. A는 UI에서 과거 실행(7일 범위·zip)과 새 실행이 섞이고, 과거 실행을 Clear하면 새 코드가 그 날짜로 돌아 혼란스럽다. 기존 DAG와 `fetch_game_event_logs_range.py`는 새 DAG 수집이 확인되면 삭제한다. 새 DAG 이름은 기존과 확실히 구분되게 짓는다는 조건만 둔다.
영향 — Phase 2
상태 — active

### Dec-18. retention 기준을 mtime에서 파일명 날짜로 바꾼다
영향도: local · 출처: user-suggested

문제 — Dec-6의 정리 함수가 오래된 파일을 무엇으로 판단할 것인가
옵션
  (A) mtime 30일 초과
  (B) 파일명 날짜(UTC, 이름 앞 10자) < 오늘(UTC) − 30일
선택 — B
근거 — DAG 수집 조건(파일명 날짜 ≤ 실행일 − 2, Dec-12)과 같은 축이라 "서버 보관 30일 안이면 DAG가 다시 채운다"를 파일명만으로 계산할 수 있다. 파일을 수정하거나 복사해도 보관 기간이 리셋되지 않는다. A는 코드가 조금 더 단순하지만 수정 시 보관 기간이 바뀐다. PID와 무관하게 디렉터리 전체에 적용하고, 날짜로 파싱되지 않는 파일은 지우지 않는다.
영향 — Phase 1(코드 예시·완료 기준), Verification(retention 동작)
상태 — active

### Dec-19. 로컬 게임 로그를 `data/game-logs/` 하위 폴더 하나로 모은다
영향도: local · 출처: user-suggested

문제 — 로컬에 게임 로그 폴더가 세 개(`game-logs` 초기 텍스트 로그, `game-event-logs` 옛 zip, `game-raw-events` 새 gz)로 흩어져 헷갈린다
옵션
  (A) 세 폴더를 그대로 둔다
  (B) `data/game-logs/` 아래 `v0/`(초기 `*.log`, uuid 없음), `zip-backup/`(옛 zip 원본 백업), `raw-events/`(새 gz, DAG 저장 위치)로 모은다
선택 — B
근거 — 로그 종류가 한 곳에서 보이고, 백업(`zip-backup/`)은 검증 후 폴더째 지우면 된다. 새 DAG를 켜기 전이고 compose 재생성도 어차피 필요한 시점이라 비용이 작다. airflow는 `raw-events/`만 마운트해 백업·v0에는 쓰지 못한다. `raw-events`는 서버 경로 이름과 맞췄다.
영향 — Phase 2(`LOCAL_DIR`, compose 마운트), Phase 3(백업 위치), Phase 4(분석 스크립트 경로), Dec-16
상태 — active
