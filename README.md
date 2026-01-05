# Summary Service - LangGraph 기반 텍스트 요약 서비스

상용 수준의 채팅 및 이메일 요약 서비스입니다. LangGraph를 활용한 멀티 스텝 요약 워크플로우를 제공합니다.

## 주요 기능

- ✅ **다양한 요약 스타일**: Brief, Detailed, Bullet, Executive
- ✅ **멀티 언어 지원**: 한국어, 영어, 일본어, 중국어
- ✅ **워크플로우 기반 처리**: 전처리 → 핵심 추출 → 요약 생성 → 품질 검증
- ✅ **Redis 캐싱**: 동일 요청 빠른 응답
- ✅ **JWT 인증**: 보안 API 접근
- ✅ **Rate Limiting**: API 남용 방지
- ✅ **Prometheus 메트릭**: 모니터링 지원
- ✅ **PostgreSQL**: 데이터 영구 저장
- ✅ **Docker 지원**: 간편한 배포

## 시스템 요구사항

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (선택사항)

## 빠른 시작

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY, SECRET_KEY 등 설정
```

### 2. Docker Compose로 실행

```bash
docker-compose up -d
docker-compose logs -f app
```

### 3. 로컬에서 실행

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## API 사용법

### 사용자 등록
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'
```

### 로그인
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'
```

### 텍스트 요약
```bash
curl -X POST http://localhost:8000/api/v1/summarize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "text": "여기에 요약할 텍스트...",
    "summary_type": "chat",
    "summary_style": "brief",
    "language": "ko"
  }'
```

## 아키텍처

```
Client → FastAPI (Auth/RateLimit/LangGraph) → PostgreSQL/Redis
```

## 테스트

```bash
pytest
pytest --cov=app tests/
```

## 라이선스

MIT License
