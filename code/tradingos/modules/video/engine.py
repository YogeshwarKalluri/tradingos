"""Video Pipeline Engine - Ross Cameron content automation."""

import json
import re
from pathlib import Path
from typing import Any

from tradingos.core.logging import get_logger
from tradingos.modules.video.interfaces import (
    ExtractedContent,
    VideoPipeline,
    VideoPipelineConfig,
    VideoSource,
)

logger = get_logger(__name__)


class RossCameronPipeline(VideoPipeline):
    """Video pipeline for Ross Cameron content."""

    def __init__(self, config: VideoPipelineConfig | dict[str, Any] | None = None):
        if isinstance(config, dict):
            config = VideoPipelineConfig(**config)
        self.config = config or VideoPipelineConfig(sources=[])
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_videos: set[str] = set()
        self._load_processed()
        logger.info("video_pipeline_initialized", output_dir=str(self.output_dir))

    def _load_processed(self) -> None:
        """Load processed video IDs."""
        processed_file = self.output_dir / "processed.json"
        if processed_file.exists():
            try:
                with open(processed_file) as f:
                    self.processed_videos = set(json.load(f))
            except Exception as e:
                logger.warning("processed_load_failed", error=str(e))

    def _save_processed(self) -> None:
        """Save processed video IDs."""
        processed_file = self.output_dir / "processed.json"
        with open(processed_file, "w") as f:
            json.dump(list(self.processed_videos), f)

    async def process_source(self, source: VideoSource) -> list[ExtractedContent]:
        """Process a video source."""
        results = []

        if source.platform == "youtube":
            results = await self._process_youtube(source)
        elif source.platform == "local":
            results = await self._process_local(source)

        for content in results:
            self.processed_videos.add(content.video_id)
            await self._save_content(content)

        self._save_processed()
        return results

    async def _process_youtube(self, source: VideoSource) -> list[ExtractedContent]:
        """Process YouTube video/channel."""
        results = []

        if source.video_id:
            # Single video
            content = await self._download_and_transcribe_youtube(source.video_id)
            if content:
                results.append(content)
        elif source.channel_id:
            # Channel - get recent videos
            video_ids = await self._get_channel_videos(source.channel_id)
            for vid in video_ids[:10]:  # Limit to 10 most recent
                if vid not in self.processed_videos:
                    content = await self._download_and_transcribe_youtube(vid)
                    if content:
                        results.append(content)

        return results

    async def _get_channel_videos(self, channel_id: str) -> list[str]:
        """Get video IDs from channel (placeholder)."""
        # In production, use YouTube Data API
        logger.info("getting_channel_videos", channel_id=channel_id)
        return []

    async def _download_and_transcribe_youtube(self, video_id: str) -> ExtractedContent | None:
        """Download and transcribe YouTube video."""
        try:
            # In production: yt-dlp + faster-whisper
            # For now, return mock content
            logger.info("processing_youtube_video", video_id=video_id)

            # Mock transcript extraction
            transcript = "Mock transcript for video " + video_id

            # Extract tickers
            tickers = self._extract_tickers(transcript)

            # Extract patterns
            patterns = self._extract_patterns(transcript)

            content = ExtractedContent(
                video_id=video_id,
                title=f"Ross Cameron Trade Recap {video_id}",
                transcript=transcript,
                segments=[{"start": 0, "end": 300, "text": transcript, "speaker": "Ross"}],
                key_moments=[
                    {"timestamp": 60, "type": "entry", "description": "Long AAPL breakout"},
                    {"timestamp": 180, "type": "exit", "description": "Scaled out at resistance"},
                ],
                tickers_mentioned=tickers,
                patterns_discussed=patterns,
                duration_seconds=600,
            )

            return content

        except Exception as e:
            logger.error("youtube_processing_failed", video_id=video_id, error=str(e))
            return None

    async def _process_local(self, source: VideoSource) -> list[ExtractedContent]:
        """Process local video file."""
        if not source.local_path:
            return []

        path = Path(source.local_path)
        if not path.exists():
            logger.warning("local_file_not_found", path=str(path))
            return []

        # In production: faster-whisper + pyannote
        logger.info("processing_local_video", path=str(path))

        video_id = path.stem
        if video_id in self.processed_videos:
            return []

        # Mock processing
        content = ExtractedContent(
            video_id=video_id,
            title=path.name,
            transcript="Local video transcript",
            segments=[],
            key_moments=[],
            tickers_mentioned=[],
            patterns_discussed=[],
            duration_seconds=300,
        )

        return [content]

    def _extract_tickers(self, text: str) -> list[str]:
        """Extract stock tickers from transcript."""
        # Common ticker pattern: 1-5 uppercase letters
        ticker_pattern = r"\b[A-Z]{1,5}\b"
        candidates = re.findall(ticker_pattern, text)

        # Filter common words
        common_words = {
            "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER",
            "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "HAS", "HIM", "HIS", "HOW",
            "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "TWO", "WHO", "BOY", "DID",
            "MAN", "PUT", "SAY", "SHE", "TOO", "USE", "WAY", "WIN", "YES",
            "IMO", "USA", "CEO", "IPO", "ETF", "SEC", "NYSE", "NASDAQ", "RSI",
            "MACD", "VWAP", "ATR", "ORB", "HOD", "LOD", "PM", "AM", "EST", "PST",
        }

        tickers = [t for t in candidates if t not in common_words and len(t) <= 5]
        return list(set(tickers))

    def _extract_patterns(self, text: str) -> list[str]:
        """Extract trading patterns from transcript."""
        patterns = []
        text_lower = text.lower()

        pattern_keywords = {
            "bull_flag": ["bull flag", "bullflag"],
            "flat_top_breakout": ["flat top", "flat top breakout"],
            "vwap_reclaim": ["vwap reclaim", "reclaimed vwap"],
            "opening_range_breakout": ["opening range", "orb", "opening range breakout"],
            "double_bottom": ["double bottom", "w bottom"],
            "cup_and_handle": ["cup and handle", "cup handle"],
            "head_and_shoulders": ["head and shoulders", "h&s"],
            "wedge": ["wedge", "rising wedge", "falling wedge"],
            "triangle": ["triangle", "ascending triangle", "descending triangle"],
            "gap_up": ["gap up", "gapped up"],
            "gap_down": ["gap down", "gapped down"],
        }

        for pattern, keywords in pattern_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    patterns.append(pattern)
                    break

        return list(set(patterns))

    async def _save_content(self, content: ExtractedContent) -> None:
        """Save extracted content to disk."""
        output_file = self.output_dir / f"{content.video_id}.json"
        with open(output_file, "w") as f:
            json.dump(content.__dict__, f, default=str)
        logger.info("content_saved", video_id=content.video_id)

    async def run_scheduled(self) -> list[ExtractedContent]:
        """Run scheduled processing of all sources."""
        all_results = []
        for source in self.config.sources:
            results = await self.process_source(source)
            all_results.extend(results)
        return all_results

    async def get_processed_videos(self) -> list[str]:
        """Get list of processed video IDs."""
        return list(self.processed_videos)


def create_video_pipeline(
    config: VideoPipelineConfig | dict[str, Any] | None = None,
) -> VideoPipeline:
    """Factory function to create video pipeline."""
    return RossCameronPipeline(config)
