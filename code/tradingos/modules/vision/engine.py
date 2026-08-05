"""Vision Engine - Chart pattern recognition using ONNX/TensorRT."""

from typing import Any

import numpy as np

from tradingos.core.logging import get_logger
from tradingos.modules.vision.interfaces import VisionEngine, VisionOutput

logger = get_logger(__name__)

# Pattern classes the vision model can detect
PATTERN_CLASSES = [
    "bull_flag",
    "bear_flag",
    "flat_top_breakout",
    "vwap_reclaim",
    "opening_range_breakout",
    "vwap_breakdown",
    "double_bottom",
    "double_top",
    "head_and_shoulders",
    "cup_and_handle",
    "ascending_triangle",
    "descending_triangle",
    "symmetrical_triangle",
    "wedge_up",
    "wedge_down",
    "channel_up",
    "channel_down",
    "support_test",
    "resistance_test",
    "gap_up",
    "gap_down",
    "no_pattern",
]


class ONNXVisionEngine(VisionEngine):
    """ONNX/TensorRT optimized vision engine for chart pattern detection."""

    def __init__(
        self,
        model_path: str = "models/vision/pattern_detector.onnx",
        input_shape: tuple[int, int] = (224, 224),
        confidence_threshold: float = 0.65,
        nms_iou_threshold: float = 0.45,
        use_tensorrt: bool = True,
    ):
        self.model_path = model_path
        self.input_shape = input_shape
        self.confidence_threshold = confidence_threshold
        self.nms_iou_threshold = nms_iou_threshold
        self.use_tensorrt = use_tensorrt
        self.session = None
        self._load_model()

    def _load_model(self) -> None:
        """Load ONNX model with TensorRT optimization."""
        try:
            import onnxruntime as ort

            providers = ["CPUExecutionProvider"]
            if self.use_tensorrt:
                providers.insert(0, "TensorrtExecutionProvider")
                providers.insert(1, "CUDAExecutionProvider")

            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=sess_options,
                providers=providers,
            )

            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [o.name for o in self.session.get_outputs()]

            logger.info(
                "vision_model_loaded",
                path=self.model_path,
                providers=providers,
                input_shape=self.input_shape,
            )
        except Exception as e:
            logger.warning("vision_model_load_failed", error=str(e))
            self.session = None

    def _preprocess(self, chart_tensor: np.ndarray) -> np.ndarray:
        """Preprocess chart tensor for model input."""
        # Ensure correct shape and normalization
        if chart_tensor.shape[-1] == 3:
            # HWC to CHW
            tensor = np.transpose(chart_tensor, (2, 0, 1))
        else:
            tensor = chart_tensor

        # Normalize to [0, 1]
        if tensor.max() > 1.0:
            tensor = tensor.astype(np.float32) / 255.0
        else:
            tensor = tensor.astype(np.float32)

        # Add batch dimension
        tensor = np.expand_dims(tensor, axis=0)

        return tensor

    async def analyze(self, chart_tensor: Any) -> VisionOutput:
        """Analyze chart tensor for patterns."""
        if self.session is None:
            return VisionOutput(
                patterns=["no_model"],
                confidence=0.0,
                metadata={"error": "Model not loaded"},
            )

        try:
            # Handle multi-timeframe input - use highest resolution
            if isinstance(chart_tensor, dict):
                # Prefer 1m timeframe
                tensor = (
                    chart_tensor.get("1m")
                    or chart_tensor.get("5m")
                    or next(iter(chart_tensor.values()))
                )
            else:
                tensor = chart_tensor

            # Preprocess
            input_tensor = self._preprocess(tensor)

            # Run inference
            outputs = self.session.run(self.output_names, {self.input_name: input_tensor})

            # Parse outputs (assuming classification logits)
            logits = outputs[0][0]  # Batch dim removed
            probs = self._softmax(logits)

            # Get top predictions above threshold
            detected_patterns = []
            for i, prob in enumerate(probs):
                if prob >= self.confidence_threshold and i < len(PATTERN_CLASSES):
                    detected_patterns.append({
                        "pattern": PATTERN_CLASSES[i],
                        "confidence": float(prob),
                    })

            # Sort by confidence
            detected_patterns.sort(key=lambda x: x["confidence"], reverse=True)

            patterns = [p["pattern"] for p in detected_patterns]
            confidence = detected_patterns[0]["confidence"] if detected_patterns else 0.0

            return VisionOutput(
                patterns=patterns,
                confidence=confidence,
                metadata={
                    "all_predictions": detected_patterns[:5],
                    "input_shape": input_tensor.shape,
                },
            )
        except Exception as e:
            logger.error("vision_inference_error", error=str(e))
            return VisionOutput(
                patterns=["error"],
                confidence=0.0,
                metadata={"error": str(e)},
            )

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        """Numerically stable softmax."""
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()


class MockVisionEngine(VisionEngine):
    """Mock vision engine for development/testing."""

    def __init__(self, **kwargs):
        self.patterns = ["bull_flag", "vwap_reclaim", "opening_range_breakout"]
        logger.info("mock_vision_engine_initialized")

    async def analyze(self, chart_tensor: Any) -> VisionOutput:
        """Return mock analysis."""
        import random

        # Simulate realistic pattern detection
        num_patterns = random.randint(0, 2)
        selected = random.sample(self.patterns, k=num_patterns) if num_patterns > 0 else []

        return VisionOutput(
            patterns=selected,
            confidence=random.uniform(0.7, 0.95) if selected else 0.0,
            metadata={"mock": True, "source": "mock_engine"},
        )


def create_vision_engine(use_mock: bool = True, **kwargs) -> VisionEngine:
    """Factory function to create vision engine."""
    if use_mock:
        return MockVisionEngine(**kwargs)
    return ONNXVisionEngine(**kwargs)
