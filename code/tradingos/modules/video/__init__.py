"""Video module - Ross Cameron content automation pipeline."""

from tradingos.modules.video.engine import RossCameronPipeline, create_video_pipeline
from tradingos.modules.video.interfaces import (
    ExtractedContent,
    VideoPipeline,
    VideoPipelineConfig,
    VideoSource,
)

__all__ = [
    "VideoPipeline",
    "VideoPipelineConfig",
    "VideoSource",
    "ExtractedContent",
    "RossCameronPipeline",
    "create_video_pipeline",
]
