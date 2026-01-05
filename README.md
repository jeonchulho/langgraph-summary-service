# LangGraph 기반 상용 텍스트 요약 서비스

LangGraph를 사용한 프로덕션 수준의 채팅/메일 요약 서비스입니다.

## 주요 기능

### 🚀 핵심 기능
- **LangGraph 워크플로우**: StateGraph 기반 5단계 요약 프로세스
- **다양한 요약 스타일**: Brief, Detailed, Bullet, Executive
- **다양한 텍스트 타입**: Email, Chat, Document
- **배치 처리**: 최대 10개 텍스트 동시 처리
- **품질 검증**: 자동 품질 평가 및 재작성 (< 0.6 점수)
- **캐싱**: Redis 기반 SHA256 캐시 (1시간 TTL)
- **인증**: JWT 토큰 기반 인증
- **Rate Limiting**: 분당 요청 제한
- **모니터링**: Prometheus 메트릭 + Sentry 통합

### 🎯 LangGraph 워크플로우
```
Preprocess → Extract Key Points → Generate Summary → Validate Quality
                                                            ↓
                                                    (if score < 0.6)
                                                            ↓
                                                     Refine Summary
```

## 시스템 요구사항

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15
- Redis 7
- OpenAI API Key

## 빠른 시작

### 1. 환경 변수 설정

```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY and SECRET_KEY
```

필수 환경 변수:
- `OPENAI_API_KEY`: OpenAI API 키
- `SECRET_KEY`: JWT 토큰 암호화 키

### 2. Docker Compose로 실행

```bash
# 컨테이너 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f app

# 상태 확인
curl http://localhost:8000/health
```

### 3. API 문서 접속

브라우저에서 http://localhost:8000/docs 접속

## API 사용 예제

### 1. 사용자 등록

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123"
  }'
```

### 2. 로그인

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123"
  }'
```

응답:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. 텍스트 요약

```bash
curl -X POST "http://localhost:8000/api/v1/summarize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your long text here... (minimum 50 characters)",
    "type": "document",
    "style": "brief"
  }'
```

응답:
```json
{
  "id": 1,
  "summary": "Brief summary of the text...",
  "key_points": [
    "Key point 1",
    "Key point 2",
    "Key point 3"
  ],
  "metrics": {
    "quality_score": 0.85,
    "processing_time": 2.3,
    "token_count": 450,
    "cost": 0.009
  },
  "created_at": "2026-01-05T08:00:00"
}
```

### 4. 배치 요약

```bash
curl -X POST "http://localhost:8000/api/v1/summarize/batch" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "First text to summarize...",
      "Second text to summarize...",
      "Third text to summarize..."
    ],
    "type": "document",
    "style": "bullet"
  }'
```

### 5. 요약 목록 조회

```bash
curl -X GET "http://localhost:8000/api/v1/summaries?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. 사용량 통계

```bash
curl -X GET "http://localhost:8000/api/v1/usage" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 아키텍처

### 컴포넌트 구조

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Auth API   │  │  Summary API │  │  Metrics API │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Auth Service │  │ Cache Service│  │   LangGraph  │ │
│  └──────────────┘  └──────────────┘  │   Workflow   │ │
│                                       └──────────────┘ │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  PostgreSQL  │  │    Redis     │  │  OpenAI API  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 디렉토리 구조

```
app/
├── __init__.py
├── main.py                 # FastAPI 애플리케이션
├── config.py               # 설정 관리
├── models/
│   ├── database.py         # SQLAlchemy 모델
│   └── schemas.py          # Pydantic 스키마
├── agents/
│   ├── workflow.py         # LangGraph 워크플로우
│   └── summarizer.py       # 요약 서비스
├── api/
│   ├── routes.py           # API 엔드포인트
│   └── dependencies.py     # 의존성 주입
├── services/
│   ├── auth.py             # 인증 서비스
│   └── cache.py            # 캐시 서비스
└── utils/
    ├── logger.py           # 로깅
    └── metrics.py          # Prometheus 메트릭
```

## 요약 스타일

### Brief (간단)
- 2-3 문장 요약
- 핵심 내용만 포함
- 빠른 파악용

