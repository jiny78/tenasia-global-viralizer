import os
import json
import time
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# JSON 스키마 정의
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "kr": {
            "type": "object",
            "properties": {
                "x": {"type": "string", "description": "X(Twitter)용 한국어 게시물 (140-200자)"},
                "insta": {"type": "string", "description": "Instagram용 한국어 게시물 (최소 3문단, 해시태그 10개)"},
                "threads": {"type": "string", "description": "Threads용 한국어 게시물 (300자 내외, 질문 포함)"}
            },
            "required": ["x", "insta", "threads"]
        },
        "en": {
            "type": "object",
            "properties": {
                "x": {"type": "string", "description": "X(Twitter)용 영문 게시물 (140-200 chars)"},
                "insta": {"type": "string", "description": "Instagram용 영문 게시물 (min 3 paragraphs, 10 hashtags)"},
                "threads": {"type": "string", "description": "Threads용 영문 게시물 (~300 chars, with question)"}
            },
            "required": ["x", "insta", "threads"]
        },
        "review_score": {
            "type": "object",
            "description": "AI가 스스로 매긴 완성도 점수 (1-10)",
            "properties": {
                "kr": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X 게시물 완성도 점수 (1-10)"},
                        "insta": {"type": "integer", "description": "Instagram 게시물 완성도 점수 (1-10)"},
                        "threads": {"type": "integer", "description": "Threads 게시물 완성도 점수 (1-10)"}
                    },
                    "required": ["x", "insta", "threads"]
                },
                "en": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X post quality score (1-10)"},
                        "insta": {"type": "integer", "description": "Instagram post quality score (1-10)"},
                        "threads": {"type": "integer", "description": "Threads post quality score (1-10)"}
                    },
                    "required": ["x", "insta", "threads"]
                }
            },
            "required": ["kr", "en"]
        },
        "key_takeaway": {
            "type": "object",
            "description": "기사의 핵심 요약 1줄",
            "properties": {
                "kr": {"type": "string", "description": "한국어 핵심 요약"},
                "en": {"type": "string", "description": "영문 핵심 요약"}
            },
            "required": ["kr", "en"]
        }
    },
    "required": ["kr", "en", "review_score", "key_takeaway"]
}


def retry_with_exponential_backoff(func, max_retries=3, progress_callback=None):
    """
    지수 백오프(Exponential Backoff) 방식으로 함수 실행을 재시도합니다.

    Args:
        func: 실행할 함수
        max_retries: 최대 재시도 횟수 (기본값: 3)
        progress_callback: 재시도 진행 상황을 알리는 콜백 함수 (선택)

    Returns:
        함수 실행 결과

    Raises:
        마지막 시도에서 발생한 예외
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except (google_exceptions.InternalServerError,
                google_exceptions.ResourceExhausted,
                google_exceptions.ServiceUnavailable) as e:
            last_exception = e

            # 마지막 시도인 경우 예외 발생
            if attempt == max_retries - 1:
                raise

            # 지수 백오프: 2^attempt 초 대기 (1차: 2초, 2차: 4초, 3차: 8초)
            wait_time = 2 ** (attempt + 1)

            # 진행 상황 콜백 호출
            if progress_callback:
                progress_callback(
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    wait_time=wait_time,
                    error=str(e)
                )

            time.sleep(wait_time)
        except Exception as e:
            # 재시도 불가능한 에러는 즉시 발생
            raise

    # 여기 도달하면 안 되지만, 안전을 위해
    if last_exception:
        raise last_exception


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
            "response_schema": RESPONSE_SCHEMA,  # JSON 스키마 정의
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
        unified_prompt = f"""당신은 {site_name}의 수석 글로벌 SNS 에디터입니다.
아래 기사를 바탕으로 3개 플랫폼(X, Instagram, Threads) x 2개 언어(English, Korean) = 총 6개의 SNS 게시물을 생성하세요.

{article_info}

출처 매체: {site_name} (영문: {site_name_en})

## 🎯 완성도 체크포인트 (Self-Correction)

게시물 작성 전, 반드시 다음 3가지를 스스로 검토하세요:

✓ **팩트 체크**: 기사 본문의 정보와 100% 일치하는가? 숫자, 날짜, 인용문 등을 정확히 사용했는가?
✓ **품격 유지**: {site_name}의 브랜드 이미지에 맞는 고급스럽고 전문적인 어휘를 사용했는가?
✓ **자연스러운 현지화**: 번역투가 아닌, 해당 언어권의 인플루언서가 작성한 것 같은 자연스러운 표현인가?

각 게시물마다 위 3가지 기준으로 1-10점의 review_score를 매기세요.

## 📱 플랫폼별 상세 가이드라인

### 🐦 X (Twitter) - Punchy & Viral

