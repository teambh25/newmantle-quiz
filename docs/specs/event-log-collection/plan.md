# 게임 이벤트 로그 수집 구조 변경 — 고아 파일 결손 응급처치
> 압축을 서버(loguru)에서 수집 DAG로 옮기고, 서버 로그 파일을 워커별로 분리해 재시작이 있어도 로그를 빠짐없이 가져온다

## 1. Context
- 배경
  - 게임 서버가 KST 09~24시에 재시작되면 그때 쓰던 이벤트 로그가 압축되지 않은 `.jsonl`(고아 파일)로 남는다. 수집 DAG는 `.jsonl.zip`만 받아서 이 파일을 놓치고, 서버 retention(1달)이 지우면 영구 결손된다. 과거 11일이 하루의 약 70%씩 빠졌다.
  - 재시작은 주로 퀴즈 등록 중 uvicorn이 워커를 kill하면서 생기지만, 배포·장애·재부팅으로도 생긴다. 근본 원인(등록 부하)은 서버 구조 변경이 필요해 오래 걸리므로, 원인과 무관하게 결손을 막는 응급처치가 먼저 필요하다.
  - 재시작 원인(등록 중 워커 kill)의 증거와 근본 해결: [newmantle-game docs/problem/quiz-upsert-load.md](../../../../newmantle-game/docs/problem/quiz-upsert-load.md)
  - 결손 분석 상세는 아래 "결손 분석 (2026-11-19 조사)"
- 외부 제약
  - uvicorn `--workers 2` 유지 (Dec-10)
  - 파일명 날짜 규칙 유지: 파일명 `D`(UTC) = KST `D+1` 하루치. 분석 스크립트와 기존 로컬 파일이 이 규칙에 의존한다 (Dec-7)
  - rotation `15:00`(UTC, KST 자정) 유지 (Dec-7)
  - 서버 보관 기간 1달 유지. 서버 디스크는 비압축 기준 최대 약 1.2GB(최근 약 250MB)까지 허용
  - 수집 DAG: 매일 16:00 KST, `catchup=False` (Dec-14). 수집 대상은 날짜 범위 대신 "안 받은 파일 전부" (Dec-12)
  - Airflow 데스크톱은 보통 KST 09~24시에만 켜져 있음
  - 수집 연결은 기존 `game_server_sftp` 하나만 사용 (SSH exec 가능 확인됨)
  - 새 경로 이름은 기존 경로(서버 `logs/events/`, 로컬 `data/game-event-logs/`)와 확실히 구분되게 짓는다 — 접두어가 겹쳐 glob·`startswith`에 함께 걸리지 않도록 (Dec-15). 이 문서에서는 `raw-events`, `game-logs/raw-events`로 표기
- 기존 패턴
  - 서버: `newmantle-game/fastapi/app/cores/logging.py`의 events sink (`setup_logging()`이 워커마다 `app/cores/event.py`에서 호출됨)
  - DAG: `airflow/dags/vocab/fetch_game_event_logs_dag.py` (SFTPHook, 날짜 범위 매칭)
  - 일회성 수집: `airflow/dags/vocab/fetch_game_event_logs_range.py` (Dec-12 적용 후 불필요, Phase 3 스크립트에 재활용 가능)

### 결손 분석 (2026-11-19 조사)
대상: 로컬 `data/game-event-logs/` (2026-04-18 ~ 11-18) vs 서버 `fastapi/logs/events/` (최근 1개월)

현재 로그 설정 (서버 `app/cores/logging.py`)

```python
logger.add(
    "./logs/events/{time:YYYY-MM-DD!UTC}.jsonl",
    rotation="15:00",  # KST 자정
    retention="1 month",
    compression="zip",
    enqueue=True,
)
```

