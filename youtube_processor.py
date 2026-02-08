"""
YouTube 비디오 처리 모듈

YouTube URL에서 yt-dlp로 가장 낮은 화질의 영상을 다운로드하고
OpenCV로 로컬 파일에서 프레임을 추출합니다.
"""

import yt_dlp
import cv2
import tempfile
import os
from PIL import Image
from typing import List, Dict, Optional
from pathlib import Path
import config


def download_video_for_ai(youtube_url: str) -> str:
    """
    yt-dlp를 사용하여 영상을 가장 낮은 화질로 다운로드합니다.
    AI 분석용이므로 파일 용량을 최소화하여 속도를 극대화합니다.

    Args:
        youtube_url: YouTube 비디오 URL

    Returns:
        다운로드된 mp4 파일의 경로

    Raises:
        Exception: 다운로드 실패 시
    """
    # 임시 파일 경로 생성
    temp_dir = tempfile.gettempdir()
    temp_video_path = os.path.join(temp_dir, f"youtube_ai_{os.getpid()}.mp4")

    ydl_opts = {
        # 가장 낮은 화질 선택 (용량 최소화)
        'format': 'worst[ext=mp4]/worst/bestvideo[height<=360][ext=mp4]/bestvideo[height<=360]',
        'outtmpl': temp_video_path,
        'quiet': False,
        'no_warnings': False,
        # 다운로드 속도 최적화
        'concurrent_fragment_downloads': 4,
        'http_chunk_size': 10485760,  # 10MB chunks
        # 추가 옵션
        'geo_bypass': True,
        'nocheckcertificate': True,
    }

    try:
        print(f"📥 YouTube 영상 다운로드 중 (가장 낮은 화질)...")
        print(f"   URL: {youtube_url}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)

            print(f"✅ 다운로드 완료!")
            print(f"   제목: {info.get('title', 'Unknown')}")
            print(f"   길이: {info.get('duration', 0)}초")

            # 파일이 생성되었는지 확인
            if os.path.exists(temp_video_path):
                file_size_mb = os.path.getsize(temp_video_path) / (1024 * 1024)
                print(f"   파일 크기: {file_size_mb:.2f} MB")
                print(f"   저장 경로: {temp_video_path}")
                return temp_video_path
            else:
                raise Exception("다운로드된 파일을 찾을 수 없습니다")

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ 다운로드 실패: {error_msg}\n")

        # 에러 파일이 있으면 삭제
        if os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except:
                pass

        # 더 자세한 에러 메시지
        if "Video unavailable" in error_msg:
            raise Exception("영상을 사용할 수 없습니다. 영상이 삭제되었거나 비공개일 수 있습니다.")
        elif "Sign in to confirm your age" in error_msg or "age" in error_msg.lower():
            raise Exception("연령 제한이 있는 영상입니다. 다른 영상을 시도해주세요.")
        elif "This video is not available" in error_msg or "not available" in error_msg.lower():
            raise Exception("이 영상은 사용할 수 없습니다. 지역 제한이나 저작권 문제일 수 있습니다.")
        elif "Private video" in error_msg:
            raise Exception("비공개 영상입니다. 공개 영상을 시도해주세요.")
        elif "members-only" in error_msg.lower():
            raise Exception("멤버십 전용 영상입니다. 일반 공개 영상을 시도해주세요.")
        else:
            raise Exception(f"YouTube 다운로드 실패: {error_msg}")


def get_youtube_info(youtube_url: str) -> Dict[str, any]:
    """
    YouTube URL에서 비디오 정보를 추출합니다 (URL 포함).

    Args:
        youtube_url: YouTube 비디오 URL

    Returns:
        비디오 정보 딕셔너리 (url, title, duration 등)

    Raises:
        Exception: 정보 추출 실패 시
    """
    # Shorts 감지
    is_shorts = '/shorts/' in youtube_url

    # Shorts 최적화 포맷 (낮은 해상도, 세로 영상 우선)
    if is_shorts:
        format_str = 'worst[ext=mp4]/worst/best[ext=mp4]/best'
        print(f"📱 Shorts 모드: 낮은 해상도 우선 선택")
    else:
        format_str = 'best[ext=mp4]/best'

    ydl_opts = {
        'format': format_str,
        'quiet': False,  # 디버깅을 위해 False로 변경
        'no_warnings': False,  # 경고 메시지 출력
        'extract_flat': False,
        'socket_timeout': 30,
        'ignoreerrors': False,  # 에러를 명확히 표시
        # 추가 옵션
        'geo_bypass': True,  # 지역 제한 우회 시도
        'nocheckcertificate': True,  # SSL 인증서 검사 무시
    }

    try:
        print(f"🔍 YouTube 비디오 정보 추출 중...")
        print(f"   URL: {youtube_url}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            # 디버깅: 사용 가능한 포맷 출력
            if 'formats' in info:
                print(f"   사용 가능한 포맷 수: {len(info['formats'])}")
                # 처음 3개 포맷만 출력
                for i, fmt in enumerate(info['formats'][:3]):
                    print(f"   포맷 {i+1}: {fmt.get('format_id')} - {fmt.get('ext')} ({fmt.get('resolution', 'N/A')})")

            # 비디오 URL 찾기
            video_url = info.get('url')
            if not video_url:
                # 대체 URL 찾기
                if 'formats' in info and len(info['formats']) > 0:
                    for fmt in info['formats']:
                        if fmt.get('url'):
                            video_url = fmt['url']
                            print(f"   대체 URL 사용: {fmt.get('format_id')}")
                            break

                if not video_url:
                    raise Exception("비디오 URL을 찾을 수 없습니다")

            duration = info.get('duration', 0)

            print(f"✅ 비디오 정보 추출 완료")
            print(f"   제목: {info.get('title', 'Unknown')}")
            print(f"   길이: {duration}초")
            print(f"   업로더: {info.get('uploader', 'Unknown')}")

            return {
                'url': video_url,
                'title': info.get('title', 'Unknown'),
                'duration': duration,
                'width': info.get('width', 0),
                'height': info.get('height', 0),
            }

    except Exception as e:
        error_msg = str(e)

        print(f"\n❌ 에러 발생: {error_msg}\n")

        # 더 자세한 에러 메시지
        if "Video unavailable" in error_msg:
            raise Exception("영상을 사용할 수 없습니다. 영상이 삭제되었거나 비공개일 수 있습니다.")
        elif "Sign in to confirm your age" in error_msg or "age" in error_msg.lower():
            raise Exception("연령 제한이 있는 영상입니다. 다른 영상을 시도해주세요.")
        elif "This video is not available" in error_msg or "not available" in error_msg.lower():
            raise Exception("이 영상은 사용할 수 없습니다. 지역 제한이나 저작권 문제일 수 있습니다.")
        elif "Private video" in error_msg:
            raise Exception("비공개 영상입니다. 공개 영상을 시도해주세요.")
        elif "members-only" in error_msg.lower():
            raise Exception("멤버십 전용 영상입니다. 일반 공개 영상을 시도해주세요.")
        else:
            raise Exception(f"YouTube 정보 추출 실패: {error_msg}")


def extract_frame_from_video(video_path: str, frame_position: int, skip_retry: bool = True) -> Optional[Image.Image]:
    """
    OpenCV를 사용하여 로컬 비디오 파일에서 특정 프레임을 추출합니다.
    Skip-and-Retry: 비어있는 프레임을 만나면 앞으로 이동하여 재시도

    Args:
        video_path: 로컬 비디오 파일 경로
        frame_position: 프레임 위치 (번호)
        skip_retry: Skip-and-Retry 활성화 여부 (기본값: True)

    Returns:
        PIL.Image 객체 또는 None
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return None

    try:
        # Skip-and-Retry: 0, +30, +60, +90 프레임씩 앞으로 이동
        retry_offsets = [0, 30, 60, 90] if skip_retry else [0]

        for offset in retry_offsets:
            adjusted_position = frame_position + offset

            if offset > 0:
                print(f"\n      ↻ Skip-and-Retry: +{offset} 프레임 앞으로...", end=" ")

            # 프레임 위치 설정
            cap.set(cv2.CAP_PROP_POS_FRAMES, adjusted_position)
            ret, frame = cap.read()

            if ret and frame is not None and frame.size > 0:
                # BGR → RGB 변환
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # PIL Image로 변환
                pil_image = Image.fromarray(frame_rgb)
                return pil_image

        return None

    finally:
        cap.release()


def extract_frames_from_youtube(youtube_url: str, num_frames: int = None) -> tuple[List[Image.Image], str]:
    """
    YouTube URL에서 프레임을 추출합니다.
    yt-dlp로 가장 낮은 화질의 영상을 다운로드하고 OpenCV로 프레임을 추출합니다.

    Args:
        youtube_url: YouTube 비디오 URL
        num_frames: 추출할 프레임 수 (기본값: config.MAX_FRAMES)

    Returns:
        PIL.Image 객체 리스트

    Raises:
        Exception: 프레임 추출 실패 시
    """
    if num_frames is None:
        num_frames = config.MAX_FRAMES

    # YouTube Shorts 감지
    is_shorts = '/shorts/' in youtube_url

    # YouTube Shorts URL을 일반 URL로 변환
    if is_shorts:
        video_id = youtube_url.split('/shorts/')[-1].split('?')[0]
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"📱 Shorts 감지: {video_id}")
        print(f"   일반 URL로 변환: {youtube_url}")
        # Shorts는 보통 짧으므로 프레임 수 조정
        if num_frames > 5:
            num_frames = 5
            print(f"   Shorts 최적화: 프레임 수를 5개로 조정")

    video_path = None

    try:
        # 1. 영상 다운로드 (가장 낮은 화질)
        video_path = download_video_for_ai(youtube_url)

        # 2. OpenCV로 비디오 열기
        print(f"\n🎬 {num_frames}개 프레임 추출 중 (OpenCV 사용)...")
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise Exception("다운로드된 영상 파일을 열 수 없습니다")

        # 총 프레임 수와 FPS 가져오기
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0

        print(f"   총 프레임 수: {total_frames}")
        print(f"   FPS: {fps:.2f}")
        print(f"   길이: {duration:.1f}초")

        cap.release()

        # 비디오 길이 제한 체크
        if duration > config.MAX_VIDEO_LENGTH:
            print(f"⚠️  경고: 비디오가 {config.MAX_VIDEO_LENGTH}초를 초과합니다.")
            print(f"   처음 {config.MAX_VIDEO_LENGTH}초만 처리합니다.")
            total_frames = min(total_frames, int(fps * config.MAX_VIDEO_LENGTH))

        # 3. 프레임 위치 계산 (균등 분포)
        interval = total_frames // num_frames
        frame_positions = [i * interval for i in range(num_frames)]

        print(f"   추출 위치: {[f'{p}번째' for p in frame_positions]}\n")

        # 4. 각 위치에서 프레임 추출 (Skip-and-Retry)
        frames = []
        success_count = 0
        fail_count = 0

        for i, frame_pos in enumerate(frame_positions):
            print(f"   [{i+1}/{num_frames}] 프레임 {frame_pos} 추출 중...", end=" ")

            # OpenCV로 프레임 추출 (Skip-and-Retry 활성화)
            pil_image = extract_frame_from_video(video_path, frame_pos, skip_retry=True)

            if pil_image is None:
                print(f"❌ 모든 재시도 실패")
                fail_count += 1
                continue

            frames.append(pil_image)
            success_count += 1
            print(f"✅")

        # 5. 프레임 추출 결과 확인 (1개 이상이면 진행)
        print(f"\n{'='*60}")
        print(f"📊 프레임 추출 결과: 성공 {success_count}개 / 실패 {fail_count}개")
        print(f"{'='*60}")

        if len(frames) == 0:
            error_details = "\n❌ 프레임 추출 완전 실패: 0개 추출됨\n\n"
            error_details += "가능한 원인:\n"
            error_details += "1. 다운로드된 영상 파일이 손상됨\n"
            error_details += "2. 영상 포맷이 OpenCV와 호환되지 않음\n"
            error_details += "3. 영상의 모든 프레임이 비어있음\n\n"
            error_details += "해결 방법:\n"
            error_details += "- 다른 YouTube 공개 영상 시도\n"
            error_details += "- 방법 3: 직접 입력 사용"
            raise Exception(error_details)

        if len(frames) < num_frames:
            print(f"⚠️  경고: {len(frames)}개만 추출됨 (목표: {num_frames}개)")
            print(f"   → 추출된 프레임으로 분석을 진행합니다\n")

        print(f"✅ 총 {len(frames)}개 프레임 추출 완료!")
        print(f"📦 영상 파일 보관: {video_path}")
        print(f"   (Gemini 분석 후 자동 삭제됩니다)\n")

        # 프레임 리스트와 비디오 파일 경로를 함께 반환
        return frames, video_path

    except Exception as e:
        # 에러 발생 시 비디오 파일 삭제
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                print(f"🔒 에러로 인한 임시 파일 삭제")
            except:
                pass
        raise Exception(f"프레임 추출 중 오류 발생: {str(e)}")


def get_youtube_metadata(youtube_url: str) -> Dict[str, any]:
    """
    YouTube 비디오의 메타데이터만 추출합니다 (프레임 추출 없이).

    Args:
        youtube_url: YouTube 비디오 URL

    Returns:
        메타데이터 딕셔너리

    Raises:
        Exception: 메타데이터 추출 실패 시
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
                'description': info.get('description', ''),
            }

    except Exception as e:
        raise Exception(f"메타데이터 추출 실패: {str(e)}")


if __name__ == "__main__":
    # 테스트 코드
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # 예시 URL

    print("=" * 80)
    print("YouTube Processor 테스트 (ffmpeg 방식)")
    print("=" * 80)

    try:
        # 메타데이터 추출 테스트
        print("\n📊 메타데이터 추출 테스트:")
        metadata = get_youtube_metadata(test_url)
        print(f"   제목: {metadata['title']}")
        print(f"   길이: {metadata['duration']}초")
        print(f"   업로더: {metadata['uploader']}")

        # 프레임 추출 테스트
        print("\n🎬 프레임 추출 테스트 (5개 프레임):")
        frames = extract_frames_from_youtube(test_url, num_frames=5)

        print(f"\n✅ 성공! {len(frames)}개 프레임 추출됨")
        print(f"   첫 프레임 크기: {frames[0].size}")
        print(f"   첫 프레임 모드: {frames[0].mode}")

    except Exception as e:
        print(f"\n❌ 오류: {str(e)}")
