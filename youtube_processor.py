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


def get_youtube_stream_url(youtube_url: str) -> Dict[str, any]:
    """
    YouTube URL에서 가장 안정적인 mp4 스트리밍 URL을 추출합니다.

    Args:
        youtube_url: YouTube 비디오 URL

    Returns:
        비디오 정보 딕셔너리 (url, title, duration 등)

    Raises:
        Exception: URL 추출 실패 시
    """
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # mp4 우선, 없으면 최선의 포맷
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 30,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            return {
                'url': info['url'],
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'width': info.get('width', 0),
                'height': info.get('height', 0),
            }

    except Exception as e:
        raise Exception(f"YouTube URL 추출 실패: {str(e)}")


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
    cap = cv2.VideoCapture(stream_url)

    if not cap.isOpened():
        raise Exception("비디오 스트림을 열 수 없습니다.")

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
