# 📈 RiskXpertAI

**AI 기반 금융지표 예측 챗봇 서비스**  
Transformer 기반 시계열 예측 모델 + GPT 기반 요약 시나리오 + 실시간 스트리밍 챗 응답

---

## 🧠 서비스 흐름

---

## 💡 핵심 기능

- ✅ **Transformer 기반 시계열 예측**
- ✨ **GPT-3.5 기반 요약 + 시나리오 생성**
- ⚡ **스트리밍 기반 응답 처리**
- 🧠 **Redis 캐시로 속도 최적화**
- 💾 **MongoDB로 사용자 대화 저장**
- 🔐 **카카오 로그인(OAuth2) 인증 연동**
- 🐳 **Docker 환경 구성 (로컬 / 프로덕션 분리)**

---

## 🖥️ 사용자 흐름

1. **카카오 로그인** → JWT 발급 후 프론트 전달
2. **메인 페이지 진입** → 개월 수 + 사용자 질문 입력
3. FastAPI → Redis에서 캐시 확인  
   - 캐시 존재 → 바로 스트리밍 출력  
   - 캐시 없음 → 아래 순서로 처리:
     1. Transformer 예측
     2. GPT 요약 생성
     3. GPT 시나리오 스트리밍 생성
     4. Redis 저장 + Mongo 저장
     5. 스트리밍 출력

---

## 📌 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | FastAPI, Pydantic, Starlette |
| AI | PyTorch, Hugging Face Transformers, OpenAI GPT |
| 데이터 | Redis (캐시), MongoDB (기록) |
| 인증 | Kakao OAuth2.0, JWT |
| 배포 | Docker, Docker Compose, Ngrok |
| 프론트 | HTML/CSS + JS (Vanilla) |

---

## 🎉 특징 요약

- 🚀 **"챗"처럼 빠르게**, **분석처럼 똑똑하게**
- 📊 시계열 기반 **실제 금융 데이터**를 예측
- 🤖 GPT를 두 번 돌려 요약 + 시나리오를 분리
- 🔄 Redis로 응답 캐싱하여 빠른 재질문 응답
- 💬 프론트엔드에서 **스트리밍 방식으로 출력**

---

## 🔒 로그인 & 인증

- 사용자는 **카카오 로그인**으로 진입
- JWT로 access_token, refresh_token 발급
- 토큰은 `localStorage`에 저장되어 인증 유지
- `/main` 페이지 진입 시 자동 리디렉션/인증 확인

---

## 📌 추가 예정

- [ ] 사용자별 기록 조회 페이지
- [ ] 금융 뉴스 요약 기능
- [ ] 사용자 질문 기반 그래프 시각화


---

## 운영 인프라 아키텍처 및 비용 정리

### 서비스 개요
- 프레임워크: FastAPI (챗봇 API)
- 기능: OpenAI API 2회 호출 + Hugging Face 기반 커스텀 Transformer 추론
- 데이터베이스/캐시: MongoDB Atlas, Redis Labs (서드파티)
- 트래픽: 하루 100명 이하
- 운영 목표: 비용 최소화, ECS 경험, 무중단 배포 구성
- 운영 기간: 2개월 예정

---

### 인프라 구성

| 구성 요소 | 선택 | 이유 |
|-----------|------|------|
| ECS (EC2 기반) | 사용 | Fargate보다 24시간 운영 시 비용 저렴함 |
| EC2 t3.small | 사용 | 모델 + API + 정적 파일 운영에 2GB 메모리 필요 |
| CloudWatch | 미사용 | Kafka + Airflow로 로깅/모니터링 대체 |
| Nginx + Certbot | 사용 | EC2 내부에서 정적 자산 + HTTPS 처리 |
| ALB, RDS, Lambda, Fargate | 미사용 | 비용 절감 및 단순화 목적 |

---

### 전체 구성도
```
사용자
│
└─> Nginx (EC2 내부)
├ /           → index.html, JS, CSS (정적 자산)
└ /api        → FastAPI API 서버 (ECS Task)
├─ 커스텀 Transformer 추론 (PyTorch)
├─ OpenAI API 호출 (2회)
├─ Hugging Face 스타일 모델 응답
├─ Redis Labs (캐시)
└─ MongoDB Atlas (대화 기록 저장)

[로깅 및 배치]
└─ Kafka (서드파티)
└─ Airflow (서드파티) → 추후 알림, 로그 흐름, ETL 처리

[배포]
└─ GitHub Actions
└─ ECS 서비스에 무중단 배포 (force-new-deployment)
```

---

### 배포 방식

- GitHub Actions + ECS 무중단 배포 (`force-new-deployment` 사용)
- Blue/Green 없이 간단한 Canary 스타일 배포
- 정적 파일은 Nginx에서 서빙, API는 ECS에서 처리

---

### 예상 운영 비용 (2개월 기준, 24시간 상시 운영)

| 항목 | 월간 | 2개월 합계 |
|------|------|------------|
| EC2 t3.small | $15.18 | $30.36 |
| EBS 기본 스토리지 (8GB) | 약 $0.80 | 약 $1.60 |
| 기타 (도메인 등 선택) | 약 $1 미만 | 약 $1 미만 |
| **총합** |  | **약 $31~32** |

> 프리 티어 계정은 사용하지 않음  
> CloudWatch, RDS, ALB 등 고비용 구성 요소는 제외  
> 서드파티 기반으로 AWS 비용 최소화


