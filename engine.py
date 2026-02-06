import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def generate_sns_posts_streaming(article_text: str, article_title: str = ""):
    """
    한국어 기사를 받아 English와 Korean 버전의 SNS 게시물을 스트리밍 방식으로 생성합니다.
    각 플랫폼이 완료될 때마다 yield로 반환합니다.

    Args:
        article_text: 한국어 기사 내용
        article_title: 한국어 기사 제목 (선택)

    Yields:
        각 플랫폼/언어별 결과를 담은 딕셔너리
        {"platform": "x", "language": "english", "status": "completed", "content": "..."}
    """
    try:
        # Gemini 모델 초기화
        model = genai.GenerativeModel('gemini-2.5-flash')

        # English 페르소나
        english_instruction = """당신은 K-엔터 전문 글로벌 에디터입니다.
기사의 팩트를 유지하되, 글로벌 팬들이 클릭하고 싶게 만드는 최신 유행어(Gen Z Slang)와 감각적인 표현을 사용하세요.
번역체 느낌을 완전히 지워야 합니다. 자연스러운 네이티브 영어로 작성하세요.

Gen Z Slang 예시: slay, iconic, ate, serving, no cap, it's giving, the way..., not me..., bestie, main character energy 등"""

        # Korean 페르소나
        korean_instruction = """당신은 대한민국 최고의 연예 매체 텐아시아의 베테랑 SNS 에디터입니다.
국내 커뮤니티에서 화제가 될 법한 유머러스하거나 핵심을 찌르는 문구로 팬들의 공감을 이끌어내세요.
기사의 팩트를 유지하되, SNS에 최적화된 친근하고 감각적인 한국어 표현을 사용하세요."""

        article_info = f"""
기사 제목: {article_title}

기사 내용:
{article_text}
"""

        # X (Twitter) - English
        yield {"platform": "x", "language": "english", "status": "generating", "content": None}

        x_english_prompt = f"""{english_instruction}

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

        x_english_response = model.generate_content(x_english_prompt
        )

        yield {"platform": "x", "language": "english", "status": "completed", "content": x_english_response.text.strip()}

        # X (Twitter) - Korean
        yield {"platform": "x", "language": "korean", "status": "generating", "content": None}

        x_korean_prompt = f"""{korean_instruction}

{article_info}

위 기사를 바탕으로 X(트위터)용 한국어 게시물을 작성하세요.

중요 규칙:
- **속보 느낌의 긴박함** 또는 **팬들의 공감을 사는 친근한 말투** (~함, ~임)
- 2-3문장 이내로 짧고 강렬하게
- 국내 커뮤니티에서 화제가 될 법한 Hook으로 시작
- 적절한 '짤' 설명 포함 (예: "이 표정 실화냐", "미쳤다 진짜")
- 해시태그 3-4개만 (마지막에)

예시 톤: "ㄹㅇ 미쳤다... [이름]이 [이벤트]에서 보여준 이 모습 실화임? 🔥 팬들 다 기절각ㅋㅋㅋ #텐아시아 #[이름] #화제"

게시물만 작성 (설명 없이):"""

        x_korean_response = model.generate_content(x_korean_prompt
        )

        yield {"platform": "x", "language": "korean", "status": "completed", "content": x_korean_response.text.strip()}

        # Instagram - English
        yield {"platform": "instagram", "language": "english", "status": "generating", "content": None}

        instagram_english_prompt = f"""{english_instruction}

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

        instagram_english_response = model.generate_content(instagram_english_prompt
        )

        yield {"platform": "instagram", "language": "english", "status": "completed", "content": instagram_english_response.text.strip()}

        # Instagram - Korean
        yield {"platform": "instagram", "language": "korean", "status": "generating", "content": None}

        instagram_korean_prompt = f"""{korean_instruction}

{article_info}

위 기사를 바탕으로 Instagram용 한국어 게시물을 작성하세요.

중요 규칙:
- **감성적인 문구**로 팬들의 공감 유도
- 4-5문장으로 간결하지만 감동적으로
- 이모지 5-6개 전략적으로 배치
- 반드시 **#텐아시아 #TenAsia** 포함
- 마지막 줄에 해시태그 5-7개 (한국어/영어 혼용 가능)

예시 구조:
[감성적인 Hook + 이모지]
[본문 2-3문장 - 팬들이 공감할 수 있는 내용]
[마무리 문장 + 이모지]

[해시태그: #텐아시아 #TenAsia #[관련태그] #[관련태그] #[관련태그]]

게시물만 작성:"""

        instagram_korean_response = model.generate_content(instagram_korean_prompt
        )

        yield {"platform": "instagram", "language": "korean", "status": "completed", "content": instagram_korean_response.text.strip()}

        # Threads - English
        yield {"platform": "threads", "language": "english", "status": "generating", "content": None}

        threads_english_prompt = f"""{english_instruction}

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

        threads_english_response = model.generate_content(threads_english_prompt
        )

        yield {"platform": "threads", "language": "english", "status": "completed", "content": threads_english_response.text.strip()}

        # Threads - Korean
        yield {"platform": "threads", "language": "korean", "status": "generating", "content": None}

        threads_korean_prompt = f"""{korean_instruction}

{article_info}

위 기사를 바탕으로 Threads용 한국어 게시물을 작성하세요.

중요 규칙:
- **유저들과 소통할 수 있는 반말/존댓말 섞인 질문형 문구**
- 3-4문장으로 짧고 친근하게
- 마지막은 반드시 질문으로 끝내기 (댓글 유도)
- 해시태그 2-3개만 (자연스럽게 중간에)
- 친구와 대화하듯 편안한 톤

예시 톤: "와 근데 진짜 [주제] 이거 실화임?? 👀 [내용] 이 정도면 ㄹㅇ 레전드 아니냐ㅋㅋㅋ 너네 생각은 어때? #텐아시아 #[관련태그]"

게시물만 작성:"""

        threads_korean_response = model.generate_content(threads_korean_prompt
        )

        yield {"platform": "threads", "language": "korean", "status": "completed", "content": threads_korean_response.text.strip()}

        # 최종 완료 신호
        yield {"platform": "all", "status": "completed", "model": "gemini-2.5-flash"}

    except Exception as e:
        yield {"platform": "error", "status": "error", "error": str(e)}


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
