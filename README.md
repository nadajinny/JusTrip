# 🌤️ AI-Powered Travel Planner with Real-Time Weather Forecast

**실시간 날씨 기반 GPT 여행 활동 추천 웹앱**  
Live weather + Vertex AI (GPT) → 맞춤형 활동 제안!

---

## 🎯 1. 문제 정의 (Problem Statement)

> “여행을 가려고 할 때, 현재 날씨나 장소 조건에 맞는 활동을 쉽게 추천해주는 서비스가 부족하다.”

- 사용자는 날씨에 따라 여행 계획을 변경해야 하지만, 직접 검색하거나 비교해야 함.
- 특히 실시간 날씨와 활동 추천을 함께 제공하는 자동화된 서비스는 드물다.

✅ **→ 이 문제를 해결하기 위해 실시간 날씨 데이터 + AI 추천을 결합한 시스템을 만든다.**

---

## 🌍 2. 해결 방안 (Solution Overview)

> “도시명을 입력하면, 실시간 날씨 정보를 바탕으로 Vertex AI가 추천 여행 활동을 제안해주는 웹앱입니다.”

- Google Maps API 또는 Weather API를 통해 **현재 날씨 정보를 수집**
- 수집된 정보를 기반으로 **Google Vertex AI (PaLM2 또는 Gemini)** 에게 프롬프트를 보내 맞춤형 여행 활동 추천
- Google Apps Script 또는 GCP 환경에서 손쉽게 배포 가능

✅ **핵심 포인트**: `날씨 + AI = 개인화된 스마트 여행 추천`

---

## 🧱 3. 시스템 구성 요소 (Architecture Breakdown)

| 구성 요소         | 설명                                                |
|------------------|-----------------------------------------------------|
| 🌐 UI             | Google Apps Script 기반 웹 인터페이스 or Firebase 호스팅 |
| ☁️ Weather API    | OpenWeatherMap 또는 Google Maps Weather API         |
| 🧠 Vertex AI      | 날씨 + 위치 → 자연어 기반 활동 추천 생성            |
| ☁️ Google Cloud   | Cloud Run / Functions / Secret Manager / Logging 등 |

---

## 🔄 4. 사용자 흐름 (User Flow)

1. 사용자가 웹에 접속
2. 도시 입력 (예: `"Seoul"`)
3. 앱이 Google Weather API로 실시간 날씨 정보 조회
4. Vertex AI로 프롬프트 전송 → 활동 추천 결과 생성
5. 결과를 웹 UI에 출력

💬 예시 출력:
오늘 서울은 흐리고 기온은 22°C입니다.
추천 활동:

실내 미술관 투어
북촌 한옥마을 산책
스타필드에서 쇼핑 및 식사


---

## 📅 5. 개발 및 배포 계획 (3-Day Plan)

| Day    | 작업 내용                                      |
|--------|-----------------------------------------------|
| 1일차   | UI 설계, 날씨 API 연동, GCP 프로젝트 설정         |
| 2일차   | Vertex AI 연결, 프롬프트 설계, 결과 표시            |
| 3일차   | GCP 배포, UI 다듬기, 에러 처리 추가               |

---

## 💡 요약 키워드

- **Keyword #1**: 실시간 개인화 (Real-time personalization)
- **Keyword #2**: LLM 활용 (Prompt-based activity generation)
- **Keyword #3**: GCP 통합 (Google-first architecture)
- **Keyword #4**: 빠른 배포 (Serverless Web App)

---

## 🔜 다음 단계

> 음식점 추천, 인기 명소 정보 등 **추가 추천 기능** 연동 예정!