### Detailed (상세)
- 5-7 문장 요약
- 주요 세부 사항 포함
- 완전한 이해 필요시

### Bullet (불릿 포인트)
- 5-7개 주요 항목
- 구조화된 형식
- 항목별 정리 필요시

### Executive (임원용)
- 결론 우선
- 핵심 의사결정 정보
- 비즈니스 컨텍스트

## 텍스트 타입별 전처리

### Email
- 메타데이터 제거 (From, To, Subject)
- HTML 태그 제거
- 본문만 추출

### Chat
- 타임스탬프 제거
- 대화 내용만 유지
- 메시지 정규화

### Document
- 일반 텍스트 정리
- 공백 정규화
- 포맷 통일

## 모니터링

### Prometheus 메트릭

메트릭 엔드포인트: http://localhost:8000/metrics

제공 메트릭:
- `app_request_count`: 요청 수 (method, endpoint, status)
- `app_request_duration_seconds`: 요청 처리 시간
- `summary_total`: 생성된 요약 수 (type, style)
- `summary_duration_seconds`: 요약 생성 시간
- `summary_quality_score`: 품질 점수 분포
- `cache_hits_total`: 캐시 히트 수
- `cache_misses_total`: 캐시 미스 수
- `active_requests`: 활성 요청 수
- `database_connections`: DB 연결 수

### Health Check

```bash
curl http://localhost:8000/health
```

응답:
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "timestamp": "2026-01-05T08:00:00"
}
```

### 로그

로그는 `logs/` 디렉토리에 저장됩니다:
- 구조화된 JSON 로그
- 요청/응답 로깅
- 에러 추적

## 테스트

### 전체 테스트 실행

```bash
# Docker 컨테이너 내부에서
docker-compose exec app pytest tests/ -v

# 로컬에서
make test
```

### 커버리지 포함 테스트

```bash
make test-cov
```

### 특정 테스트만 실행

```bash
pytest tests/test_summarizer.py -v
```

## 개발

### 로컬 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
uvicorn app.main:app --reload

# 또는 Make 사용
make dev
```

### 데이터베이스 마이그레이션

```bash
# 마이그레이션 생성
make migrate-create msg="Add new table"

# 마이그레이션 적용
make migrate
```

### 코드 정리

```bash
make clean
```

## 보안

### 구현된 보안 기능
- ✅ JWT 토큰 기반 인증
- ✅ Bcrypt 비밀번호 해싱
- ✅ Rate limiting
- ✅ SQL Injection 방지 (SQLAlchemy ORM)
- ✅ CORS 설정
- ✅ 입력 검증 (Pydantic)
- ✅ 환경 변수를 통한 비밀 관리

### 프로덕션 체크리스트
- [ ] `.env` 파일의 `SECRET_KEY` 변경
- [ ] CORS 설정을 실제 도메인으로 제한
- [ ] Rate limiting 값 조정
- [ ] Sentry DSN 설정
- [ ] HTTPS 사용
- [ ] 정기적인 의존성 업데이트
- [ ] 로그 모니터링 설정

## 문제 해결

### OpenAI API 에러
```bash
# .env 파일에서 OPENAI_API_KEY 확인
cat .env | grep OPENAI_API_KEY
```

### 데이터베이스 연결 실패
```bash
# PostgreSQL 컨테이너 상태 확인
docker-compose ps postgres

# 로그 확인
docker-compose logs postgres
```

### Redis 연결 실패
```bash
# Redis 컨테이너 상태 확인
docker-compose ps redis

# Redis CLI 테스트
docker-compose exec redis redis-cli ping
```

## 성능 최적화

### 캐싱
- Redis 캐시로 중복 요청 방지
- SHA256 기반 캐시 키
- 1시간 TTL

### 배치 처리
- 최대 10개 텍스트 동시 처리
- 비동기 처리로 성능 향상

### 데이터베이스
- 인덱스 최적화
- 연결 풀링
- 비동기 쿼리

## 라이선스

MIT License

## 기여

이슈와 PR을 환영합니다!

## 문의

문제가 있으시면 GitHub Issues를 통해 문의해주세요.