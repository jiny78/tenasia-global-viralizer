import requests
from typing import Dict, Optional


def extract_article(url: str) -> Dict[str, Optional[str]]:
    """
    Jina Reader API를 사용하여 URL에서 기사 내용을 추출합니다.

    Args:
        url: 기사 URL

    Returns:
        제목과 본문을 담은 딕셔너리
        {
            "success": bool,
            "title": str or None,
            "content": str or None,
            "error": str or None
        }
    """
    try:
        # Jina Reader API 사용
        jina_url = f"https://r.jina.ai/{url}"

        # 타임아웃 설정 (60초)
        response = requests.get(jina_url, timeout=60)

        # 응답 확인
        if response.status_code != 200:
            return {
                "success": False,
                "title": None,
                "content": None,
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
            "error": None
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "title": None,
            "content": None,
            "error": "요청 시간이 초과되었습니다. 다시 시도해주세요."
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "title": None,
            "content": None,
            "error": f"네트워크 오류: {str(e)}"
        }

    except Exception as e:
        return {
            "success": False,
            "title": None,
            "content": None,
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
