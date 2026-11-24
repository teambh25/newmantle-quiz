## 개요
- 매일 한번 퀴즈의 stats을 redis에서 db로 flush시키는 api를 호출하는 airflow batch
- 배치가 실행될 때마다 Redis에 저장되어 있는 모든 stats을 flush (스탯 데이터 TTL, 최근 7일 치)
- flush api
  - POST /admin/stats/flush
  - request body로 date 전송 (ex. {"date": "2026-04-13"})
  - 멱등(upsert 기반)해서 동일한 날짜를 여러번 실행해도 됨

## 구현

- **DAG 파일**: `airflow/dags/stats/flush_stat_dag.py`
- **스케줄**: 매일 17:30 KST (`30 17 * * *`)
- **catchup**: 비활성화 (Redis TTL이 7일이라 오래된 실행 복구 불필요)

### 동작 방식

1. `get_flush_dates`: 실행 시점(`data_interval_end`) 기준 오늘 포함 최근 7일치 날짜 리스트 생성
2. `flush_stat_by_date`: 날짜별로 `POST /admin/stats/flush` 호출 (7개 task로 expand)
   - 개별 날짜 실패 시 나머지 날짜는 계속 진행
   - `game_api_rate_limit` pool 사용 (game server 부하 제어)
   - 실패 시 최대 5회 재시도 (1분 간격)