"""Video Pipeline interfaces - Ross Cameron content automation."""

from dataclasses import dataclass
from typing import Any


@dataclass
class VideoSource:
    """Source video configuration."""
    platform: str  # youtube, local
    channel_id: str | None = None
    video_id: str | None = None
    local_path: str | None = None
    keywords: list[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@dataclass
class ExtractedContent:
    """Content extracted from video."""
    video_id: str
    title: str
    transcript: str
    segments: list[dict[str, Any]]  # timestamp, text, speaker
    key_moments: list[dict[str, Any]]  # timestamp, type, description
    tickers_mentioned: list[str]
    patterns_discussed: list[str]
    duration_seconds: int


@dataclass
class VideoPipelineConfig:
    """Configuration for video pipeline."""
    sources: list[VideoSource]
    output_dir: str = "data/video"
    whisper_model: str = "base"  # tiny, base, small, medium, large
    diarization: bool = True
    extract_tickers: bool = True
    extract_patterns: bool = True
    schedule: str = "0 3 * * 1-5"  # 3 AM weekdays


class VideoPipeline:
    """Base class for video content pipeline."""

    async def process_source(self, source: VideoSource) -> list[ExtractedContent]:
        raise NotImplementedError

    async def run_scheduled(self) -> list[ExtractedContent]:
        raise NotImplementedError

    async def get_processed_videos(self) -> list[str]:
        raise NotImplementedError
