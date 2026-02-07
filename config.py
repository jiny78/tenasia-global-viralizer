"""
Global Viralizer 설정 파일

모델, API 설정, 재시도 정책 등을 중앙에서 관리합니다.
"""

# ========================================
# 모델 설정
# ========================================

# 텍스트 분석용 모델 (기사 내용 분석 및 SNS 게시물 생성)
# gemini-1.5-flash-latest는 v1beta API에서 안정적으로 지원됨
ARTICLE_MODEL = "gemini-1.5-flash-latest"

# 멀티모달 프레임 분석용 모델 (비디오 콘텐츠 분석)
# gemini-1.5-pro-latest는 멀티모달 분석에 더 강력함
VIDEO_MODEL = "gemini-1.5-pro-latest"


# ========================================
# API 설정
# ========================================

# API 호출 실패 시 재시도 횟수
MAX_RETRIES = 3

# API 타임아웃 (초)
API_TIMEOUT = 120

# 지수 백오프 기본 대기 시간 (초)
# 실제 대기 시간 = BASE_WAIT_TIME * (2 ** attempt)
BASE_WAIT_TIME = 2


# ========================================
# 비디오 처리 설정
# ========================================

# 비디오에서 추출할 프레임 수
MAX_FRAMES = 10

# 프레임 추출 간격 (초)
FRAME_INTERVAL = 5

# 최대 비디오 길이 (초)
MAX_VIDEO_LENGTH = 300


# ========================================
# SNS 플랫폼 설정
# ========================================

# 플랫폼별 문자 수 제한
PLATFORM_LIMITS = {
    "x": {
        "max_chars": 280,
        "recommended_min": 140,
        "recommended_max": 200
    },
    "instagram": {
        "max_chars": 2200,
        "recommended_min": 500,
        "min_paragraphs": 3,
        "hashtag_count": 10
    },
    "threads": {
        "max_chars": 500,
        "recommended_chars": 300,
        "min_chars": 200
    }
}


# ========================================
# 언어 설정
# ========================================

SUPPORTED_LANGUAGES = ["kr", "en"]

# 언어별 사이트명 매핑
SITE_NAME_MAPPING = {
    "텐아시아": {
        "kr": "텐아시아",
        "en": "TenAsia"
    },
    "한국경제": {
        "kr": "한국경제",
        "en": "hankyung"
    }
}


# ========================================
# 품질 검증 설정
# ========================================

# Self-Correction 체크포인트
QUALITY_CHECKPOINTS = [
    "팩트 체크: 기사 본문의 정보와 100% 일치하는가?",
    "품격 유지: 브랜드 이미지에 맞는 고급스러운 어휘를 사용했는가?",
    "자연스러운 현지화: 번역투가 아닌 현지 인플루언서의 말투인가?"
]

# 완성도 점수 범위
MIN_REVIEW_SCORE = 1
MAX_REVIEW_SCORE = 10


# ========================================
# 로깅 설정
# ========================================

# 로그 레벨
LOG_LEVEL = "INFO"

# 로그 포맷
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
