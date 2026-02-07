import os
import json
import time
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from dotenv import load_dotenv
import config

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
        "viral_analysis": {
            "type": "object",
            "description": "각 플랫폼별 바이럴 가능성 분석 (1-100점)",
            "properties": {
                "kr": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "integer", "description": "바이럴 점수 (1-100)"},
                                "reason": {"type": "string", "description": "점수 근거 한 문장"}
                            },
                            "required": ["score", "reason"]
                        },
                        "insta": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "integer", "description": "바이럴 점수 (1-100)"},
                                "reason": {"type": "string", "description": "점수 근거 한 문장"}
                            },
                            "required": ["score", "reason"]
                        },
                        "threads": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "integer", "description": "바이럴 점수 (1-100)"},
                                "reason": {"type": "string", "description": "점수 근거 한 문장"}
                            },
                            "required": ["score", "reason"]
                        }
                    },
                    "required": ["x", "insta", "threads"]
                },
                "en": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "integer", "description": "Viral score (1-100)"},
                                "reason": {"type": "string", "description": "Score reasoning in one sentence"}
                            },
                            "required": ["score", "reason"]
                        },
                        "insta": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "integer", "description": "Viral score (1-100)"},
                                "reason": {"type": "string", "description": "Score reasoning in one sentence"}
                            },
                            "required": ["score", "reason"]
                        },
                        "threads": {
                            "type": "object",
                            "properties": {
                                "score": {"type": "integer", "description": "Viral score (1-100)"},
                                "reason": {"type": "string", "description": "Score reasoning in one sentence"}
                            },
                            "required": ["score", "reason"]
                        }
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
    "required": ["kr", "en", "review_score", "viral_analysis", "key_takeaway"]
}


def safe_generate_content(model, prompt, max_retries=None, progress_callback=None):
    """
    안정적인 콘텐츠 생성 래퍼 함수

    500 서버 에러, 429 쿼터 에러, 503 서비스 불가 에러 발생 시
    Exponential Backoff 방식으로 재시도합니다.

    Args:
        model: genai.GenerativeModel 인스턴스
        prompt: 생성할 프롬프트
        max_retries: 최대 재시도 횟수 (기본값: config.MAX_RETRIES)
        progress_callback: 재시도 진행 상황을 알리는 콜백 함수 (선택)

    Returns:
        생성된 응답

    Raises:
        마지막 시도에서 발생한 예외
    """
    if max_retries is None:
        max_retries = config.MAX_RETRIES

    last_exception = None

    for attempt in range(max_retries):
        try:
            # API 호출
            response = model.generate_content(prompt)

            # 응답 유효성 검증
            if not response or not response.text:
                raise Exception("Empty response from API")

            return response

        except (google_exceptions.InternalServerError,      # 500 에러
                google_exceptions.ResourceExhausted,        # 429 쿼터 에러
                google_exceptions.ServiceUnavailable,       # 503 에러
                google_exceptions.DeadlineExceeded) as e:   # 타임아웃 에러

            last_exception = e
            error_type = type(e).__name__

            # 마지막 시도인 경우 예외 발생
            if attempt == max_retries - 1:
                raise Exception(f"API 호출 실패 (재시도 {max_retries}회 모두 실패): {error_type} - {str(e)}")

            # 지수 백오프: BASE_WAIT_TIME * (2 ** attempt)
            # 1차: 2초, 2차: 4초, 3차: 8초
            wait_time = config.BASE_WAIT_TIME * (2 ** attempt)

            # 429 에러(쿼터 초과)의 경우 더 긴 대기
            if isinstance(e, google_exceptions.ResourceExhausted):
                wait_time = wait_time * 2  # 2배 더 대기

            # 진행 상황 콜백 호출
            if progress_callback:
                progress_callback(
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    wait_time=wait_time,
                    error=f"{error_type}: {str(e)}"
                )

            # 대기
            time.sleep(wait_time)

        except Exception as e:
            # 재시도 불가능한 에러는 즉시 발생
            raise Exception(f"재시도 불가능한 에러: {type(e).__name__} - {str(e)}")

    # 여기 도달하면 안 되지만, 안전을 위해
    if last_exception:
        raise last_exception


def retry_with_exponential_backoff(func, max_retries=None, progress_callback=None):
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
            config.ARTICLE_MODEL,
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

## 🔥 Viral Analysis (바이럴 가능성 평가)

각 플랫폼별 게시물이 글로벌 팬덤 사이에서 얼마나 바이럴될지 **1점부터 100점 사이의 점수(viral_score)**를 매기고, 구체적인 이유(viral_reason)를 **한 문장**으로 작성하세요.

**평가 기준:**
- **X (Twitter)**: 현재 트렌딩 해시태그와의 일치도, 리트윗 유도력, 훅의 강도, Gen Z 슬랭 활용도
- **Instagram**: 감성적 서사의 완성도, 이모지 배치의 시각적 효과, 해시태그 전략, 팬들의 공감 포인트
- **Threads**: 질문의 참여 유도력, 댓글 유발 가능성, 대화체의 자연스러움

