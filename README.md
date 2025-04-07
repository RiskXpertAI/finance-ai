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