- 파일명 = 파일을 연 시점의 UTC 날짜 → 정상 rotation 시 `D.jsonl.zip`은 KST `D+1` 하루치
- 압축은 rotation 시점에만 일어남 (프로세스 종료 시에는 압축하지 않음)
- rotation 시 새 파일명이 기존과 같으면 기존 파일을 `D.<타임스탬프>.jsonl`로 rename 후 압축
- uvicorn `--workers 2` → 워커마다 독립된 sink가 같은 파일에 기록·rotation
- 수집 DAG는 `f.startswith(log_date) and f.endswith(".jsonl.zip")`으로 매칭 → `.jsonl`은 무시

고아 파일이 생기는 과정 (10/30 사례, 원격 mtime 기준)

```
10-30 15:00Z  rotation → 2026-10-30.jsonl 열고 기록 시작
10-31 14:31Z  서버 재시작 (다음 rotation 29분 전)
              → 기존 프로세스 종료: 2026-10-30.jsonl 미압축 상태로 남음
              → 새 프로세스: 현재 UTC 날짜로 2026-10-31.jsonl 을 새로 엶
              → 이후 아무도 2026-10-30.jsonl 을 다시 열지 않음 → 영원히 미압축
10-31 15:00Z  rotation: 새 파일명(2026-10-31)이 기존과 같아서
              2026-10-31.2026-10-31_14-31-39_....jsonl.zip 으로 rename + 압축
```

- 재시작 시각이 KST 00~09시면 새 파일명 = 기존 파일명 → 같은 파일에 이어 씀 → 문제 없음
- 재시작 시각이 KST 09~24시면 새 파일명 ≠ 기존 파일명 → 고아 파일 발생
- 결손 날짜의 재시작은 모두 일·수·금(퀴즈 등록일), 대부분 KST 17:0x (등록 DAG 실행 시각). 워커 수와 무관하게 발생
- 남은 워커가 있으면 이전 파일에 계속 기록함 → 11/17 파일은 다음 날 11:08Z(2차 업로드 때 남은 워커 교체)까지 기록

서버에만 있던 파일 → 수동 복구 완료

| 파일 | 크기 | 마지막 기록 | 내용 (KST) |
|------|-----:|-------------|-----------|
| `2026-10-30.jsonl` | 5.6MB | 10-31 14:31Z | 10/31 00:00 ~ 23:31 (27,120건) |
| `2026-11-17.jsonl` | 11.9MB | 11-18 11:08Z | 11/18 00:00 ~ 20:08 (56,945건) |

영구 결손 (서버 retention 경과, 복구 불가) — 파일명 날짜가 빈 11일. 각 다음 날(KST) 자정 ~ 재시작 시각이 빠짐

| 비어 있는 파일명 | 결손 구간 (KST) |
|-----------------|----------------|
| 2026-04-21 | 04-22 00:00 ~ 15:35 |
| 2026-05-16 | 05-17 00:00 ~ 17:03 |
| 2026-05-23 | 05-24 00:00 ~ 17:04 |
| 2026-06-25 | 06-26 00:00 ~ 17:02 |
| 2026-07-23 | 07-24 00:00 ~ 17:03 |
| 2026-08-08 | 08-09 00:00 ~ 17:05 |
| 2026-09-08 | 09-09 00:00 ~ 17:06 |
| 2026-09-15 | 09-16 00:00 ~ 17:06 |
| 2026-09-26 | 09-27 00:00 ~ 17:41 |
| 2026-10-03 | 10-04 00:00 ~ 17:16 |
| 2026-10-13 | 10-14 00:00 ~ 17:06 |

- 파일명 공백과 이벤트 시간 공백이 11일 모두 정확히 대응 (서버에 파일이 없어 고아 파일이었다는 것 자체는 정황 확인)

중복 파일 (이중 집계) — 내용(md5)이 같은 `D.jsonl.zip` ↔ `D.<타임스탬프>.jsonl.zip` 4쌍