**예시:**
- X (85점): "현재 X에서 유행하는 'main character energy' 슬랭을 활용하여 높은 리트윗 가능성"
- Instagram (92점): "3문단 완전 서사 구조와 감성적 질문이 팬들의 공감과 저장을 유도함"
- Threads (78점): "열린 질문 형식이 댓글 참여를 유도하지만 훅의 강도가 다소 약함"

## 📱 플랫폼별 상세 가이드라인

### 🐦 X (Twitter) - Punchy & Viral

**🚨 필수 요구사항: 클릭을 유발하는 강력한 훅(Hook)을 포함할 것! 🚨**

**English Version:**
- **길이**: 정확히 140-200자 사이 (엄수!)
- **구조**:
  - **첫 줄**: 가장 논란적이거나 충격적인 '한 줄' 훅 (예: "WAIT WHAT?!", "NOT THIS!", "I'M SCREAMING")
  - **두 번째 줄**: 핵심 내용 (Gen Z Slang 필수)
  - **마지막**: 해시태그
- **목표**: 즉각적인 클릭 유도, 대량 RT 유발
- **톤**: Gen Z Slang 적극 활용 (slay, iconic, ate, serving, no cap, it's giving, the way..., not me..., bestie, main character energy, fr fr, ngl, literally)
- **번역체 절대 금지**: 100% 네이티브 영어 (미국/영국 10대가 쓰는 말투)
- **해시태그**: 정확히 3-4개 (마지막에)
- **예시**: "WAIT- [Name] just DID THAT?! 😭 Not them absolutely SLAYING at [Event] and serving iconic behavior... the way I SCREAMED 💅 #KPop #[Name] #Viral"

**Korean Version:**
- **길이**: 정확히 140-200자 사이 (엄수!)
- **구조**:
  - **첫 줄**: 충격적인 훅 (예: "ㄹㅇ 실화?", "미쳤다...", "헐 대박", "이거 진짜??")
  - **두 번째 줄**: 핵심 내용 + 리액션
  - **마지막**: 해시태그
- **목표**: 즉각적인 클릭 유도, 대량 RT 유발
- **톤**: 국내 커뮤니티 화제성 폭발 스타일 (디시, 트위터, 인스타 댓글 톤)
- **리액션 필수 포함**: "ㄹㅇ", "실화?", "미쳤다", "ㅋㅋㅋ", "ㅠㅠ", "기절각" 등
- **해시태그**: 정확히 3-4개 (반드시 #{site_name} 첫 번째에 포함!)
- **예시**: "ㄹㅇ 미쳤다... [이름]이 [이벤트]에서 이 정도 폼은 실화임?? 🔥 팬들 다 기절각ㅋㅋㅋ 이게 바로 레전드 #{site_name} #[이름] #화제"

### 📸 Instagram - Long-form Storytelling

**🚨 필수 요구사항: 최소 3문단 이상의 완전한 서사(Narrative)를 작성할 것! 🚨**
**⚠️  분량 미달 시 재작성 필요! 각 문단은 최소 2-3문장 이상!**

**English Version:**
- **필수 길이**: **최소 3문단** (각 문단 2-3문장 이상, 총 8-10문장)
- **줄바꿈**: 각 문단 사이 반드시 빈 줄 삽입 (가독성 극대화)
- **구조 (엄격히 준수)**:
  - **1문단**: 감성적인 Hook + 이모지 (기사의 가장 감동적인 순간 포착)
  - **2문단**: 기사 속 **구체적 인용문** 또는 **구체적 숫자/기록** 활용한 스토리텔링 (예: "reached #1 in 50 countries", "10 million views in 24 hours")
  - **3문단**: 아티스트의 여정, 노력, 의미 등을 감동적으로 풀어쓰기
  - **4문단 (마무리)**: 감동적인 마무리 + 팬들에게 던지는 질문 + 이모지
- **톤**: Gen Z 감성 + 고급스러운 어휘 (casual하지만 sophisticated)
- **번역체 절대 금지**: 100% 네이티브 인플루언서 말투
- **해시태그**: 정확히 10개 (마지막 줄에 한 번에 배치)
- **이모지**: 각 문단마다 1-2개 전략적 배치
- **예시**:
  ```
  ✨ When [Artist] said "[actual quote from article]"... I felt that deep in my soul. 💫

  Their journey from [specific starting point with numbers] to [achievement with exact stats] is literally the definition of dedication and artistry. In just [timeframe], they've managed to [specific accomplishment], proving that talent and hard work truly pay off.

  What strikes me most is how they [specific quality/action from article] while staying true to themselves. That kind of authenticity is rare in this industry, and it's exactly why millions of people around the world connect with their music on such a personal level.

  This is what real artistry looks like. 👑 Which moment from their journey touched your heart the most? Drop a 💜 if you're proud!

  #KPop #[Artist] #TenAsia #Viral #Music #Inspiration #Icon #Goals #Legend #Masterpiece
  ```

**Korean Version:**
- **필수 길이**: **최소 3문단** (각 문단 2-3문장 이상, 총 8-10문장)
- **줄바꿈**: 각 문단 사이 반드시 빈 줄 삽입
- **구조 (엄격히 준수)**:
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
  "viral_analysis": {{
    "kr": {{
      "x": {{
        "score": 85,  // 1-100 바이럴 점수
        "reason": "현재 국내 트위터에서 유행하는 리액션 표현('ㄹㅇ', '미쳤다')을 활용하여 높은 RT 가능성"
      }},
      "insta": {{
        "score": 92,
        "reason": "3문단 완전 서사 구조와 구체적 수치가 팬들의 공감과 저장을 유도함"
      }},
      "threads": {{
        "score": 78,
        "reason": "열린 질문 형식이 댓글 참여를 유도하지만 훅의 강도가 다소 약함"
      }}
    }},
    "en": {{
      "x": {{
        "score": 88,
        "reason": "Uses trending Gen Z slang ('main character energy', 'no cap') for high RT potential"
      }},
      "insta": {{
        "score": 90,
        "reason": "Full 3-paragraph narrative with emotional hooks drives saves and shares"
      }},
      "threads": {{
        "score": 82,
        "reason": "Conversational question format encourages replies but could use stronger hook"
      }}
    }}
  }},
  "key_takeaway": {{
    "kr": "이 기사의 핵심 요약을 한 줄로 (예: '[아티스트]가 [성과]를 달성하며 새로운 역사를 썼다')",
    "en": "One-line key takeaway (e.g., '[Artist] makes history with [achievement]')"
  }}
}}

