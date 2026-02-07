import streamlit as st
import streamlit.components.v1 as components
from engine import generate_sns_posts_streaming
from extractor import extract_article

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

# 타이틀
st.title("🌐 Global Viralizer")
st.markdown("K-엔터 기사를 글로벌 바이럴 SNS 콘텐츠로 변환하세요 (텐아시아 · 한국경제)")

# 사이드바에 정보 표시
with st.sidebar:
    st.header("ℹ️ 사용 방법")

    # 모바일/데스크톱 안내
    st.info("📱 모바일에서도 완벽하게 작동합니다!")

    st.markdown("""
    **방법 1: URL 입력** ⚡
    1. 텐아시아/한국경제 기사 URL 입력
    2. 'Extract' 버튼 클릭
    3. 자동으로 출처 인식 및 게시물 생성

    **방법 2: 직접 입력** ✍️
    1. 기사 내용 붙여넣기
    2. 'Generate' 버튼 클릭

    **결과 확인** 🎉
    - 🌐 English / 🇰🇷 Korean 탭 전환
    - 📋 코드 블록에서 복사
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
    st.subheader("📰 기사 입력")

    # URL 입력 섹션
    st.markdown("##### 방법 1: URL에서 자동 추출")
    article_url = st.text_input(
        "기사 URL",
        placeholder="https://www.tenasia.co.kr/article/... 또는 https://www.hankyung.com/...",
        help="텐아시아 또는 한국경제 기사 URL을 입력하면 자동으로 출처와 내용을 추출합니다"
    )

    extract_button = st.button("📥 Extract Article", type="secondary", use_container_width=True)

    st.divider()

    # 직접 입력 섹션
    st.markdown("##### 방법 2: 직접 입력")

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
        height=300,
        placeholder="여기에 한국어 기사 내용을 붙여넣으세요...",
        key="content_input"
    )

    generate_button = st.button("🚀 Generate SNS Posts", type="primary", use_container_width=True)

with col2:
    st.subheader("✨ 생성 결과")

# Extract 버튼 클릭 시
if extract_button:
    if not article_url.strip():
        with col1:
            st.error("URL을 입력해주세요!")
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
    st.session_state.generation_status = {
        "x": {"english": "generating", "korean": "pending"},
        "instagram": {"english": "pending", "korean": "pending"},
        "threads": {"english": "pending", "korean": "pending"}
    }
    st.session_state.generation_count += 1

    with col2:
        gen_id = st.session_state.generation_count

        # Placeholder 미리 생성
        st.markdown("### 🐦 X (Twitter)")
        x_status_placeholder = st.empty()
        x_content_placeholder = st.container()

        st.divider()

        st.markdown("### 📸 Instagram")
        instagram_status_placeholder = st.empty()
        instagram_content_placeholder = st.container()

        st.divider()

        st.markdown("### 🧵 Threads")
        threads_status_placeholder = st.empty()
        threads_content_placeholder = st.container()

        st.divider()

        model_info_placeholder = st.empty()

        # 초기 상태
        x_status_placeholder.info("🎨 X (Twitter) 게시물 생성 중...")
        instagram_status_placeholder.info("⏳ 대기 중...")
        threads_status_placeholder.info("⏳ 대기 중...")

        try:
            # 스트리밍 방식으로 생성
            for update in generate_sns_posts_streaming(content_to_use, title_to_use, site_name_to_use):
                platform = update["platform"]
                status = update["status"]
                language = update.get("language")

                if platform == "error":
                    x_status_placeholder.error(f"❌ 생성 실패: {update.get('error', '알 수 없는 오류')}")
                    break

                elif platform == "all" and status == "completed":
                    st.session_state.model_name = update.get("model")
                    model_info_placeholder.caption(f"🤖 Generated by: {st.session_state.model_name}")

                else:
                    # 각 플랫폼/언어별 처리
                    if platform == "x" and language:
                        if status == "generating":
                            lang_display = "영문" if language == "english" else "한국어"
                            x_status_placeholder.info(f"🎨 X (Twitter) {lang_display} 게시물 생성 중...")
                            st.session_state.generation_status["x"][language] = "generating"
                        elif status == "completed":
                            st.session_state.generated_posts["x"][language] = update["content"]
                            st.session_state.generation_status["x"][language] = "completed"

                            # 두 언어 모두 완료되었는지 확인
                            if all(status == "completed" for status in st.session_state.generation_status["x"].values()):
                                x_status_placeholder.success("✅ X 게시물 생성 완료!")

                                with x_content_placeholder:
                                    st.info("💡 화제될 문장으로 시작 + 스레드 유도")
                                    # English/Korean 탭
                                    tab_x_en, tab_x_kr = st.tabs(["🌐 English", "🇰🇷 Korean"])

                                    with tab_x_en:
                                        st.text_area(
                                            "English Version",
                                            value=st.session_state.generated_posts["x"]["english"],
                                            height=150,
                                            key=f"x_en_textarea_{gen_id}",
                                            label_visibility="collapsed",
                                            disabled=True
                                        )
                                        st.code(st.session_state.generated_posts["x"]["english"], language=None)
                                        if st.button("📋 Copy", key=f"x_en_copy_{gen_id}", use_container_width=True):
                                            copy_to_clipboard(st.session_state.generated_posts["x"]["english"], f"x_en_copy_{gen_id}")
                                            st.success("✅ 복사 완료!")

                                    with tab_x_kr:
                                        st.text_area(
                                            "Korean Version",
                                            value=st.session_state.generated_posts["x"]["korean"],
                                            height=150,
                                            key=f"x_kr_textarea_{gen_id}",
                                            label_visibility="collapsed",
                                            disabled=True
                                        )
                                        st.code(st.session_state.generated_posts["x"]["korean"], language=None)
                                        if st.button("📋 Copy", key=f"x_kr_copy_{gen_id}", use_container_width=True):
                                            copy_to_clipboard(st.session_state.generated_posts["x"]["korean"], f"x_kr_copy_{gen_id}")
                                            st.success("✅ 복사 완료!")

                    elif platform == "instagram" and language:
                        if status == "generating":
                            lang_display = "영문" if language == "english" else "한국어"
                            instagram_status_placeholder.info(f"🎨 Instagram {lang_display} 게시물 생성 중...")
                            st.session_state.generation_status["instagram"][language] = "generating"
                        elif status == "completed":
                            st.session_state.generated_posts["instagram"][language] = update["content"]
                            st.session_state.generation_status["instagram"][language] = "completed"

                            # 두 언어 모두 완료되었는지 확인
                            if all(status == "completed" for status in st.session_state.generation_status["instagram"].values()):
                                instagram_status_placeholder.success("✅ Instagram 게시물 생성 완료!")

                                with instagram_content_placeholder:
                                    st.info("💡 이모지 배치 + 비주얼 중심 감성 문구")
                                    # English/Korean 탭
                                    tab_ig_en, tab_ig_kr = st.tabs(["🌐 English", "🇰🇷 Korean"])

                                    with tab_ig_en:
                                        st.text_area(
                                            "English Version",
                                            value=st.session_state.generated_posts["instagram"]["english"],
                                            height=300,
                                            key=f"instagram_en_textarea_{gen_id}",
                                            label_visibility="collapsed",
                                            disabled=True
                                        )
                                        st.code(st.session_state.generated_posts["instagram"]["english"], language=None)
                                        if st.button("📋 Copy", key=f"instagram_en_copy_{gen_id}", use_container_width=True):
                                            copy_to_clipboard(st.session_state.generated_posts["instagram"]["english"], f"instagram_en_copy_{gen_id}")
                                            st.success("✅ 복사 완료!")

                                    with tab_ig_kr:
                                        st.text_area(
                                            "Korean Version",
                                            value=st.session_state.generated_posts["instagram"]["korean"],
                                            height=300,
                                            key=f"instagram_kr_textarea_{gen_id}",
                                            label_visibility="collapsed",
                                            disabled=True
                                        )
                                        st.code(st.session_state.generated_posts["instagram"]["korean"], language=None)
                                        if st.button("📋 Copy", key=f"instagram_kr_copy_{gen_id}", use_container_width=True):
                                            copy_to_clipboard(st.session_state.generated_posts["instagram"]["korean"], f"instagram_kr_copy_{gen_id}")
                                            st.success("✅ 복사 완료!")

                    elif platform == "threads" and language:
                        if status == "generating":
                            lang_display = "영문" if language == "english" else "한국어"
                            threads_status_placeholder.info(f"🎨 Threads {lang_display} 게시물 생성 중...")
                            st.session_state.generation_status["threads"][language] = "generating"
                        elif status == "completed":
                            st.session_state.generated_posts["threads"][language] = update["content"]
                            st.session_state.generation_status["threads"][language] = "completed"

                            # 두 언어 모두 완료되었는지 확인
                            if all(status == "completed" for status in st.session_state.generation_status["threads"].values()):
                                threads_status_placeholder.success("✅ Threads 게시물 생성 완료!")

                                with threads_content_placeholder:
                                    st.info("💡 유저 참여형 질문 중심")
                                    # English/Korean 탭
                                    tab_th_en, tab_th_kr = st.tabs(["🌐 English", "🇰🇷 Korean"])

                                    with tab_th_en:
                                        st.text_area(
                                            "English Version",
                                            value=st.session_state.generated_posts["threads"]["english"],
                                            height=300,
                                            key=f"threads_en_textarea_{gen_id}",
                                            label_visibility="collapsed",
                                            disabled=True
                                        )
                                        st.code(st.session_state.generated_posts["threads"]["english"], language=None)
                                        if st.button("📋 Copy", key=f"threads_en_copy_{gen_id}", use_container_width=True):
                                            copy_to_clipboard(st.session_state.generated_posts["threads"]["english"], f"threads_en_copy_{gen_id}")
                                            st.success("✅ 복사 완료!")

                                    with tab_th_kr:
                                        st.text_area(
                                            "Korean Version",
                                            value=st.session_state.generated_posts["threads"]["korean"],
                                            height=300,
                                            key=f"threads_kr_textarea_{gen_id}",
                                            label_visibility="collapsed",
                                            disabled=True
                                        )
                                        st.code(st.session_state.generated_posts["threads"]["korean"], language=None)
                                        if st.button("📋 Copy", key=f"threads_kr_copy_{gen_id}", use_container_width=True):
                                            copy_to_clipboard(st.session_state.generated_posts["threads"]["korean"], f"threads_kr_copy_{gen_id}")
                                            st.success("✅ 복사 완료!")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            st.info("💡 GOOGLE_API_KEY 환경 변수가 설정되어 있는지 확인해주세요.")

elif should_generate and not content_to_use.strip():
    with col2:
        st.error("기사 내용을 입력해주세요!")

# 이미 생성된 결과가 있으면 표시 (생성 중이 아닐 때만)
elif not should_generate and st.session_state.generated_posts:
    with col2:
        gen_id = st.session_state.generation_count

        # X (Twitter)
        if st.session_state.generated_posts["x"]["english"] or st.session_state.generated_posts["x"]["korean"]:
            st.markdown("### 🐦 X (Twitter)")
            st.success("✅ X 게시물 생성 완료!")
            st.info("💡 화제될 문장으로 시작 + 스레드 유도")

            tab_x_en_d, tab_x_kr_d = st.tabs(["🌐 English", "🇰🇷 Korean"])

            with tab_x_en_d:
                if st.session_state.generated_posts["x"]["english"]:
                    st.text_area(
                        "English Version",
                        value=st.session_state.generated_posts["x"]["english"],
                        height=150,
                        key=f"x_en_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["x"]["english"], language=None)
                    if st.button("📋 Copy", key=f"x_en_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["x"]["english"], f"x_en_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            with tab_x_kr_d:
                if st.session_state.generated_posts["x"]["korean"]:
                    st.text_area(
                        "Korean Version",
                        value=st.session_state.generated_posts["x"]["korean"],
                        height=150,
                        key=f"x_kr_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["x"]["korean"], language=None)
                    if st.button("📋 Copy", key=f"x_kr_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["x"]["korean"], f"x_kr_copy_display_{gen_id}")
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
                    st.text_area(
                        "English Version",
                        value=st.session_state.generated_posts["instagram"]["english"],
                        height=300,
                        key=f"instagram_en_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["instagram"]["english"], language=None)
                    if st.button("📋 Copy", key=f"instagram_en_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["instagram"]["english"], f"instagram_en_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            with tab_ig_kr_d:
                if st.session_state.generated_posts["instagram"]["korean"]:
                    st.text_area(
                        "Korean Version",
                        value=st.session_state.generated_posts["instagram"]["korean"],
                        height=300,
                        key=f"instagram_kr_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["instagram"]["korean"], language=None)
                    if st.button("📋 Copy", key=f"instagram_kr_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["instagram"]["korean"], f"instagram_kr_copy_display_{gen_id}")
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
                    st.text_area(
                        "English Version",
                        value=st.session_state.generated_posts["threads"]["english"],
                        height=300,
                        key=f"threads_en_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["threads"]["english"], language=None)
                    if st.button("📋 Copy", key=f"threads_en_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["threads"]["english"], f"threads_en_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            with tab_th_kr_d:
                if st.session_state.generated_posts["threads"]["korean"]:
                    st.text_area(
                        "Korean Version",
                        value=st.session_state.generated_posts["threads"]["korean"],
                        height=300,
                        key=f"threads_kr_textarea_display_{gen_id}",
                        label_visibility="collapsed",
                        disabled=True
                    )
                    st.code(st.session_state.generated_posts["threads"]["korean"], language=None)
                    if st.button("📋 Copy", key=f"threads_kr_copy_display_{gen_id}", use_container_width=True):
                        copy_to_clipboard(st.session_state.generated_posts["threads"]["korean"], f"threads_kr_copy_display_{gen_id}")
                        st.success("✅ 복사 완료!")

            st.divider()

        # 모델 정보
        if hasattr(st.session_state, 'model_name') and st.session_state.model_name:
            st.caption(f"🤖 Generated by: {st.session_state.model_name}")