| 파일명 날짜 | 영향 KST 날짜 |
|------------|--------------|
| 2026-06-14 | 06/15 |
| 2026-10-21 | 10/22 |
| 2026-10-29 | 10/30 (235,678건 = 117,839 × 2) |
| 2026-11-07 | 11/08 |

- `overview.py`의 `load_logs`는 중복 제거 없이 concat → 위 날짜의 action 수·guess 분포·duplicate guess 비율이 부풀려짐 (DAU는 `nunique`라 영향 없음)
- 워커 2개의 이중 rotation과 관련된 것으로 추정, 정확한 경위는 미확인

그 밖의 관찰

- KST 10/29 전체(484건) + 10/30 00:00 ~ 03:25: 실제 서비스 장애 (수집 문제 아님)
- KST 04:30 ~ 06:30 사이 60 ~ 100분 공백 13일: 새벽 저트래픽으로 정상 추정 (미검증)
- 날짜당 파일 수: 2개(141일)는 데이터 zip + 두 번째 워커의 22바이트 빈 zip, 3 ~ 4개(37일)는 당일 재시작으로 인한 추가 rotate 파일, 1개(26일)는 빈 zip이 생기지 않은 날

기존 분석에 대한 영향

| 문서 | 분석 기간 | 영향 날짜 |
|------|----------|----------|
| [invalid-word.md](../../log-analysis/invalid-word.md) | 2026-04-18 ~ 05-02 | 04-22 (약 65% 결손) |
| [input-pos.md](../../log-analysis/input-pos.md) | 2026-04-17 ~ 04-20 | 없음 |

- 날짜별 지표(DAU, 리텐션 등)를 볼 때 결손 11일·중복 4일·장애 기간은 제외하거나 별도 표기. KST 10/30은 장애 + 중복이 겹침

## 2. Scope
- In
  - 서버: 새 경로 `logs/raw-events/`에 새 sink — 압축 없음 (Dec-4), 파일명에 PID (Dec-5), 디렉터리 전체 정리 retention (Dec-6, 파일명 날짜 기준 Dec-18). 기존 `logs/events/` sink는 제거 (Dec-15)
  - DAG: 서버 새 경로에서 기록이 끝났고 아직 안 받은 `.jsonl`을 SSH `gzip -c` stdout으로 받아 로컬 새 경로 `data/game-logs/raw-events/`에 `.jsonl.gz`로 저장 (Dec-1, Dec-2, Dec-3, Dec-12, Dec-15)
  - 일회성 마이그레이션: 서버 기존 경로 + 로컬 기존 경로의 로그를 `.gz`로 변환·중복 제거 후 로컬 새 경로로 이동 (Dec-15)
  - 분석 스크립트: 로컬 새 경로의 `.jsonl.gz`만 읽도록 변경 (`overview.py`, `invalid_word_analysis.py`)
- Out
  - 등록 중 워커 kill 방지, 업로드 구조·Redis 대체 등 서버 아키텍처 변경 → 서버에서 별도 진행 (quiz-upsert-load.md) (Dec-10)
  - 워커 수 변경 (Dec-10)
  - rotation 방식·파일명 날짜 규칙 변경 (Dec-7)
  - KST 하루 단위 재분할 (Dec-9)
  - 행 단위 중복 제거(`drop_duplicates`) — 실제로 동일한 이벤트 2건도 지울 수 있음
  - docker 로그 rotation → 서버 운영 작업, 이번 범위 아님 (Backlog)

## 3. Plan
### Phase 0 — 서버에만 남은 고아 파일 수동 복구
- 완료 기준: `2026-10-30.jsonl`, `2026-11-17.jsonl`을 로컬에 저장, 원본 크기 일치·`testzip` 통과
- 진행상황: [x] 완료 (2026-11-19)

