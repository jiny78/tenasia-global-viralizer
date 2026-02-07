import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def retry_with_exponential_backoff(func, max_retries=3):
    """
    지수 백오프(Exponential Backoff) 방식으로 함수 실행을 재시도합니다.

    Args:
        func: 실행할 함수
        max_retries: 최대 재시도 횟수 (기본값: 3)

    Returns:
        함수 실행 결과

    Raises:
        마지막 시도에서 발생한 예외
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_message = str(e)

            # 500 에러 또는 네트워크 관련 에러인 경우에만 재시도
            is_retryable = (
                "500" in error_message or
                "503" in error_message or
                "timeout" in error_message.lower() or
                "network" in error_message.lower() or
                "connection" in error_message.lower()
            )

            if not is_retryable or attempt == max_retries - 1:
                # 재시도 불가능한 에러이거나 마지막 시도인 경우 예외 발생
                raise

            # 지수 백오프: 2^attempt 초 대기 (1차: 2초, 2차: 4초, 3차: 8초)
            wait_time = 2 ** (attempt + 1)
            print(f"API 호출 실패 (시도 {attempt + 1}/{max_retries}). {wait_time}초 후 재시도...")
            time.sleep(wait_time)


def generate_sns_posts_streaming(article_text: str, article_title: str = "", site_name: str = "해당 매체"):
    """
    한국어 기사를 받아 English와 Korean 버전의 SNS 게시물을 스트리밍 방식으로 생성합니다.
    단 한 번의 API 호출로 모든 플랫폼/언어 조합의 게시물을 JSON 형식으로 받아옵니다.

    Args:
        article_text: 한국어 기사 내용
        article_title: 한국어 기사 제목 (선택)
        site_name: 출처 사이트 이름 (선택, 기본값: "해당 매체")

    Yields:
        각 플랫폼/언어별 결과를 담은 딕셔너리
        {"platform": "x", "language": "english", "status": "completed", "content": "..."}
    """
    try:
        # 안전 설정 및 생성 설정
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        generation_config = {
            "temperature": 0.9,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 4096,
            "response_mime_type": "application/json",  # JSON 응답 강제
        }

        # Gemini 모델 초기화
        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            safety_settings=safety_settings,
            generation_config=generation_config
        )

        # 영문 사이트명 매핑
        site_name_en = {
            "텐아시아": "TenAsia",
            "한국경제": "hankyung"
        }.get(site_name, site_name)

        article_info = f"""
기사 제목: {article_title}

기사 내용:
{article_text}
"""

        # 통합 프롬프트: 한 번의 API 호출로 모든 플랫폼/언어 조합 생성
        unified_prompt = f"""당신은 K-엔터 전문 글로벌 SNS 에디터입니다.
아래 기사를 바탕으로 3개 플랫폼(X, Instagram, Threads) x 2개 언어(English, Korean) = 총 6개의 SNS 게시물을 생성하세요.

{article_info}

출처 매체: {site_name} (영문: {site_name_en})

## 플랫폼별 가이드라인:

