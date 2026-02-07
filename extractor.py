import requests
from typing import Dict, Optional
from urllib.parse import urlparse
import config


def get_site_name(url: str) -> str:
    """
    URL에서 사이트 이름을 추출합니다.

    Args:
        url: 기사 URL

    Returns:
        사이트 이름 (한글)
    """
    # 지원 언론사 도메인 매핑
    site_mapping = {
        "tenasia.co.kr": "텐아시아",
        "hankyung.com": "한국경제"
    }

    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        # www. 제거
        if domain.startswith("www."):
            domain = domain[4:]

        # 도메인 매핑에서 찾기
        for key, name in site_mapping.items():
            if key in domain:
                return name

        # 지원하지 않는 사이트
        return None

    except Exception:
        return None


def extract_article(url: str) -> Dict[str, Optional[str]]:
    """
    Jina Reader API를 사용하여 URL에서 기사 내용을 추출합니다.

    Args:
        url: 기사 URL

    Returns:
        제목, 본문, 사이트 이름을 담은 딕셔너리
        {
            "success": bool,
            "title": str or None,
            "content": str or None,
            "site_name": str or None,
            "error": str or None
        }
    """
    try:
        # URL에서 사이트 이름 추출
        site_name = get_site_name(url)

        # 지원하지 않는 사이트인 경우
        if site_name is None:
            return {
                "success": False,
                "title": None,
                "content": None,
                "site_name": None,
                "error": "지원하지 않는 언론사입니다. 현재 텐아시아와 한국경제만 지원합니다."
            }

        # Jina Reader API 사용
        jina_url = f"https://r.jina.ai/{url}"

        # 타임아웃 설정
        response = requests.get(jina_url, timeout=config.API_TIMEOUT)

        # 응답 확인
        if response.status_code != 200:
            return {
                "success": False,
                "title": None,
                "content": None,
                "site_name": site_name,
                "error": f"HTTP {response.status_code}: 기사를 가져올 수 없습니다."
            }

        # 텍스트 추출
        content = response.text.strip()

        # 최소 길이 체크
        if not content or len(content) < 50:
            return {
                "success": False,
                "title": None,
                "content": None,
                "site_name": site_name,
                "error": "추출된 내용이 너무 짧습니다. URL을 확인해주세요."
            }

        # 첫 번째 줄을 제목으로 사용 (# 제거)
        lines = content.split('\n', 1)
        title = lines[0].replace('#', '').strip() if lines else "제목 없음"

        # 전체 내용을 본문으로 반환 (제목 포함)
        return {
            "success": True,
            "title": title,
            "content": content,
            "site_name": site_name,
            "error": None
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "title": None,
            "content": None,
            "site_name": None,
            "error": "요청 시간이 초과되었습니다. 다시 시도해주세요."
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "title": None,
            "content": None,
            "site_name": None,
            "error": f"네트워크 오류: {str(e)}"
        }

    except Exception as e:
        return {
            "success": False,
            "title": None,
            "content": None,
            "site_name": None,
            "error": f"추출 중 오류 발생: {str(e)}"
        }


if __name__ == "__main__":
    # 테스트 코드
    test_url = "https://www.tenasia.co.kr/article/2026020679984"
    print("=" * 60)
    print("Jina Reader API 기사 추출 테스트")
    print("=" * 60)
    print(f"\nURL: {test_url}\n")
    print("추출 중...")

    result = extract_article(test_url)

    if result["success"]:
        print(f"\n[SUCCESS] 추출 성공!")
        print(f"\n제목: {result['title']}")
        print(f"\n본문 (처음 500자):\n{result['content'][:500]}...")
        print(f"\n전체 길이: {len(result['content'])}자")
    else:
        print(f"\n[ERROR] 오류: {result['error']}")