### Phase 1 — 서버 로깅 변경 (새 경로)
- 내용
  ```python
  EVENTS_DIR = Path("./logs/raw-events")

  def _cleanup_events(_files):  # loguru가 넘기는 목록은 현재 PID 파일뿐이라 무시
      cutoff = datetime.now(timezone.utc).date() - timedelta(days=30)
      for p in EVENTS_DIR.glob("*.jsonl"):
          try:
              file_date = date.fromisoformat(p.name[:10])  # 파일명 날짜(UTC) 기준 (Dec-18)
          except ValueError:  # 날짜로 시작하지 않는 파일은 유지
              continue
          if file_date < cutoff:
              try:
                  p.unlink()
              except FileNotFoundError:  # 다른 워커가 먼저 지운 경우
                  pass

  logger.add(
      f"./logs/raw-events/{{time:YYYY-MM-DD!UTC}}.{os.getpid()}.jsonl",
      rotation="15:00",
      retention=_cleanup_events,
      # compression 없음
      ...
  )
  ```
  - 기존 `./logs/events/` sink는 삭제 → 배포 시점부터 기존 경로에는 아무도 쓰지 않음 (retention도 더 이상 돌지 않음)
- 완료 기준
  - 배포 후 `logs/raw-events/`에 워커마다 `D.<pid>.jsonl`이 하나씩 생기고, 다음 rotation 뒤에도 `.zip`이 생기지 않음
  - `logs/events/`의 파일 mtime이 배포 시각 이후로 바뀌지 않음
  - 파일명 날짜가 31일 전인 다른 PID의 테스트 파일은 rotation 때 삭제되고, 30일 이내·날짜 파싱 불가 파일은 남음 (로컬 테스트)
