"""
YouTube 비디오 처리 모듈

YouTube URL에서 비디오를 다운로드하지 않고 스트리밍으로 프레임을 추출합니다.
"""

import yt_dlp
import cv2
from PIL import Image
import numpy as np
from typing import List, Optional, Dict
import config


def get_youtube_stream_url(youtube_url: str, debug: bool = True) -> Dict[str, any]:
    """
    YouTube URL에서 가장 안정적인 mp4 스트리밍 URL을 추출합니다.

    Args:
        youtube_url: YouTube 비디오 URL
        debug: 디버그 정보 출력 여부

    Returns:
        비디오 정보 딕셔너리 (url, title, duration 등)

    Raises:
        Exception: URL 추출 실패 시
    """
    ydl_opts = {
        # 포맷 선택: 낮은 해상도부터 시도 (더 안정적)
        'format': 'worst[ext=mp4]/worst/best[ext=mp4]/best',
        'quiet': not debug,
        'no_warnings': not debug,
        'extract_flat': False,
        'socket_timeout': 30,
        # User-Agent 추가 (봇 감지 우회)
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # 추가 옵션
        'nocheckcertificate': True,
        'prefer_insecure': False,
        'geo_bypass': True,
        'age_limit': None,
    }

    try:
        if debug:
            print(f"📋 yt-dlp 옵션: {ydl_opts}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if debug:
                print(f"🔄 yt-dlp로 정보 추출 중...")

            info = ydl.extract_info(youtube_url, download=False)

            if debug:
                print(f"✅ 정보 추출 완료")
                print(f"   - 제목: {info.get('title', 'Unknown')}")
                print(f"   - 길이: {info.get('duration', 0)}초")
                print(f"   - 사용 가능한 포맷 수: {len(info.get('formats', []))}")

            # 여러 URL 형식 중 가장 적합한 것 선택
            video_url = info.get('url')

            # 대체 URL 확인
            if not video_url and 'formats' in info:
                if debug:
                    print(f"🔍 대체 포맷 검색 중...")

                # mp4 포맷 우선 선택
                for fmt in info['formats']:
                    if fmt.get('ext') == 'mp4' and fmt.get('url'):
                        video_url = fmt['url']
                        if debug:
                            print(f"✅ mp4 포맷 선택: {fmt.get('format_id')}")
                        break

                # mp4가 없으면 첫 번째 사용 가능한 포맷
                if not video_url:
                    for fmt in info['formats']:
                        if fmt.get('url'):
                            video_url = fmt['url']
                            if debug:
                                print(f"✅ 대체 포맷 선택: {fmt.get('ext')} ({fmt.get('format_id')})")
                            break

            if not video_url:
                raise Exception("사용 가능한 스트림 URL을 찾을 수 없습니다")

            return {
                'url': video_url,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'width': info.get('width', 0),
                'height': info.get('height', 0),
            }

    except Exception as e:
        error_msg = str(e)
        if debug:
            print(f"❌ 에러 발생: {error_msg}")

        # 더 자세한 에러 메시지
        if "Video unavailable" in error_msg:
            raise Exception("영상을 사용할 수 없습니다. 영상이 삭제되었거나 비공개일 수 있습니다.")
        elif "Sign in to confirm your age" in error_msg:
            raise Exception("연령 제한이 있는 영상입니다. 다른 영상을 시도해주세요.")
        elif "This video is not available" in error_msg:
            raise Exception("이 영상은 사용할 수 없습니다. 지역 제한이나 저작권 문제일 수 있습니다.")
        else:
            raise Exception(f"YouTube URL 추출 실패: {error_msg}")


def extract_frame_with_retry(cap: cv2.VideoCapture, target_frame: int, total_frames: int, max_retry: int = 5) -> Optional[np.ndarray]:
    """
    네트워크 지연을 고려하여 프레임을 추출합니다.
    실패 시 전후로 최대 max_retry 프레임까지 재시도합니다.

    Args:
        cap: cv2.VideoCapture 객체
        target_frame: 목표 프레임 위치
        total_frames: 총 프레임 수
        max_retry: 최대 재시도 횟수 (기본값: 5)

    Returns:
        프레임 이미지 (numpy array) 또는 None
    """
    # 먼저 목표 프레임을 시도
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ret, frame = cap.read()

    if ret and frame is not None:
        return frame

    # 실패 시 전후로 재시도 (-1, +1, -2, +2, -3, +3, ..., -5, +5)
    for offset in range(1, max_retry + 1):
        for direction in [-1, 1]:  # 앞뒤로 시도
            retry_frame = target_frame + (offset * direction)

            # 범위 체크
            if retry_frame < 0 or retry_frame >= total_frames:
                continue

            cap.set(cv2.CAP_PROP_POS_FRAMES, retry_frame)
            ret, frame = cap.read()

            if ret and frame is not None:
                return frame

    return None


def extract_frames_from_youtube(youtube_url: str, num_frames: int = None) -> List[Image.Image]:
    """
    YouTube URL에서 프레임을 추출합니다.
    전체 비디오를 10등분하여 각 지점에서 프레임을 캡처합니다.

    Args:
        youtube_url: YouTube 비디오 URL
        num_frames: 추출할 프레임 수 (기본값: config.MAX_FRAMES)

    Returns:
        PIL.Image 객체 리스트 (메모리 내 작업)

    Raises:
        Exception: 프레임 추출 실패 시
    """
    if num_frames is None:
        num_frames = config.MAX_FRAMES

    # YouTube Shorts URL을 일반 URL로 변환
    if '/shorts/' in youtube_url:
        video_id = youtube_url.split('/shorts/')[-1].split('?')[0]
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"📱 Shorts URL을 일반 URL로 변환: {youtube_url}")

    # 1. 스트리밍 URL 및 메타데이터 추출
    print(f"🔍 YouTube URL 분석 중...")
    video_info = get_youtube_stream_url(youtube_url)
    stream_url = video_info['url']
    duration = video_info['duration']

    print(f"✅ 비디오 정보:")
    print(f"   제목: {video_info['title']}")
    print(f"   길이: {duration}초")
    print(f"   해상도: {video_info['width']}x{video_info['height']}")

    # 2. VideoCapture로 스트림 열기
    print(f"\n📹 비디오 스트림 열기 중...")

    # OpenCV 백엔드 옵션 시도
    cap = None
    backends = [
        cv2.CAP_ANY,      # 자동 선택
        cv2.CAP_FFMPEG,   # FFmpeg (가장 안정적)
        cv2.CAP_GSTREAMER # GStreamer
    ]

    for backend in backends:
        try:
            cap = cv2.VideoCapture(stream_url, backend)
            if cap.isOpened():
                print(f"✅ 백엔드 사용: {backend}")
                break
            else:
                cap.release()
                cap = None
        except Exception as e:
            print(f"⚠️  백엔드 {backend} 실패: {str(e)}")
            continue

    if cap is None or not cap.isOpened():
        raise Exception(
            "비디오 스트림을 열 수 없습니다.\n"
            "가능한 원인:\n"
            "1. YouTube의 일시적인 제한\n"
            "2. 영상이 비공개 또는 삭제됨\n"
            "3. 짧은 영상(Shorts)은 지원되지 않을 수 있음\n"
            "4. 네트워크 연결 문제\n\n"
            "해결 방법:\n"
            "- 일반 YouTube 영상 URL을 시도해보세요\n"
            "- 잠시 후 다시 시도해보세요\n"
            "- 다른 영상 URL을 시도해보세요"
        )

    try:
        # 총 프레임 수와 FPS 가져오기
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        print(f"✅ 총 프레임 수: {total_frames}")
        print(f"✅ FPS: {fps}")

        # 비디오 길이 제한 체크
        if duration > config.MAX_VIDEO_LENGTH:
            print(f"⚠️  경고: 비디오가 {config.MAX_VIDEO_LENGTH}초를 초과합니다. 처음 {config.MAX_VIDEO_LENGTH}초만 처리합니다.")
            total_frames = min(total_frames, int(fps * config.MAX_VIDEO_LENGTH))

        # 3. 프레임 추출 (10등분)
        print(f"\n🎬 {num_frames}개 프레임 추출 중...")
        interval = total_frames // num_frames
        frames = []

        for i in range(num_frames):
            target_frame = i * interval

            # 진행 상황 표시
            print(f"   [{i+1}/{num_frames}] 프레임 {target_frame} 추출 중...", end=" ")

            # 재시도 로직으로 프레임 추출
            frame = extract_frame_with_retry(cap, target_frame, total_frames, max_retry=5)

            if frame is None:
                print(f"❌ 실패")
                raise Exception(f"프레임 {target_frame} 추출 실패 (재시도 5회 모두 실패)")

            # BGR(OpenCV) → RGB(PIL) 변환
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # numpy array → PIL Image (메모리 내 작업)
            pil_image = Image.fromarray(frame_rgb)
            frames.append(pil_image)

            print(f"✅")

        print(f"\n✅ 총 {len(frames)}개 프레임 추출 완료!")
        return frames

    except Exception as e:
        raise Exception(f"프레임 추출 중 오류 발생: {str(e)}")

    finally:
        # 리소스 해제
        cap.release()
        print(f"🔒 비디오 스트림 닫기 완료")


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
    print("YouTube Processor 테스트")
    print("=" * 80)

    try:
        # 메타데이터 추출 테스트
        print("\n📊 메타데이터 추출 테스트:")
        metadata = get_youtube_metadata(test_url)
        print(f"   제목: {metadata['title']}")
        print(f"   길이: {metadata['duration']}초")
        print(f"   업로더: {metadata['uploader']}")

        # 프레임 추출 테스트
        print("\n🎬 프레임 추출 테스트:")
        frames = extract_frames_from_youtube(test_url, num_frames=10)

        print(f"\n✅ 성공! {len(frames)}개 프레임 추출됨")
        print(f"   첫 프레임 크기: {frames[0].size}")
        print(f"   첫 프레임 모드: {frames[0].mode}")

    except Exception as e:
        print(f"\n❌ 오류: {str(e)}")