**중요**:
1. 각 게시물을 작성한 후, 완성도 체크포인트 3가지(팩트 정확성, 품격, 자연스러움)를 기준으로 1-10점의 review_score를 정직하게 매기세요.
2. 각 게시물의 바이럴 가능성을 1-100점으로 평가하고, 구체적인 이유를 한 문장으로 작성하세요.
"""

        # 진행 상황 표시
        yield {"platform": "all", "language": "all", "status": "generating", "content": None}

        # 재시도 진행 상황을 yield하기 위한 wrapper
        retry_attempts = []

        def progress_callback(attempt, max_retries, wait_time, error):
            retry_attempts.append({
                "attempt": attempt,
                "max_retries": max_retries,
                "wait_time": wait_time,
                "error": error
            })

        # 안전한 API 호출 (Exponential Backoff 포함)
        response = safe_generate_content(
            model,
            unified_prompt,
            max_retries=config.MAX_RETRIES,
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
        yield {
            "platform": "x",
            "language": "english",
            "status": "completed",
            "content": result["en"]["x"],
            "viral_score": result["viral_analysis"]["en"]["x"]["score"],
            "viral_reason": result["viral_analysis"]["en"]["x"]["reason"]
        }

        # X (Twitter) - Korean
        yield {"platform": "x", "language": "korean", "status": "generating", "content": None}
        yield {
            "platform": "x",
            "language": "korean",
            "status": "completed",
            "content": result["kr"]["x"],
            "viral_score": result["viral_analysis"]["kr"]["x"]["score"],
            "viral_reason": result["viral_analysis"]["kr"]["x"]["reason"]
        }

        # Instagram - English
        yield {"platform": "instagram", "language": "english", "status": "generating", "content": None}
        yield {
            "platform": "instagram",
            "language": "english",
            "status": "completed",
            "content": result["en"]["insta"],
            "viral_score": result["viral_analysis"]["en"]["insta"]["score"],
            "viral_reason": result["viral_analysis"]["en"]["insta"]["reason"]
        }

        # Instagram - Korean
        yield {"platform": "instagram", "language": "korean", "status": "generating", "content": None}
        yield {
            "platform": "instagram",
            "language": "korean",
            "status": "completed",
            "content": result["kr"]["insta"],
            "viral_score": result["viral_analysis"]["kr"]["insta"]["score"],
            "viral_reason": result["viral_analysis"]["kr"]["insta"]["reason"]
        }

        # Threads - English
        yield {"platform": "threads", "language": "english", "status": "generating", "content": None}
        yield {
            "platform": "threads",
            "language": "english",
            "status": "completed",
            "content": result["en"]["threads"],
            "viral_score": result["viral_analysis"]["en"]["threads"]["score"],
            "viral_reason": result["viral_analysis"]["en"]["threads"]["reason"]
        }

        # Threads - Korean
        yield {"platform": "threads", "language": "korean", "status": "generating", "content": None}
        yield {
            "platform": "threads",
            "language": "korean",
            "status": "completed",
            "content": result["kr"]["threads"],
            "viral_score": result["viral_analysis"]["kr"]["threads"]["score"],
            "viral_reason": result["viral_analysis"]["kr"]["threads"]["reason"]
        }

        # 최종 완료 신호
        yield {"platform": "all", "status": "completed", "model": config.ARTICLE_MODEL}

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
        model = genai.GenerativeModel(config.ARTICLE_MODEL)

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
            "model": config.ARTICLE_MODEL
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
