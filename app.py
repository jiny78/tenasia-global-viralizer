import streamlit as st
import streamlit.components.v1 as components
from engine import generate_article_posts, generate_video_posts
from extractor import extract_article
from youtube_processor import extract_frames_from_youtube, get_youtube_metadata

# 페이지 설정
st.set_page_config(
    page_title="Tenasia Global Viralizer",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 클립보드 복사 함수
def copy_to_clipboard(text, button_key):
    """JavaScript를 사용해 클립보드에 텍스트 복사"""
    # HTML과 JavaScript를 사용해 클립보드에 복사
    copy_js = f"""
    <script>
    function copyToClipboard_{button_key}() {{{{
        const text = {repr(text)};
        navigator.clipboard.writeText(text).then(function() {{{{
            console.log('Copied to clipboard successfully!');
        }}}}, function(err) {{{{
            console.error('Could not copy text: ', err);
        }}}});
    }}}}
    copyToClipboard_{button_key}();
    </script>
    """
    components.html(copy_js, height=0)

def get_viral_color(score):
    """바이럴 점수에 따른 색상 반환"""
    if score >= 80:
        return "#00C853"  # 녹색
    elif score >= 60:
        return "#64DD17"  # 연두색
    elif score >= 40:
        return "#FFD600"  # 노란색
    else:
        return "#FF6D00"  # 주황색

def display_viral_score(score, reason, language="korean"):
    """바이럴 점수와 이유를 시각적으로 표시"""
    color = get_viral_color(score)

    # 점수 표시 (진행 바 + 숫자)
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(score / 100)
    with col2:
        st.markdown(f"<div style='text-align: right; font-size: 1.2em; font-weight: bold; color: {color};'>{score}점</div>", unsafe_allow_html=True)

    # 이유 표시 (접을 수 있는 형태)
    with st.expander("📊 바이럴 분석 근거"):
        st.caption(reason)

def get_top_viral_pick(viral_scores, language):
    """해당 언어에서 가장 높은 바이럴 점수를 가진 플랫폼 반환"""
    max_score = 0
    top_platform = None

    for platform in ["x", "instagram", "threads"]:
        score = viral_scores.get(platform, {}).get(language, 0)
        if score > max_score:
            max_score = score
            top_platform = platform

    return top_platform, max_score

# 모바일 최적화 CSS
st.markdown("""
<style>
    /* 모바일 최적화 */
    @media (max-width: 768px) {
        .stApp {
            padding: 1rem 0.5rem;
        }

        /* 입력 영역 풀 너비 */
        .stTextInput, .stTextArea {
            width: 100% !important;
        }

        /* 버튼 풀 너비 */
        .stButton button {
            width: 100% !important;
            margin-bottom: 0.5rem;
        }

        /* 탭 텍스트 크기 조정 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            font-size: 0.9rem;
            padding: 0.5rem 0.75rem;
        }

        /* 텍스트 영역 높이 조정 */
        .stTextArea textarea {
            min-height: 150px !important;
        }

        /* 컬럼 간격 줄이기 */
        .row-widget.stHorizontal {
            gap: 0.5rem;
        }
    }

    /* 데스크톱 최적화 */
    @media (min-width: 769px) {
        .stTextArea textarea {
            min-height: 300px !important;
        }
    }

    /* 공통 스타일 */
    .stCode {
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    .element-container {
        margin-bottom: 0.5rem;
    }

    /* 타이틀 반응형 */
    h1 {
        font-size: clamp(1.5rem, 5vw, 2.5rem);
    }

    h2, h3 {
        font-size: clamp(1.2rem, 3vw, 1.8rem);
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'article_title' not in st.session_state:
    st.session_state.article_title = ""
if 'article_content' not in st.session_state:
    st.session_state.article_content = ""
if 'site_name' not in st.session_state:
    st.session_state.site_name = "해당 매체"
if 'auto_generate' not in st.session_state:
    st.session_state.auto_generate = False
if 'generation_count' not in st.session_state:
    st.session_state.generation_count = 0
if 'is_mobile' not in st.session_state:
    st.session_state.is_mobile = False
if 'generated_posts' not in st.session_state:
    st.session_state.generated_posts = None
if 'generation_status' not in st.session_state:
    st.session_state.generation_status = {
        "x": {"english": "pending", "korean": "pending"},
        "instagram": {"english": "pending", "korean": "pending"},
        "threads": {"english": "pending", "korean": "pending"}
    }
if 'youtube_frames' not in st.session_state:
    st.session_state.youtube_frames = None
if 'youtube_video_path' not in st.session_state:
    st.session_state.youtube_video_path = None

# 타이틀
st.title("🌐 Global Viralizer")
st.markdown("K-엔터 기사를 글로벌 바이럴 SNS 콘텐츠로 변환하세요 (텐아시아 · 한국경제)")

# 사이드바에 정보 표시
with st.sidebar:
    st.header("ℹ️ 사용 방법")

    # 모바일/데스크톱 안내
    st.info("📱 모바일에서도 완벽하게 작동합니다!")

    st.markdown("""
    **방법 1: 기사 URL 입력** 📰
    1. 텐아시아/한국경제 기사 URL 입력
    2. 'Extract Article' 버튼 클릭
    3. 자동으로 출처 인식 및 게시물 생성

    **방법 2: 유튜브 쇼츠 URL** 🎬
    1. 유튜브 쇼츠 URL 입력
    2. 'Extract Frames' 버튼 클릭
    3. 영상 프레임 분석하여 게시물 생성

    **방법 3: 직접 입력** ✍️
    1. 기사 내용 직접 붙여넣기
    2. 'Generate' 버튼 클릭

    **결과 확인** 🎉
    - 🌐 English / 🇰🇷 Korean 탭 전환
    - 📋 바이럴 점수 & 근거 확인
    - X, Instagram, Threads 각 6개 생성

    **지원 언론사** 📰
    - 📰 **텐아시아** (tenasia.co.kr)
    - 💼 **한국경제** (hankyung.com)
    """)

    st.divider()

    # 버전 정보
    st.caption("🤖 Powered by Google Gemini 2.5 Flash")
    st.caption("📱 Responsive Design for All Devices")

# 디바이스 감지 (JavaScript)
st.markdown("""
<script>
    const isMobile = window.innerWidth <= 768;
    window.parent.postMessage({type: 'streamlit:setComponentValue', value: isMobile}, '*');
</script>
""", unsafe_allow_html=True)

# 메인 컨텐츠 - 반응형 레이아웃
# 모바일: 세로 배치, 데스크톱: 가로 배치
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📰 콘텐츠 입력")

    # 방법 1: 기사 URL 입력
    st.markdown("##### 방법 1: 기사 URL 자동 추출")
    article_url = st.text_input(
        "기사 URL",
        placeholder="https://www.tenasia.co.kr/article/... 또는 https://www.hankyung.com/...",
        help="텐아시아 또는 한국경제 기사 URL을 입력하면 자동으로 출처와 내용을 추출합니다"
    )

    extract_article_button = st.button("📰 Extract Article", type="secondary", use_container_width=True, key="extract_article_btn")

    st.divider()

    # 방법 2: 유튜브 쇼츠 URL 입력
    st.markdown("##### 방법 2: 유튜브 쇼츠 프레임 분석")
    youtube_url = st.text_input(
        "유튜브 쇼츠 URL",
        placeholder="https://www.youtube.com/watch?v=... (일반 영상 추천)",
        help="유튜브 URL을 입력하면 영상 프레임을 분석하여 게시물을 생성합니다. 일반 영상이 더 안정적입니다."
    )
    st.caption("💡 테스트용 샘플: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`")

    extract_youtube_button = st.button("🎬 Extract Frames", type="secondary", use_container_width=True, key="extract_youtube_btn")

    st.divider()

    # 방법 3: 직접 입력
    st.markdown("##### 방법 3: 직접 입력")

    # 세션 상태와 연결된 입력 필드
    article_title = st.text_input(
        "기사 제목 (선택)",
        value=st.session_state.article_title,
        placeholder="기사 제목을 입력하세요 (선택사항)",
        key="title_input"
    )

    article_content = st.text_area(
        "한국어 기사 내용",
        value=st.session_state.article_content,
        height=200,
        placeholder="여기에 한국어 기사 내용을 붙여넣으세요...",
        key="content_input"
    )

    # 분량 모드 선택
    st.divider()
    tone_mode = st.radio(
        "📏 분량 모드",
        options=["rich", "compact"],
        format_func=lambda x: "📚 Rich (풍부하고 상세)" if x == "rich" else "⚡ Compact (간결하고 임팩트)",
        horizontal=True,
        help="Rich: Instagram 최소 3문단, Threads 300자 / Compact: Instagram 최소 2문단, Threads 200-250자"
    )

    generate_button = st.button("🚀 Generate SNS Posts", type="primary", use_container_width=True)

with col2:
    st.subheader("✨ 생성 결과")

# 방법 1: Extract Article 버튼 클릭 시
if extract_article_button:
    if not article_url.strip():
        with col1:
            st.error("기사 URL을 입력해주세요!")
    else:
        # 오른쪽 결과 영역에 진행 상황 표시
        with col2:
            status_container = st.container()
            with status_container:
                st.info("🔍 기사를 추출하는 중...")

        result = extract_article(article_url)

        if result["success"]:
            with col1:
                st.success(f"✅ 기사 추출 완료!")
                st.info(f"**출처:** {result['site_name']}")
                st.info(f"**제목:** {result['title'][:100]}...")

            # 세션 상태 업데이트
            st.session_state.article_title = result['title']
            st.session_state.article_content = result['content']
            st.session_state.site_name = result['site_name']
            st.session_state.auto_generate = True  # 자동 생성 플래그 설정

            # 페이지 새로고침
            st.rerun()
        else:
            with col1:
                st.error(f"❌ 추출 실패: {result['error']}")
            with col2:
                st.error(f"❌ 추출 실패: {result['error']}")

# 방법 2: Extract YouTube Frames 버튼 클릭 시
if extract_youtube_button:
    if not youtube_url.strip():
        with col1:
            st.error("유튜브 URL을 입력해주세요!")
    else:
        # 오른쪽 결과 영역에 진행 상황 표시
        with col2:
            status_container = st.container()
            with status_container:
                progress_info = st.info("🎬 유튜브 영상 분석 중...")
                progress_details = st.empty()

        try:
            # 메타데이터 추출
            progress_details.text("📊 영상 정보 가져오는 중...")
            metadata = get_youtube_metadata(youtube_url)

            with col1:
                st.info(f"**제목:** {metadata['title'][:100]}...")
                st.info(f"**길이:** {metadata['duration']}초")

            # 프레임 추출 (미리보기용 + Gemini 분석용 비디오 파일)
            progress_details.text("🎞️ 프레임 추출 및 영상 다운로드 중...")
            frames, video_path = extract_frames_from_youtube(youtube_url, num_frames=10)

            with col1:
                st.success(f"✅ {len(frames)}개 프레임 추출 완료!")

                # 추출된 프레임 미리보기
                st.markdown("---")
                st.markdown("### 📸 추출된 프레임 미리보기")
                st.caption("AI 분석에 사용될 프레임들입니다")

                # 프레임을 그리드로 표시 (3개씩)
                if len(frames) > 0:
                    # 3개씩 끊어서 표시
                    for row_start in range(0, len(frames), 3):
                        cols = st.columns(3)
                        for col_idx, frame_idx in enumerate(range(row_start, min(row_start + 3, len(frames)))):
                            with cols[col_idx]:
                                st.image(
                                    frames[frame_idx],
                                    caption=f"프레임 {frame_idx + 1}/{len(frames)}",
                                    use_container_width=True
                                )

            # 프레임을 engine.py로 전달하여 멀티모달 분석
            youtube_content = f"""
제목: {metadata['title']}

설명:
{metadata.get('description', '설명 없음')[:500]}

영상 길이: {metadata['duration']}초
조회수: {metadata.get('view_count', 0):,}회
업로더: {metadata.get('uploader', '알 수 없음')}
"""

            # 세션 상태 업데이트
            st.session_state.article_title = metadata['title']
            st.session_state.article_content = youtube_content
            st.session_state.site_name = "YouTube"
            st.session_state.youtube_frames = frames  # 프레임 저장 (미리보기용)
            st.session_state.youtube_video_path = video_path  # 비디오 파일 경로 (Gemini 분석용)
            st.session_state.auto_generate = True  # 자동 생성 플래그 설정

            with col2:
                st.success("✅ 유튜브 영상 분석 완료! SNS 게시물 생성 중...")

            # 페이지 새로고침
            st.rerun()

        except Exception as e:
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()

            with col1:
                st.error(f"❌ 유튜브 처리 실패")

                # 에러 메시지 표시
                st.warning("**에러 상세:**")
                st.code(error_msg)

                # 구체적인 해결 방법
                if "비디오 스트림을 열 수 없습니다" in error_msg:
                    st.info("""
                    **해결 방법:**
                    1. 일반 YouTube 영상 URL 사용 (Shorts 대신)
                    2. 영상이 공개 상태인지 확인
                    3. 짧은 영상 시도 (30초~2분)
                    4. 잠시 후 다시 시도
                    """)
                elif "영상을 사용할 수 없습니다" in error_msg or "Video unavailable" in error_msg:
                    st.info("""
                    **이 영상은 사용할 수 없습니다:**
                    - 영상이 삭제되었거나 비공개일 수 있습니다
                    - 다른 공개 영상을 시도해주세요
                    """)
                elif "연령 제한" in error_msg:
                    st.info("""
                    **연령 제한 영상:**
                    - 연령 제한이 없는 영상을 사용해주세요
                    """)
                elif "지역 제한" in error_msg or "not available" in error_msg:
                    st.info("""
                    **지역 제한 또는 저작권 문제:**
                    - 다른 영상을 시도해주세요
                    """)
                else:
                    st.info("""
                    **일반적인 해결 방법:**
                    1. 테스트용 샘플 URL 시도
                    2. 방법 3: 직접 입력 사용
                    3. yt-dlp 업데이트
                    """)

                # 디버그 정보
                with st.expander("🔍 디버그 정보 (개발자용)"):
                    st.code(error_trace)

                # 추가 도움말
                with st.expander("💡 추가 도움말"):
                    st.markdown("""
                    **yt-dlp 업데이트:**
                    ```bash
                    pip install --upgrade yt-dlp
                    ```

                    **OpenCV 재설치:**
                    ```bash
                    pip install --upgrade opencv-python-headless
                    ```

                    **또는 방법 3 사용:**
                    영상 내용을 직접 입력하여 SNS 게시물 생성
                    """)

            with col2:
                st.error(f"❌ 유튜브 처리 실패")
                st.info("왼쪽 패널에서 에러 상세와 해결 방법을 확인하세요")

# Generate 버튼 클릭 시 또는 자동 생성 플래그가 설정된 경우
should_generate = generate_button or st.session_state.auto_generate

# 자동 생성의 경우 세션 상태에서 직접 값 가져오기
if st.session_state.auto_generate:
    st.session_state.auto_generate = False
    content_to_use = st.session_state.article_content
    title_to_use = st.session_state.article_title
    site_name_to_use = st.session_state.site_name
else:
    # 수동 생성의 경우 입력 필드 값 사용
    content_to_use = article_content
    title_to_use = article_title
    site_name_to_use = st.session_state.get('site_name', '해당 매체')

# 생성 실행
if should_generate and content_to_use.strip():
    # 생성 시작 - 세션 상태 초기화
    st.session_state.generated_posts = {
        "x": {"english": None, "korean": None},
        "instagram": {"english": None, "korean": None},
        "threads": {"english": None, "korean": None}
    }
    st.session_state.viral_scores = {
        "x": {"english": 0, "korean": 0},
        "instagram": {"english": 0, "korean": 0},
        "threads": {"english": 0, "korean": 0}
    }
    st.session_state.viral_reasons = {
        "x": {"english": "", "korean": ""},
        "instagram": {"english": "", "korean": ""},
        "threads": {"english": "", "korean": ""}
    }
    st.session_state.generation_count += 1

    with col2:
        gen_id = st.session_state.generation_count

        # 진행 상태 표시
        status_container = st.status("🤖 AI 기사 분석 및 SNS 게시물 생성 중...", expanded=True)

        with status_container:
            # 진행 바 및 상태 표시
            progress_bar = st.progress(0)
            progress_text = st.empty()
            retry_info = st.empty()

            st.write("**📊 생성 진행 상황:**")
            status_x = st.empty()
            status_instagram = st.empty()
            status_threads = st.empty()

            status_x.text("🐦 X (Twitter): ⏳ 대기 중...")
            status_instagram.text("📸 Instagram: ⏳ 대기 중...")
            status_threads.text("🧵 Threads: ⏳ 대기 중...")

        # 결과 표시 영역
        result_container = st.container()
        model_info = st.empty()

        try:
            # 영상 모드인지 기사 모드인지 판별
            video_path = st.session_state.get('youtube_video_path', None)
            is_video_mode = video_path is not None

            with status_container:
                progress_bar.progress(10)
                progress_text.text("🤖 AI 모델 초기화 중...")

                # 모드별 함수 호출 (관심사 분리)
                if is_video_mode:
                    progress_text.text("🎬 영상 전체 분석 중... (시간이 걸릴 수 있습니다)")
                    result = generate_video_posts(
                        video_path=video_path,
                        video_metadata=content_to_use,
                        video_title=title_to_use,
                        site_name=site_name_to_use,
                        tone_mode=tone_mode
                    )
                else:
                    progress_text.text("📝 기사 분석 및 SNS 게시물 생성 중...")
                    result = generate_article_posts(
                        article_text=content_to_use,
                        article_title=title_to_use,
                        site_name=site_name_to_use,
                        tone_mode=tone_mode
                    )

                progress_bar.progress(100)
                progress_text.text("✅ 생성 완료!")
                status_x.text("🐦 X (Twitter): ✅ 완료")
                status_instagram.text("📸 Instagram: ✅ 완료")
                status_threads.text("🧵 Threads: ✅ 완료")

            status_container.update(label="✅ 생성 완료!", state="complete", expanded=False)

            # 결과 저장 (JSON 형식에서 session_state로)
            st.session_state.generated_posts["x"]["english"] = result["en"]["x"]
            st.session_state.generated_posts["x"]["korean"] = result["kr"]["x"]
            st.session_state.generated_posts["instagram"]["english"] = result["en"]["insta"]
            st.session_state.generated_posts["instagram"]["korean"] = result["kr"]["insta"]
            st.session_state.generated_posts["threads"]["english"] = result["en"]["threads"]
            st.session_state.generated_posts["threads"]["korean"] = result["kr"]["threads"]

            # 바이럴 점수 저장
            st.session_state.viral_scores["x"]["english"] = result["viral_analysis"]["en"]["x"]["score"]
            st.session_state.viral_scores["x"]["korean"] = result["viral_analysis"]["kr"]["x"]["score"]
            st.session_state.viral_scores["instagram"]["english"] = result["viral_analysis"]["en"]["insta"]["score"]
            st.session_state.viral_scores["instagram"]["korean"] = result["viral_analysis"]["kr"]["insta"]["score"]
            st.session_state.viral_scores["threads"]["english"] = result["viral_analysis"]["en"]["threads"]["score"]
            st.session_state.viral_scores["threads"]["korean"] = result["viral_analysis"]["kr"]["threads"]["score"]

            # 바이럴 이유 저장
            st.session_state.viral_reasons["x"]["english"] = result["viral_analysis"]["en"]["x"]["reason"]
            st.session_state.viral_reasons["x"]["korean"] = result["viral_analysis"]["kr"]["x"]["reason"]
            st.session_state.viral_reasons["instagram"]["english"] = result["viral_analysis"]["en"]["insta"]["reason"]
            st.session_state.viral_reasons["instagram"]["korean"] = result["viral_analysis"]["kr"]["insta"]["reason"]
            st.session_state.viral_reasons["threads"]["english"] = result["viral_analysis"]["en"]["threads"]["reason"]
            st.session_state.viral_reasons["threads"]["korean"] = result["viral_analysis"]["kr"]["threads"]["reason"]

            # 모델 정보 표시
            model_used = "gemini-1.5-flash" if is_video_mode else "gemini-2.0-flash"
            model_info.caption(f"🤖 Generated by: {model_used} ({tone_mode.upper()} mode)")

        except Exception as e:
            status_container.update(label="❌ 생성 실패", state="error", expanded=True)
            with status_container:
                st.error(f"**오류 발생:**\n\n{str(e)}")

            # 더미 에러 처리 블록 (기존 로직 호환)
            for update in [{"platform": "error"}]:
                platform = update.get("platform")
                if platform == "error":
                    status_container.update(label="❌ 생성 실패", state="error", expanded=True)
                    with status_container:
                        st.error(f"**오류 발생:**\n\n{update.get('error', '알 수 없는 오류')}")

        # 결과 표시
        with result_container:
                st.divider()
                st.markdown("## 📝 생성된 SNS 게시물")

                # X (Twitter)
                if st.session_state.generated_posts["x"]["english"] or st.session_state.generated_posts["x"]["korean"]:
                    st.markdown("### 🐦 X (Twitter)")
                    st.info("💡 화제될 문장으로 시작 + 스레드 유도")

                    tab_x_kr, tab_x_en = st.tabs(["🇰🇷 Korean", "🇺🇸 English"])

                    # 최고 바이럴 픽 찾기
                    top_kr_platform, top_kr_score = get_top_viral_pick(st.session_state.viral_scores, "korean")
                    top_en_platform, top_en_score = get_top_viral_pick(st.session_state.viral_scores, "english")

                    with tab_x_kr:
                        if st.session_state.generated_posts["x"]["korean"]:
                            # Editor's Choice 배지 (최고 점수인 경우)
                            if top_kr_platform == "x":
                                st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                            # 바이럴 점수 표시
                            st.markdown("**📈 예상 바이럴 점수**")
                            display_viral_score(
                                st.session_state.viral_scores["x"]["korean"],
                                st.session_state.viral_reasons["x"]["korean"],
                                "korean"
                            )

                            st.text_area(
                                "Korean Version",
                                value=st.session_state.generated_posts["x"]["korean"],
                                height=150,
                                key=f"x_korean_textarea_{gen_id}",
                                label_visibility="collapsed",
                                disabled=True
                            )
                            st.code(st.session_state.generated_posts["x"]["korean"], language=None)

                            # 추천 배지
                            st.markdown("**🔥 이 카피 추천!** - 국내 커뮤니티 화제성 최적화")

                            if st.button("📋 Copy", key=f"x_korean_copy_{gen_id}", use_container_width=True):
                                copy_to_clipboard(st.session_state.generated_posts["x"]["korean"], f"x_korean_copy_{gen_id}")
                                st.success("✅ 복사 완료!")

                    with tab_x_en:
                        if st.session_state.generated_posts["x"]["english"]:
                            # Editor's Choice 배지 (최고 점수인 경우)
                            if top_en_platform == "x":
                                st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                            # 바이럴 점수 표시
                            st.markdown("**📈 예상 바이럴 점수**")
                            display_viral_score(
                                st.session_state.viral_scores["x"]["english"],
                                st.session_state.viral_reasons["x"]["english"],
                                "english"
                            )

                            st.text_area(
                                "English Version",
                                value=st.session_state.generated_posts["x"]["english"],
                                height=150,
                                key=f"x_english_textarea_{gen_id}",
                                label_visibility="collapsed",
                                disabled=True
                            )
                            st.code(st.session_state.generated_posts["x"]["english"], language=None)

                            # 추천 배지
                            st.markdown("**💫 글로벌 팬 추천!** - Gen Z Slang & 바이럴 최적화")

                            if st.button("📋 Copy", key=f"x_english_copy_{gen_id}", use_container_width=True):
                                copy_to_clipboard(st.session_state.generated_posts["x"]["english"], f"x_english_copy_{gen_id}")
                                st.success("✅ 복사 완료!")

                    st.divider()

                # Instagram
                if st.session_state.generated_posts["instagram"]["english"] or st.session_state.generated_posts["instagram"]["korean"]:
                    st.markdown("### 📸 Instagram")
                    st.info("💡 이모지 배치 + 비주얼 중심 감성 문구")

                    tab_ig_kr, tab_ig_en = st.tabs(["🇰🇷 Korean", "🇺🇸 English"])

                    with tab_ig_kr:
                        if st.session_state.generated_posts["instagram"]["korean"]:
                            # Editor's Choice 배지 (최고 점수인 경우)
                            if top_kr_platform == "instagram":
                                st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                            # 바이럴 점수 표시
                            st.markdown("**📈 예상 바이럴 점수**")
                            display_viral_score(
                                st.session_state.viral_scores["instagram"]["korean"],
                                st.session_state.viral_reasons["instagram"]["korean"],
                                "korean"
                            )

                            st.text_area(
                                "Korean Version",
                                value=st.session_state.generated_posts["instagram"]["korean"],
                                height=300,
                                key=f"instagram_korean_textarea_{gen_id}",
                                label_visibility="collapsed",
                                disabled=True
                            )
                            st.code(st.session_state.generated_posts["instagram"]["korean"], language=None)

                            # 추천 배지
                            st.markdown("**✨ 감성 스토리 추천!** - 3문단 완전 서사 & 공감 포인트")

                            if st.button("📋 Copy", key=f"instagram_korean_copy_{gen_id}", use_container_width=True):
                                copy_to_clipboard(st.session_state.generated_posts["instagram"]["korean"], f"instagram_korean_copy_{gen_id}")
                                st.success("✅ 복사 완료!")

                    with tab_ig_en:
                        if st.session_state.generated_posts["instagram"]["english"]:
                            # Editor's Choice 배지 (최고 점수인 경우)
                            if top_en_platform == "instagram":
                                st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                            # 바이럴 점수 표시
                            st.markdown("**📈 예상 바이럴 점수**")
                            display_viral_score(
                                st.session_state.viral_scores["instagram"]["english"],
                                st.session_state.viral_reasons["instagram"]["english"],
                                "english"
                            )

                            st.text_area(
                                "English Version",
                                value=st.session_state.generated_posts["instagram"]["english"],
                                height=300,
                                key=f"instagram_english_textarea_{gen_id}",
                                label_visibility="collapsed",
                                disabled=True
                            )
                            st.code(st.session_state.generated_posts["instagram"]["english"], language=None)

                            # 추천 배지
                            st.markdown("**🌟 Global Story Pick!** - Full 3-para narrative & relatability")

                            if st.button("📋 Copy", key=f"instagram_english_copy_{gen_id}", use_container_width=True):
                                copy_to_clipboard(st.session_state.generated_posts["instagram"]["english"], f"instagram_english_copy_{gen_id}")
                                st.success("✅ 복사 완료!")

                    st.divider()

                # Threads
                if st.session_state.generated_posts["threads"]["english"] or st.session_state.generated_posts["threads"]["korean"]:
                    st.markdown("### 🧵 Threads")
                    st.info("💡 유저 참여형 질문 중심")

                    tab_th_kr, tab_th_en = st.tabs(["🇰🇷 Korean", "🇺🇸 English"])

                    with tab_th_kr:
                        if st.session_state.generated_posts["threads"]["korean"]:
                            # Editor's Choice 배지 (최고 점수인 경우)
                            if top_kr_platform == "threads":
                                st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                            # 바이럴 점수 표시
                            st.markdown("**📈 예상 바이럴 점수**")
                            display_viral_score(
                                st.session_state.viral_scores["threads"]["korean"],
                                st.session_state.viral_reasons["threads"]["korean"],
                                "korean"
                            )

                            st.text_area(
                                "Korean Version",
                                value=st.session_state.generated_posts["threads"]["korean"],
                                height=300,
                                key=f"threads_korean_textarea_{gen_id}",
                                label_visibility="collapsed",
                                disabled=True
                            )
                            st.code(st.session_state.generated_posts["threads"]["korean"], language=None)

                            # 추천 배지
                            st.markdown("**💬 팬 참여 추천!** - 질문형 구조로 댓글 폭발 유도")

                            if st.button("📋 Copy", key=f"threads_korean_copy_{gen_id}", use_container_width=True):
                                copy_to_clipboard(st.session_state.generated_posts["threads"]["korean"], f"threads_korean_copy_{gen_id}")
                                st.success("✅ 복사 완료!")

                    with tab_th_en:
                        if st.session_state.generated_posts["threads"]["english"]:
                            # Editor's Choice 배지 (최고 점수인 경우)
                            if top_en_platform == "threads":
                                st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                            # 바이럴 점수 표시
                            st.markdown("**📈 예상 바이럴 점수**")
                            display_viral_score(
                                st.session_state.viral_scores["threads"]["english"],
                                st.session_state.viral_reasons["threads"]["english"],
                                "english"
                            )

                            st.text_area(
                                "English Version",
                                value=st.session_state.generated_posts["threads"]["english"],
                                height=300,
                                key=f"threads_english_textarea_{gen_id}",
                                label_visibility="collapsed",
                                disabled=True
                            )
                            st.code(st.session_state.generated_posts["threads"]["english"], language=None)

                            # 추천 배지
                            st.markdown("**🗣️ Engagement Booster!** - Question-driven for max replies")

                            if st.button("📋 Copy", key=f"threads_english_copy_{gen_id}", use_container_width=True):
                                copy_to_clipboard(st.session_state.generated_posts["threads"]["english"], f"threads_english_copy_{gen_id}")
                                st.success("✅ 복사 완료!")

        except Exception as e:
            status_container.update(label="❌ 오류 발생", state="error", expanded=True)
            with status_container:
                st.error(f"**예상치 못한 오류가 발생했습니다:**\n\n{str(e)}")
                st.info("💡 GOOGLE_API_KEY 환경 변수가 설정되어 있는지 확인해주세요.")

elif should_generate and not content_to_use.strip():
    with col2:
        st.error("❌ 기사 내용을 입력해주세요!")
# 이미 생성된 결과가 있으면 표시 (생성 중이 아닐 때만)
elif not should_generate and st.session_state.generated_posts:
    with col2:
        gen_id = st.session_state.generation_count

        # 바이럴 점수가 있는지 확인 (이전 세션 호환성)
        has_viral_scores = hasattr(st.session_state, 'viral_scores') and st.session_state.viral_scores

        # 최고 바이럴 픽 찾기 (점수가 있을 경우에만)
        if has_viral_scores:
            top_kr_platform_d, top_kr_score_d = get_top_viral_pick(st.session_state.viral_scores, "korean")
            top_en_platform_d, top_en_score_d = get_top_viral_pick(st.session_state.viral_scores, "english")

        # X (Twitter)
        if st.session_state.generated_posts["x"]["english"] or st.session_state.generated_posts["x"]["korean"]:
            st.markdown("### 🐦 X (Twitter)")
            st.success("✅ X 게시물 생성 완료!")
            st.info("💡 화제될 문장으로 시작 + 스레드 유도")

            tab_x_en_d, tab_x_kr_d = st.tabs(["🌐 English", "🇰🇷 Korean"])

            with tab_x_en_d:
                if st.session_state.generated_posts["x"]["english"]:
                    # Editor's Choice 배지 (최고 점수인 경우)
                    if has_viral_scores and top_en_platform_d == "x":
                        st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                    # 바이럴 점수 표시 (있을 경우에만)
                    if has_viral_scores:
                        st.markdown("**📈 예상 바이럴 점수**")
                        display_viral_score(
                            st.session_state.viral_scores["x"]["english"],
                            st.session_state.viral_reasons["x"]["english"],
                            "english"
                        )

                    st.text_area(
                        "English Version",
                        value=st.session_state.generated_posts["x"]["english"],
                        height=150,
                        key=f"x_english_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["x"]["english"], language=None)

                    # 추천 배지
                    st.markdown("**💫 글로벌 팬 추천!** - Gen Z Slang & 바이럴 최적화")

                    if st.button("📋 Copy", key=f"x_english_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["x"]["english"], f"x_english_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            with tab_x_kr_d:
                if st.session_state.generated_posts["x"]["korean"]:
                    # Editor's Choice 배지 (최고 점수인 경우)
                    if has_viral_scores and top_kr_platform_d == "x":
                        st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                    # 바이럴 점수 표시 (있을 경우에만)
                    if has_viral_scores:
                        st.markdown("**📈 예상 바이럴 점수**")
                        display_viral_score(
                            st.session_state.viral_scores["x"]["korean"],
                            st.session_state.viral_reasons["x"]["korean"],
                            "korean"
                        )

                    st.text_area(
                        "Korean Version",
                        value=st.session_state.generated_posts["x"]["korean"],
                        height=150,
                        key=f"x_korean_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["x"]["korean"], language=None)

                    # 추천 배지
                    st.markdown("**🔥 이 카피 추천!** - 국내 커뮤니티 화제성 최적화")

                    if st.button("📋 Copy", key=f"x_korean_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["x"]["korean"], f"x_korean_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            st.divider()

        # Instagram
        if st.session_state.generated_posts["instagram"]["english"] or st.session_state.generated_posts["instagram"]["korean"]:
            st.markdown("### 📸 Instagram")
            st.success("✅ Instagram 게시물 생성 완료!")
            st.info("💡 이모지 배치 + 비주얼 중심 감성 문구")

            tab_ig_en_d, tab_ig_kr_d = st.tabs(["🌐 English", "🇰🇷 Korean"])

            with tab_ig_en_d:
                if st.session_state.generated_posts["instagram"]["english"]:
                    # Editor's Choice 배지 (최고 점수인 경우)
                    if has_viral_scores and top_en_platform_d == "instagram":
                        st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                    # 바이럴 점수 표시 (있을 경우에만)
                    if has_viral_scores:
                        st.markdown("**📈 예상 바이럴 점수**")
                        display_viral_score(
                            st.session_state.viral_scores["instagram"]["english"],
                            st.session_state.viral_reasons["instagram"]["english"],
                            "english"
                        )

                    st.text_area(
                        "English Version",
                        value=st.session_state.generated_posts["instagram"]["english"],
                        height=300,
                        key=f"instagram_english_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["instagram"]["english"], language=None)

                    # 추천 배지
                    st.markdown("**🌟 Global Story Pick!** - Full 3-para narrative & relatability")

                    if st.button("📋 Copy", key=f"instagram_english_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["instagram"]["english"], f"instagram_english_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            with tab_ig_kr_d:
                if st.session_state.generated_posts["instagram"]["korean"]:
                    # Editor's Choice 배지 (최고 점수인 경우)
                    if has_viral_scores and top_kr_platform_d == "instagram":
                        st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                    # 바이럴 점수 표시 (있을 경우에만)
                    if has_viral_scores:
                        st.markdown("**📈 예상 바이럴 점수**")
                        display_viral_score(
                            st.session_state.viral_scores["instagram"]["korean"],
                            st.session_state.viral_reasons["instagram"]["korean"],
                            "korean"
                        )

                    st.text_area(
                        "Korean Version",
                        value=st.session_state.generated_posts["instagram"]["korean"],
                        height=300,
                        key=f"instagram_korean_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["instagram"]["korean"], language=None)

                    # 추천 배지
                    st.markdown("**✨ 감성 스토리 추천!** - 3문단 완전 서사 & 공감 포인트")

                    if st.button("📋 Copy", key=f"instagram_korean_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["instagram"]["korean"], f"instagram_korean_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            st.divider()

        # Threads
        if st.session_state.generated_posts["threads"]["english"] or st.session_state.generated_posts["threads"]["korean"]:
            st.markdown("### 🧵 Threads")
            st.success("✅ Threads 게시물 생성 완료!")
            st.info("💡 유저 참여형 질문 중심")

            tab_th_en_d, tab_th_kr_d = st.tabs(["🌐 English", "🇰🇷 Korean"])

            with tab_th_en_d:
                if st.session_state.generated_posts["threads"]["english"]:
                    # Editor's Choice 배지 (최고 점수인 경우)
                    if has_viral_scores and top_en_platform_d == "threads":
                        st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                    # 바이럴 점수 표시 (있을 경우에만)
                    if has_viral_scores:
                        st.markdown("**📈 예상 바이럴 점수**")
                        display_viral_score(
                            st.session_state.viral_scores["threads"]["english"],
                            st.session_state.viral_reasons["threads"]["english"],
                            "english"
                        )

                    st.text_area(
                        "English Version",
                        value=st.session_state.generated_posts["threads"]["english"],
                        height=300,
                        key=f"threads_english_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["threads"]["english"], language=None)

                    # 추천 배지
                    st.markdown("**🗣️ Engagement Booster!** - Question-driven for max replies")

                    if st.button("📋 Copy", key=f"threads_english_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["threads"]["english"], f"threads_english_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            with tab_th_kr_d:
                if st.session_state.generated_posts["threads"]["korean"]:
                    # Editor's Choice 배지 (최고 점수인 경우)
                    if has_viral_scores and top_kr_platform_d == "threads":
                        st.markdown("### 🔥 오늘의 바이럴 추천 픽!")

                    # 바이럴 점수 표시 (있을 경우에만)
                    if has_viral_scores:
                        st.markdown("**📈 예상 바이럴 점수**")
                        display_viral_score(
                            st.session_state.viral_scores["threads"]["korean"],
                            st.session_state.viral_reasons["threads"]["korean"],
                            "korean"
                        )

                    st.text_area(
                        "Korean Version",
                        value=st.session_state.generated_posts["threads"]["korean"],
                        height=300,
                        key=f"threads_korean_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["threads"]["korean"], language=None)

                    # 추천 배지
                    st.markdown("**💬 팬 참여 추천!** - 질문형 구조로 댓글 폭발 유도")

                    if st.button("📋 Copy", key=f"threads_korean_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["threads"]["korean"], f"threads_korean_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            st.divider()

        # 모델 정보
        if hasattr(st.session_state, 'model_name') and st.session_state.model_name:
            st.caption(f"🤖 Generated by: {st.session_state.model_name}")