**English Version:**
- **길이**: 140-200자 (280자 제한 안에서 짧게)
- **구조**: 가장 논란이 되거나 화제가 될 **'한 줄'**을 최상단에 배치
- **목표**: 클릭 유도, RT 유발
- **톤**: Gen Z Slang 적극 활용 (slay, iconic, ate, serving, no cap, it's giving, the way..., not me..., bestie, main character energy)
- **번역체 금지**: 완전한 네이티브 영어
- **해시태그**: 3-4개 (마지막에)
- **예시**: "Not [Name] absolutely SLAYING at [Event]! 😭 The way they served... iconic behavior fr fr 💅 #KPop #[Name] #Viral"

**Korean Version:**
- **길이**: 140-200자
- **구조**: 속보 느낌의 긴박함 또는 팬들의 공감을 사는 친근한 말투 (~함, ~임)
- **목표**: 클릭 유도, RT 유발
- **톤**: 국내 커뮤니티에서 화제가 될 법한 Hook (예: "ㄹㅇ 미쳤다...", "이거 실화임??")
- **적절한 '짤' 설명**: "이 표정 실화냐", "미쳤다 진짜" 등
- **해시태그**: 3-4개 (반드시 #{site_name} 포함)
- **예시**: "ㄹㅇ 미쳤다... [이름]이 [이벤트]에서 보여준 이 모습 실화임? 🔥 팬들 다 기절각ㅋㅋㅋ #{site_name} #[이름] #화제"

### 📸 Instagram - Long-form Storytelling

**English Version:**
- **길이**: 최소 3문단 이상 (줄바꿈으로 가독성 확보)
- **구조**:
  - 1문단: 감성적인 Hook + 이모지
  - 2-3문단: 기사 속 구체적인 인용문, 차트 기록, 숫자 등을 활용한 스토리텔링
  - 마지막 문단: 감동적인 마무리 + 질문
- **톤**: Gen Z 감성 + 고급스러운 어휘
- **번역체 금지**: 현지 인플루언서의 자연스러운 말투
- **해시태그**: 10개 (마지막 줄에 모두 배치)
- **예시**:
  ```
  ✨ When [Artist] said "[quote from article]"... I felt that. 💫

  Their journey from [specific detail] to [achievement with numbers] is literally the definition of dedication. The way they [action] while maintaining [quality] shows true artistry at its finest.

  This is why we stan real talent. 👑 What moment touched your heart the most?

  #KPop #[Artist] #TenAsia #Viral #Music #Inspiration #Icon #Goals #Legend #Masterpiece
  ```

**Korean Version:**
- **길이**: 최소 3문단 이상 (줄바꿈으로 가독성 확보)
- **구조**:
  - 1문단: 감성적인 Hook + 이모지
  - 2-3문단: 기사 속 구체적인 인용문, 차트 기록, 숫자 등을 활용한 스토리텔링
  - 마지막 문단: 감동적인 마무리 + 질문
- **톤**: {site_name}의 품격에 맞는 고급스러운 한국어 + 현대적인 감성
- **해시태그**: 10개 (첫 두 개는 반드시 #{site_name} #{site_name_en}, 마지막 줄에 모두 배치)
- **예시**:
  ```
  ✨ [아티스트]가 "[기사 속 인용문]"이라고 말했을 때, 가슴이 뭉클했다. 💫

  [구체적 수치]에서 [성과]까지의 여정은 단순한 성공 그 이상이다. [구체적 행동]을 하면서도 [품질]을 유지하는 모습에서 진정한 아티스트의 면모가 보인다.

  이게 바로 진짜 실력파를 응원하는 이유. 👑 여러분은 어떤 순간이 가장 감동적이었나요?

  #{site_name} #{site_name_en} #케이팝 #[아티스트] #음악 #영감 #아이콘 #목표 #전설 #명작
  ```

### 🧵 Threads - Engaging Discussion

**English Version:**
- **길이**: 300자 내외
- **구조**: 텍스트 위주, 마지막은 **반드시 질문으로 끝내기**
- **목표**: 댓글 반응 유도, 팬들의 의견 수집
- **톤**: 친근한 Gen Z 대화체
- **해시태그**: 2-3개 (자연스럽게 중간에)
- **예시**: "Okay but can we talk about how [Artist] just [achievement]? 👀 Like the way they [specific action from article]... it's giving main character energy no cap 💯 I'm genuinely curious - what do y'all think about this? Drop your thoughts below! #KPop #[Artist]"

**Korean Version:**
- **길이**: 300자 내외
- **구조**: 텍스트 위주, 마지막은 **반드시 질문으로 끝내기**
- **목표**: 댓글 반응 유도, 팬들의 의견 수집
- **톤**: 반말/존댓말 섞인 친근한 대화체
- **해시태그**: 2-3개 (반드시 #{site_name} 포함, 자연스럽게 중간에)
- **예시**: "와 근데 진짜 [아티스트]가 [성과] 달성한 거 실화임?? 👀 기사 보니까 [구체적 내용]이라는데, 이 정도면 ㄹㅇ 레전드 아니냐ㅋㅋㅋ 솔직히 너네 생각은 어때? 댓글로 의견 좀 남겨줘! #{site_name} #[아티스트]"

## 📤 출력 형식

반드시 아래 JSON 구조로 응답하세요. 다른 설명 없이 순수 JSON만 반환하세요:

{{
  "kr": {{
    "x": "X용 한국어 게시물 (140-200자)",
    "insta": "Instagram용 한국어 게시물 (최소 3문단, 해시태그 10개)",
    "threads": "Threads용 한국어 게시물 (300자 내외, 질문 포함)"
  }},
  "en": {{
    "x": "X용 영문 게시물 (140-200 chars)",
    "insta": "Instagram용 영문 게시물 (min 3 paragraphs, 10 hashtags)",
    "threads": "Threads용 영문 게시물 (~300 chars, with question)"
  }},
  "review_score": {{
    "kr": {{
      "x": 8,  // 1-10 점수 (팩트 정확성, 품격, 자연스러움 기준)
      "insta": 9,
      "threads": 7
    }},
    "en": {{
      "x": 9,
      "insta": 8,
      "threads": 9
    }}
  }},
  "key_takeaway": {{
    "kr": "이 기사의 핵심 요약을 한 줄로 (예: '[아티스트]가 [성과]를 달성하며 새로운 역사를 썼다')",
    "en": "One-line key takeaway (e.g., '[Artist] makes history with [achievement]')"
  }}
}}

**중요**: 각 게시물을 작성한 후, 완성도 체크포인트 3가지(팩트 정확성, 품격, 자연스러움)를 기준으로 1-10점의 review_score를 정직하게 매기세요.
"""

        # 진행 상황 표시
        yield {"platform": "all", "language": "all", "status": "generating", "content": None}

        # 재시도 진행 상황을 알리는 콜백
        def retry_progress_callback(attempt, max_retries, wait_time, error):
            yield {
                "platform": "retry",
                "status": "retrying",
                "attempt": attempt,
                "max_retries": max_retries,
                "wait_time": wait_time,
                "error": error
            }

        # 재시도 로직이 포함된 API 호출
        def api_call():
            response = model.generate_content(unified_prompt)
            if not response or not response.text:
                raise Exception("Empty response from API")
            return response

        # 재시도 진행 상황을 yield하기 위한 wrapper
        retry_attempts = []

        def progress_callback(attempt, max_retries, wait_time, error):
            retry_attempts.append({
                "attempt": attempt,
                "max_retries": max_retries,
                "wait_time": wait_time,
                "error": error
            })

        response = retry_with_exponential_backoff(
            api_call,
            max_retries=3,
            progress_callback=progress_callback
        )

        # 재시도 발생 시 알림
        for retry_info in retry_attempts:
            yield {
                "platform": "retry",
                "status": "retrying",
                "attempt": retry_info["attempt"],
                "max_retries": retry_info["max_retries"],
                "wait_time": retry_info["wait_time"],
                "error": retry_info["error"]
            }

        # JSON 파싱
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {str(e)}\n\nResponse text: {response.text[:500]}")

        # 각 플랫폼/언어별로 순차적으로 yield
        # X (Twitter) - English
        yield {"platform": "x", "language": "english", "status": "generating", "content": None}
        yield {"platform": "x", "language": "english", "status": "completed", "content": result["en"]["x"]}

        # X (Twitter) - Korean
        yield {"platform": "x", "language": "korean", "status": "generating", "content": None}
        yield {"platform": "x", "language": "korean", "status": "completed", "content": result["kr"]["x"]}

        # Instagram - English
        yield {"platform": "instagram", "language": "english", "status": "generating", "content": None}
        yield {"platform": "instagram", "language": "english", "status": "completed", "content": result["en"]["insta"]}

        # Instagram - Korean
        yield {"platform": "instagram", "language": "korean", "status": "generating", "content": None}
        yield {"platform": "instagram", "language": "korean", "status": "completed", "content": result["kr"]["insta"]}

        # Threads - English
        yield {"platform": "threads", "language": "english", "status": "generating", "content": None}
        yield {"platform": "threads", "language": "english", "status": "completed", "content": result["en"]["threads"]}

        # Threads - Korean
        yield {"platform": "threads", "language": "korean", "status": "generating", "content": None}
        yield {"platform": "threads", "language": "korean", "status": "completed", "content": result["kr"]["threads"]}

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
