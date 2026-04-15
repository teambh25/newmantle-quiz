# 단어풀 생성
- 단어 게임에 쓸 단어를 생성하는 설계 문서
- 관련 코드는 /word-embedder에 작성

# 단어 종류
- 랭킹 단어 : 유저가 문제를 푸는데 유의미하게 정보를 얻어가도록 정제된 단어(ex. 명사와 동사만)
- 입력 가능 단어 : 랭킹 단어 외에 거의 모든 단어가 입력 가능하도록 다양한 단어를 추가함
- 유저 로그 단어 : 입력 가능 단어에 없었지만, 유저가 자주 입력해서 단어를 추가함 (아마도 랭킹으론 안쓸 계획)

# 초기 단어풀 설정
- 우리말샘 (data/)

# 테이블 구조

CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    word TEXT UNIQUE NOT NULL,
    word_type NOT NULL -- ENUM 타입으로 (1: 랭킹 단어, 2: 입력 가능 단어, 3: 유저 로그 단어) 사용
    emb VECTOR(768) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);