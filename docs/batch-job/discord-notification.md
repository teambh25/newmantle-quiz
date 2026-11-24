# 배치 작업 실패 Discord 알림 설계 문서

> 배치 DAG 실패 시 Discord Webhook으로 알림을 전송하는 공통 알림 시스템 설계

## 1. Overview

Airflow 배치 작업 실패를 운영자가 빠르게 인지할 수 있도록 Discord 알림을 도입한다.
알림은 task 실패 후 모든 retry가 소진된 시점에 발동하며, 실패한 task명·에러 메시지·Airflow UI 링크를 포함한다.

적용 대상 DAG:
- `recommend_answer` (정답 단어 추천, 스케줄)
- `quiz_register_consumer` (퀴즈 등록, dataset 트리거)
- `flush_stat` (스탯 flush, 스케줄)

## 2. Requirements

### Functional Requirements
- task 실패(retry 소진 후) 시 Discord 채널에 알림 전송
- 알림에 DAG명, 실패 task명, 실행 시간, 에러 메시지 요약, Airflow UI 링크 포함
- 특정 날짜 flush 또는 퀴즈 등록 실패 시 어떤 날짜인지 파악 가능해야 함

### Non-Functional Requirements
- 알림 전송 실패가 배치 작업 자체에 영향을 주지 않아야 함 (try/except로 격리)
- 공통 코드로 관리하여 DAG별 중복 없이 재사용

## 3. Technical Decisions

### 알림 트리거 레벨
- **Choice**: Task 레벨 (`on_failure_callback`)
- **Rationale**: `flush_stat`·`quiz_register_consumer`는 날짜별로 `expand()`하므로 task 레벨에서 어떤 날짜가 실패했는지 구체적으로 파악 가능. `on_failure_callback`은 retry 소진 후에만 발동하므로 알림 중복 없음.
- **Alternatives considered**: DAG 레벨 — 실패 task 정보를 context에서 직접 파싱해야 해 복잡도 증가. expand() 구조에서 부적합.

### Discord 연동 방식
- **Choice**: Discord Webhook URL
- **Rationale**: 별도 봇 생성 없이 채널 Webhook URL로 HTTP POST만으로 충분. 메시지 수정·삭제 등 고급 기능 불필요.
- **Alternatives considered**: Discord Bot — 기능은 많으나 봇 생성·토큰 관리 오버헤드가 있고 현재 요구사항 초과.

### 알림 내용
- **Choice**: 표준 (에러 메시지 요약 + Airflow UI 링크 포함)
- **Rationale**: 알림만으로 1차 원인 파악 가능하여 Airflow UI 접속 빈도를 줄임. 에러 메시지는 일정 길이로 truncate하여 가독성 유지.
- **Alternatives considered**: 최소 알림 — UI 접속 없이는 원인 파악 불가. 상세 알림 — 로그 포함 시 알림 가독성 저하.

### Webhook URL 관리
- **Choice**: 환경변수 (`DISCORD_WEBHOOK_URL`)
- **Rationale**: 기존 `.env` 패턴(`GEMINI_API_KEY` 등 plain 시크릿)과 일관성 유지. Webhook URL은 단순 시크릿으로 Airflow Connection 구조가 불필요.
- **Alternatives considered**: Airflow Variable — UI에서 관리 편리하나 기존 패턴과 다름. Airflow Connection — Webhook에는 과한 구조.

### 공통 코드 위치
- **Choice**: `common/notifications.py`
- **Rationale**: 기존 `common/` 모듈 구조(utils, exceptions, crud 등)와 일관성. 각 DAG에서 import하여 재사용.
- **Alternatives considered**: 각 DAG 내 정의 — 코드 중복 발생.

## 4. Architecture

```
[Task 실패 (retry 소진)]
        │
        ▼
on_failure_callback 호출
        │
        ▼
common/notifications.py
  notify_failure(context)
  ├─ context에서 DAG명, task명, 실행시간, 에러 추출
  ├─ Airflow UI 링크 생성
  └─ Discord Webhook POST
        │
        ▼
Discord 채널 알림 수신
```

각 DAG는 `default_args` 또는 개별 `@task` 데코레이터에 `on_failure_callback=notify_failure`를 설정한다.

## 5. 알림 포맷

```
🚨 [recommend_answer] Task 실패

• Task: generate_candidate.get_trends_words.extract_trend_words
• 실행 시간: 2026-04-13 17:05:32 KST
• 에러: AirflowException: Gemini API quota exceeded (truncated)
• Airflow UI: http://localhost:5000/dags/recommend_answer/...
```

## 6. 환경 설정

`.env`에 추가:
```
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

## 7. Implementation Plan

1. `common/notifications.py` 작성 — `notify_failure(context)` 함수 구현
2. `os.environ`에서 `DISCORD_WEBHOOK_URL` 읽기, 미설정 시 경고 로그만 출력 (알림 실패가 배치에 영향 없도록)
3. `recommend_answer`, `quiz_register_consumer`, `flush_stat` 각 DAG에 `on_failure_callback` 추가
4. 로컬에서 강제 실패 task로 동작 확인
