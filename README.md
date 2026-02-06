# 🌐 Global Viralizer

한국 언론사 기사를 글로벌 바이럴 SNS 콘텐츠로 자동 변환하는 AI 도구

## ✨ 주요 기능

- 📰 **URL 자동 추출**: Jina Reader API로 기사 자동 추출 + 출처 인식
- 🏢 **지원 언론사**: 텐아시아, 한국경제
- 🌍 **이중 언어 생성**: English & Korean 버전 자동 생성
- 📱 **3개 플랫폼 지원**: X (Twitter), Instagram, Threads
- 🎨 **실시간 스트리밍**: 각 플랫폼 결과를 즉시 확인
- 🤖 **AI 최적화**: Google Gemini 2.5 Flash 사용
- 🏷️ **자동 태그**: 출처 사이트 이름을 자동으로 태그에 포함

## 🚀 빠른 시작

### 환경 변수 설정

`.env` 파일을 생성하고 Google API Key를 추가하세요:

```
GOOGLE_API_KEY=your_google_api_key_here
```

### 설치 및 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📋 사용 방법

**방법 1: URL 자동 추출**
1. 텐아시아 또는 한국경제 기사 URL 입력
2. "Extract Article" 버튼 클릭
3. 자동으로 출처 인식 + SNS 게시물 생성
4. English/Korean 탭에서 결과 확인
5. 코드 블록에서 복사하여 사용

**방법 2: 직접 입력**
1. 기사 내용 직접 붙여넣기
2. "Generate SNS Posts" 버튼 클릭
3. 결과 확인 및 복사

## 📰 지원 언론사

- **텐아시아** (tenasia.co.kr)
- **한국경제** (hankyung.com)

## 🛠 기술 스택

- **Frontend**: Streamlit
- **AI**: Google Gemini 2.5 Flash
- **Article Extraction**: Jina Reader API
- **Language**: Python 3.9+

## 📝 라이선스

Private Use Only

---

Powered by Google Gemini AI 🤖
