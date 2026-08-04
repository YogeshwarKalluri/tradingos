"""Vision Engine interfaces - stub for forward references."""

from dataclasses import dataclass
from typing import Any


@dataclass
class VisionOutput:
    """Output from vision model analysis."""
    patterns: list[str]
    confidence: float
    metadata: dict[str, Any]


class VisionEngine:
    """Base class for vision processing."""

    async def analyze(self, chart_tensor: Any) -> VisionOutput:
        raise NotImplementedError