### X (Twitter) - English
- 2-3문장 이내 (280자 제한)
- Gen Z Slang 사용 (slay, iconic, ate, serving, no cap, it's giving, the way..., not me..., bestie, main character energy)
- 번역체 금지, 네이티브 영어
- 해시태그 3-4개 (마지막에)
- 예시: "Not [Name] absolutely SLAYING at [Event]! 😭 The way they served... iconic behavior fr fr 💅 #KPop #[Name] #Viral"

### X (Twitter) - Korean
- 속보 느낌 또는 친근한 말투 (~함, ~임)
- 2-3문장 짧고 강렬하게
- 국내 커뮤니티 화제 Hook
- 적절한 '짤' 설명 (예: "이 표정 실화냐", "미쳤다 진짜")
- 해시태그 3-4개 (반드시 #{site_name} 포함)
- 예시: "ㄹㅇ 미쳤다... [이름]이 [이벤트]에서 보여준 이 모습 실화임? 🔥 팬들 다 기절각ㅋㅋㅋ #{site_name} #[이름] #화제"

### Instagram - English
- 4-5문장으로 간결
- 이모지 5-6개 전략적 배치
- 감성적이지만 짧고 임팩트 있게
- 마지막 줄에 해시태그 5개
- Gen Z 톤 유지

### Instagram - Korean
- 감성적인 문구로 공감 유도
- 4-5문장 간결하지만 감동적으로
- 이모지 5-6개 전략적 배치
- 마지막 줄 해시태그 5-7개
- **첫 두 해시태그는 반드시 #{site_name} #{site_name_en}**

### Threads - English
- 3-4문장 짧고 대화체
- 마지막은 반드시 질문으로 끝내기 (참여 유도)
- 친근한 Gen Z 톤
- 해시태그 2-3개 (중간에 자연스럽게)
- 예시: "Okay but can we talk about [topic]? 👀 Like the way [subject] is [action]... it's giving main character energy no cap 💯 What do y'all think? #KPop #[Name]"

### Threads - Korean
- 반말/존댓말 섞인 질문형 문구
- 3-4문장 짧고 친근하게
- 마지막은 반드시 질문으로 끝내기
- 해시태그 2-3개 (반드시 #{site_name} 포함)
- 친구와 대화하듯 편안한 톤
- 예시: "와 근데 진짜 [주제] 이거 실화임?? 👀 [내용] 이 정도면 ㄹㅇ 레전드 아니냐ㅋㅋㅋ 너네 생각은 어때? #{site_name} #[관련태그]"

## 출력 형식:
반드시 아래 JSON 구조로 응답하세요. 다른 설명 없이 순수 JSON만 반환하세요:

{{
  "x": {{
    "english": "X용 영문 게시물 전체 텍스트",
    "korean": "X용 한글 게시물 전체 텍스트"
  }},
  "instagram": {{
    "english": "Instagram용 영문 게시물 전체 텍스트",
    "korean": "Instagram용 한글 게시물 전체 텍스트"
  }},
  "threads": {{
    "english": "Threads용 영문 게시물 전체 텍스트",
    "korean": "Threads용 한글 게시물 전체 텍스트"
  }}
}}
"""

        # 진행 상황 표시
        yield {"platform": "all", "language": "all", "status": "generating", "content": None}

        # 재시도 로직이 포함된 API 호출
        def api_call():
            response = model.generate_content(unified_prompt)
            if not response or not response.text:
                raise Exception("Empty response from API")
            return response

        response = retry_with_exponential_backoff(api_call, max_retries=3)

        # JSON 파싱
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {str(e)}\n\nResponse text: {response.text[:500]}")

        # 각 플랫폼/언어별로 순차적으로 yield
        # X (Twitter) - English
        yield {"platform": "x", "language": "english", "status": "generating", "content": None}
        yield {"platform": "x", "language": "english", "status": "completed", "content": result["x"]["english"]}

        # X (Twitter) - Korean
        yield {"platform": "x", "language": "korean", "status": "generating", "content": None}
        yield {"platform": "x", "language": "korean", "status": "completed", "content": result["x"]["korean"]}

        # Instagram - English
        yield {"platform": "instagram", "language": "english", "status": "generating", "content": None}
        yield {"platform": "instagram", "language": "english", "status": "completed", "content": result["instagram"]["english"]}

        # Instagram - Korean
        yield {"platform": "instagram", "language": "korean", "status": "generating", "content": None}
        yield {"platform": "instagram", "language": "korean", "status": "completed", "content": result["instagram"]["korean"]}

        # Threads - English
        yield {"platform": "threads", "language": "english", "status": "generating", "content": None}
        yield {"platform": "threads", "language": "english", "status": "completed", "content": result["threads"]["english"]}

        # Threads - Korean
        yield {"platform": "threads", "language": "korean", "status": "generating", "content": None}
        yield {"platform": "threads", "language": "korean", "status": "completed", "content": result["threads"]["korean"]}

        # 최종 완료 신호
        yield {"platform": "all", "status": "completed", "model": "gemini-2.5-flash"}

    except Exception as e:
        import traceback
        error_details = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        yield {"platform": "error", "status": "error", "error": error_details}


def generate_sns_posts(article_text: str, article_title: str = "") -> dict:
    """
    한국어 기사를 받아 X, Instagram, Threads용 영문 게시물을 생성합니다.

    Args:
        article_text: 한국어 기사 내용
        article_title: 한국어 기사 제목 (선택)

    Returns:
        각 플랫폼별 게시물을 담은 딕셔너리
    """
    try:
        # Gemini 모델 초기화
        model = genai.GenerativeModel('gemini-2.5-flash')

        # 기본 페르소나 및 가이드라인
        base_instruction = """당신은 K-엔터 전문 글로벌 에디터입니다.
기사의 팩트를 유지하되, 글로벌 팬들이 클릭하고 싶게 만드는 최신 유행어(Gen Z Slang)와 감각적인 표현을 사용하세요.
번역체 느낌을 완전히 지워야 합니다. 자연스러운 네이티브 영어로 작성하세요.

Gen Z Slang 예시: slay, iconic, ate, serving, no cap, it's giving, the way..., not me..., bestie, main character energy 등"""

        article_info = f"""
기사 제목: {article_title}

기사 내용:
{article_text}
"""

        # X (Twitter) 게시물 생성
        x_prompt = f"""{base_instruction}

{article_info}

위 K-엔터 기사를 바탕으로 X(트위터)용 영문 게시물을 작성하세요.

중요 규칙:
- **2-3문장 이내로 극도로 짧게** (280자 제한)
- 가장 화제가 될 핵심 문장으로 시작
- 번역체 금지, 네이티브 Gen Z 표현 사용
- 해시태그 3-4개만 (마지막에)
- 팬들이 즉시 RT하고 싶게

예시 톤: "Not [Name] absolutely SLAYING at [Event]! 😭 The way they served... iconic behavior fr fr 💅 #KPop #[Name] #Viral"

게시물만 작성 (설명 없이):"""

        x_response = model.generate_content(x_prompt
        )

        # Instagram 게시물 생성
        instagram_prompt = f"""{base_instruction}

{article_info}

위 K-엔터 기사를 바탕으로 Instagram용 영문 게시물을 작성하세요.

중요 규칙:
- **4-5문장으로 간결하게**
- 이모지 5-6개만 전략적으로 배치
- 감성적이지만 짧고 임팩트 있게
- 마지막 줄에만 해시태그 5개 (한 줄에)
- 번역체 금지, Gen Z 톤 유지

예시 구조:
[Opening with emoji + hook sentence]
[Main content - 2-3 short sentences with Gen Z slang]
[Closing question/statement with emoji]

[Hashtag line: #Tag1 #Tag2 #Tag3 #Tag4 #Tag5]

게시물만 작성:"""

        instagram_response = model.generate_content(instagram_prompt
        )

        # Threads 게시물 생성
        threads_prompt = f"""{base_instruction}

{article_info}

위 K-엔터 기사를 바탕으로 Threads용 영문 게시물을 작성하세요.

중요 규칙:
- **3-4문장으로 짧고 대화체로**
- 마지막은 반드시 질문으로 끝내기 (참여 유도)
- 친근한 Gen Z 톤, 번역체 금지
- 해시태그 2-3개만 (중간에 자연스럽게)
- "댓글 달고 싶게" 만들기

예시 톤: "Okay but can we talk about [topic]? 👀 Like the way [subject] is [action]... it's giving main character energy no cap 💯 What do y'all think? #KPop #[Name]"

게시물만 작성:"""

        threads_response = model.generate_content(threads_prompt
        )

        return {
            "success": True,
            "posts": {
                "x": x_response.text.strip(),
                "instagram": instagram_response.text.strip(),
                "threads": threads_response.text.strip()
            },
            "model": "gemini-2.5-flash"
        }

    except Exception as e:
        return {
            "success": False,
            "posts": {
                "x": "",
                "instagram": "",
                "threads": ""
            },
            "error": str(e)
        }
