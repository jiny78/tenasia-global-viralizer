"""
YouTube 비디오 처리 모듈

YouTube URL에서 ffmpeg를 사용하여 안정적으로 프레임을 추출합니다.
OpenCV 스트리밍 대신 yt-dlp + ffmpeg 조합 사용.
"""

import yt_dlp
import subprocess
import tempfile
import os
from PIL import Image
from typing import List, Dict
from pathlib import Path
import config


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
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 30,
    }

    try:
        print(f"🔍 YouTube 비디오 정보 추출 중...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            # 비디오 URL 찾기
            video_url = info.get('url')
            if not video_url:
                raise Exception("비디오 URL을 찾을 수 없습니다")

            duration = info.get('duration', 0)

            print(f"✅ 비디오 정보 추출 완료")
            print(f"   제목: {info.get('title', 'Unknown')}")
            print(f"   길이: {duration}초")

            return {
                'url': video_url,
                'title': info.get('title', 'Unknown'),
                'duration': duration,
                'width': info.get('width', 0),
                'height': info.get('height', 0),
            }

    except Exception as e:
        error_msg = str(e)

        # 더 자세한 에러 메시지
        if "Video unavailable" in error_msg:
            raise Exception("영상을 사용할 수 없습니다. 영상이 삭제되었거나 비공개일 수 있습니다.")
        elif "Sign in to confirm your age" in error_msg:
            raise Exception("연령 제한이 있는 영상입니다. 다른 영상을 시도해주세요.")
        elif "This video is not available" in error_msg:
            raise Exception("이 영상은 사용할 수 없습니다. 지역 제한이나 저작권 문제일 수 있습니다.")
        else:
            raise Exception(f"YouTube 정보 추출 실패: {error_msg}")


def extract_frame_at_time(video_url: str, timestamp: float, output_path: str) -> bool:
    """
    ffmpeg를 사용하여 특정 시간의 프레임을 추출합니다.

    Args:
        video_url: 비디오 스트림 URL
        timestamp: 추출할 시간 (초)
        output_path: 저장할 이미지 경로

    Returns:
        성공 여부 (True/False)
    """
    try:
        # ffmpeg 명령어 구성
        cmd = [
            'ffmpeg',
            '-ss', str(timestamp),      # 시작 시간
            '-i', video_url,             # 입력 URL
            '-frames:v', '1',            # 1개 프레임만
            '-q:v', '2',                 # 높은 품질
            '-y',                        # 덮어쓰기
            output_path
        ]

        # ffmpeg 실행 (stderr는 숨김)
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False
        )

        # 파일이 생성되었는지 확인
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0

    except subprocess.TimeoutExpired:
        print(f"⚠️  타임아웃: {timestamp}초")
        return False
    except Exception as e:
        print(f"⚠️  에러: {str(e)}")
        return False


def extract_frames_from_youtube(youtube_url: str, num_frames: int = None) -> List[Image.Image]:
    """
    YouTube URL에서 프레임을 추출합니다.
    ffmpeg를 사용하여 안정적으로 프레임을 추출합니다.

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

    # YouTube Shorts URL을 일반 URL로 변환
    if '/shorts/' in youtube_url:
        video_id = youtube_url.split('/shorts/')[-1].split('?')[0]
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"📱 Shorts URL을 일반 URL로 변환: {youtube_url}")

    # 1. 비디오 정보 추출
    video_info = get_youtube_info(youtube_url)
    stream_url = video_info['url']
    duration = video_info['duration']

    # 비디오 길이 제한 체크
    if duration > config.MAX_VIDEO_LENGTH:
        print(f"⚠️  경고: 비디오가 {config.MAX_VIDEO_LENGTH}초를 초과합니다. 처음 {config.MAX_VIDEO_LENGTH}초만 처리합니다.")
        duration = config.MAX_VIDEO_LENGTH

    # 2. 타임스탬프 계산 (10등분)
    timestamps = []
    interval = duration / num_frames
    for i in range(num_frames):
        timestamp = i * interval
        timestamps.append(timestamp)

    print(f"\n🎬 {num_frames}개 프레임 추출 중 (ffmpeg 사용)...")
    print(f"   추출 위치: {[f'{t:.1f}초' for t in timestamps]}")

    # 3. 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp(prefix="youtube_frames_")
    frames = []

    try:
        # 4. 각 타임스탬프마다 프레임 추출
        for i, timestamp in enumerate(timestamps):
            print(f"   [{i+1}/{num_frames}] {timestamp:.1f}초 추출 중...", end=" ")

            # 임시 파일 경로
            temp_file = os.path.join(temp_dir, f"frame_{i:03d}.jpg")

            # ffmpeg로 프레임 추출
            success = extract_frame_at_time(stream_url, timestamp, temp_file)

            if not success:
                print(f"❌ 실패")
                # 실패해도 계속 진행 (최소 5개 이상 성공하면 OK)
                if len(frames) < 5:
                    continue
                else:
                    break

            # PIL로 이미지 로드
            try:
                pil_image = Image.open(temp_file)
                # RGB로 변환 (필요시)
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                frames.append(pil_image.copy())  # 복사본 저장
                print(f"✅")
            except Exception as e:
                print(f"❌ 로드 실패: {str(e)}")
                continue

        # 5. 최소 프레임 수 체크
        if len(frames) < 5:
            raise Exception(f"프레임 추출 실패: {len(frames)}개만 추출됨 (최소 5개 필요)")

        print(f"\n✅ 총 {len(frames)}개 프레임 추출 완료!")
        return frames

    except Exception as e:
        raise Exception(f"프레임 추출 중 오류 발생: {str(e)}")

    finally:
        # 6. 임시 파일 정리
        try:
            import shutil
            shutil.rmtree(temp_dir)
            print(f"🔒 임시 파일 정리 완료")
        except:
            pass


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