- 진행상황: [~] 배포 완료 (PR #6, 2026-11-24) — raw-events PID별 2개 생성·logs/events mtime 불변 확인, 첫 rotation 후 .zip 미생성 확인 대기

### Phase 2 — 수집 DAG 변경
- 내용
  - 새 dag_id로 새 DAG 작성 (이름은 기존 `fetch_game_event_logs`와 확실히 구분되게). 기존 DAG와 `fetch_game_event_logs_range.py`는 새 DAG 수집 확인 후 삭제 (Dec-17)
  - 서버 `logs/raw-events/`만 본다. 아래 조건을 모두 만족하는 파일 선택 (PID·재시작 여부 구분 없음) (Dec-12)
    - `.jsonl`로 끝남
    - 파일명 날짜 ≤ 실행일(UTC) - 2일 → 기록이 끝난 파일만. 작성 중인 파일은 다음 실행 때 수집
    - 로컬 `data/game-logs/raw-events/`에 `<이름>.jsonl.gz`가 없음
  - `gzip -c` stdout을 임시 파일로 받고, gzip 무결성 확인 후 `<서버 파일명>.gz`로 `os.replace`
  - 실행이 빠지거나 실패해도 서버 보관 기간(1달) 안이면 다음 실행에서 자동으로 채워짐 → `catchup`·범위 지정 스크립트 불필요
  - 스케줄 `0 16 * * *`(매일 KST 16시), `catchup=False` (Dec-14)
  - airflow compose(`docker-compose.yaml`)에 `./data/game-logs/raw-events` 마운트 추가 — 현재 airflow는 `./data/game-event-logs`만 마운트함 (`data/` 전체 마운트는 `word-embedder` 서비스뿐). 적용 시 airflow 재시작 (Dec-16)
  - 파일 하나가 실패하면 임시 파일만 지우고 나머지를 계속 받은 뒤, 실패 목록이 있으면 task 실패 (Dec-13)
  ```python
  ssh = SSHHook(ssh_conn_id="game_server_sftp").get_conn()
  _, stdout, _ = ssh.exec_command(f"gzip -c {shlex.quote(remote_path)}")
  with open(tmp_path, "wb") as f:
      shutil.copyfileobj(stdout, f)
  assert stdout.channel.recv_exit_status() == 0
  # gzip 무결성 확인 후 os.replace(tmp_path, final_path)
  ```
- 완료 기준: 조건에 맞는 서버 파일(고아 `.jsonl` 포함)마다 로컬 `.gz`가 하나씩 생기고 각 줄 수가 서버 원본(`wc -l`)과 일치. 바로 한 번 더 실행하면 새로 받는 파일 0개. 기존 DAG·range 스크립트 삭제
- 진행상황: [~] DAG·단위 테스트 작성 (`airflow/dags/event_logs/collect_game_event_logs_dag.py`, 경로 `logs/raw-events` → `data/game-logs/raw-events`, Dec-19), 커밋 df04abc, 실서버 검증 대기

### Phase 3 — 기존 로그 일회성 마이그레이션 (Dec-15)
- 내용 (Phase 1 배포 후, 기존 경로가 더 이상 바뀌지 않을 때)
  1. 로컬 `data/game-event-logs/`는 손대지 않고 원본 백업으로 둔다 (읽기만, Dec-16). 검증 후 삭제 여부 결정
  2. 서버 `logs/events/`의 남은 파일(`.jsonl.zip`, 고아 `.jsonl`)과 로컬 `data/game-event-logs/`의 `.jsonl.zip`을 모두 `.jsonl.gz`로 변환해 로컬 임시 경로에 모음 (서버 `.jsonl`은 `gzip -c`, zip은 받아서 변환)
  3. 중복 제거: 압축을 푼 내용의 md5가 같은 파일은 하나만 남김 (기존 4쌍 + 서버·로컬 양쪽에 있는 같은 파일), 내용이 빈 파일(22바이트 빈 zip 등) 제외
  4. 결과를 `data/game-logs/raw-events/`로 이동. 기존 파일명(`D.jsonl.gz`, `D.<타임스탬프>.jsonl.gz`)은 새 파일명(`D.<pid>.jsonl.gz`)과 겹치지 않음
  5. 확인 후 서버 `logs/events/` 삭제 (sink가 없어 retention이 더 이상 지우지 않음)
- 완료 기준
  - 날짜별 줄 수: 마이그레이션 전(중복 쌍은 한 번만 셈) = 후
  - `data/game-logs/raw-events/`에 md5 중복 0쌍, 빈 파일 0개
  - 서버에만 있던 파일(예: 11/18 고아 파일)이 포함됨
- 진행상황: [x] 완료 (2026-11-24, `word-embedder/log_analysis/migrate_event_logs.py`) — 서버 `logs/events/`를 rsync로 백업 폴더(`data/game-logs/zip-backup/`)에 합친 뒤 443개 스캔, 빈 파일 178·중복 4쌍 제외, 261개 → `data/game-logs/raw-events/`, 날짜 209개 줄 수 일치, 재실행 시 0건. 서버 `logs/events/`와 로컬 `zip-backup/` 삭제 완료

### Phase 4 — 분석 스크립트 변경
- 내용: `overview.py`, `invalid_word_analysis.py`가 `data/game-logs/raw-events/*.jsonl.gz`를 읽도록 변경 (`pd.read_json(path, lines=True)`가 gzip 자동 인식, `ZipFile` 루프 제거)
- 완료 기준: 마이그레이션 전 `.zip`으로 돌린 결과와 마이그레이션 후 `.gz`로 돌린 결과가 중복 4일을 빼고 동일
- 진행상황: [x] 완료 (2026-11-24) — `LOG_GLOB`의 gz만 읽음, 11-10 이후 zip·gz 결과 모두 596,415행으로 일치 (전체 기간은 Phase 3 날짜별 줄 수 비교로 확인)

### Phase 5 — 운영 확인
- 내용: 서버 배포 후 첫 퀴즈 등록일(일·수·금)을 지나서 DAG 실행
- 완료 기준: 등록 중 워커가 재시작된 날도 해당 날짜의 이벤트가 KST 00:00~24:00 공백 없이 로컬에 있음 (워커 kill 순간 `enqueue` 큐 몇 줄 제외)
- 진행상황: [ ] 대기

순서: Phase 1 → Phase 2·3 (서로 무관) → Phase 4. Phase 2는 서버 새 경로가 생긴 뒤 배포한다. Phase 1은 서버 기존 경로의 고아 파일이 retention으로 지워지기 전(11/18 파일 기준 12/18경)에 배포한다. 배포 후에는 기존 경로에 retention이 돌지 않아 기한이 없다.

## 4. Verification
- 수집 완전성 — 조건(날짜 ≤ 실행일-2일)에 맞는 서버 파일 목록과 로컬 목록을 이름으로 대조, 파일별 줄 수 비교
- 압축 무결성 — 저장 전 `gzip.open`으로 끝까지 읽어 확인, 실패 시 임시 파일 삭제 후 task 실패
- 재실행 안전성 — 연속으로 두 번 실행해 두 번째 실행에서 다운로드 0건
- 작성 중 파일 제외 — 실행 시점의 활성 파일(파일명 날짜 = 실행일-1 이후)이 수집되지 않는지 확인
- retention 동작 — 로컬 임시 디렉터리에 날짜·PID가 다른 파일명으로 파일을 만들어 정리 함수 단위 테스트 (기준은 mtime이 아닌 파일명 날짜, Dec-18)
- loguru 동작 확인 — loguru 소스(`_file_sink.py`)에서 retention glob이 경로의 literal 부분(PID)을 그대로 쓰는지 확인 (Dec-6의 전제)
- 워커 분리 — 배포 후 `logs/raw-events/`에 PID가 다른 파일이 워커 수만큼 있는지 확인
- 마이그레이션 — 날짜별 줄 수 전후 비교, md5 중복·빈 파일 0개 확인 (Phase 3)

## 5. Prerequisites
- `game_server_sftp`로 SSH exec 가능 (확인됨), 서버에 `gzip` 있음 (확인됨, `zip` 없음)
- airflow 이미지에 `SSHHook`(`apache-airflow-providers-ssh`) 사용 가능 — SFTP provider 의존성으로 설치되어 있음 (확인됨)
- 게임 서버 배포 권한
- 서버 기존 경로의 고아 파일은 Phase 1 배포 전까지 1달 뒤 삭제됨 (예: 11/18 파일은 12/18경) → 그 전에 Phase 1 배포

## 6. Glossary
- **고아 파일** — 재시작으로 기록하던 워커가 사라져 rotation(=압축)되지 않고 남은 `.jsonl`
- **파일명 날짜 D** — 파일을 연 시점의 UTC 날짜. 정상 rotation 시 KST `D+1` 하루치를 담는다
- **rotation** — loguru가 매일 15:00 UTC에 현재 파일을 닫고 새 파일을 여는 것
- **retention** — rotation 때 오래된 로그 파일을 지우는 loguru 기능 (현재 1달)
- **sink** — loguru의 출력 대상. 워커 프로세스마다 따로 가진다

## 7. Backlog
- 분석 스크립트 날짜 필터: `overview.py`·`invalid_word_analysis.py`가 파일명 날짜로 `--start-date ~ --end-date`를 걸러, 파일명 D = KST D+1 때문에 첫날·마지막 날이 부분값일 수 있음 → 파일은 `start - 1일 ~ end`로 읽고 `date` 필드로 최종 필터 (작업 중 발견)
- docker 로그 rotation (`max-size` 50m, `max-file` 5) (Out에서 이동)
- 워커 kill 순간 `enqueue` 큐에 남은 로그 유실 — 서버 구조 변경 때 함께 검토 (작업 중 발견)
- 빈 `.jsonl`(rotation 전까지 이벤트가 없던 워커) 처리 — 수집은 그대로 하고 분석 스크립트에서 빈 파일을 건너뛸지 구현 때 판단 (작업 중 발견)
- 중복 파일 4쌍의 생성 경위 — PID 분리 후 재발하지 않으면 종결 (Dec-5)
