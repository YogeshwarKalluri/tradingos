"""Chart Engine - GPU-accelerated chart rendering using Numba/CUDA."""


import numpy as np
from numba import cuda

from tradingos.core.logging import get_logger
from tradingos.modules.charts.interfaces import ChartRenderer, ChartTensor

logger = get_logger(__name__)


class GPUChartRenderer(ChartRenderer):
    """GPU-accelerated chart renderer for RTX 5080.

    Renders OHLCV data into normalized tensors for vision model input.
    Target: <30ms per ticker on RTX 5080.
    """

    def __init__(self, output_shape: tuple[int, int] = (224, 224)):
        self.output_shape = output_shape
        self.height, self.width = output_shape
        self._check_cuda()

    def _check_cuda(self) -> None:
        """Verify CUDA is available."""
        try:
            cuda.detect()
            logger.info("cuda_available", device=cuda.get_current_device().name)
        except Exception as e:
            logger.warning("cuda_not_available", error=str(e))
            raise RuntimeError(
                "CUDA not available - GPU chart renderer requires NVIDIA GPU"
            ) from e

    @staticmethod
    @cuda.jit
    def _render_ohlcv_kernel(
        opens, highs, lows, closes, volumes,
        output, height, width, candle_width, gap
    ):
        """CUDA kernel to render OHLCV candles."""
        tx = cuda.threadIdx.x + cuda.blockIdx.x * cuda.blockDim.x
        ty = cuda.threadIdx.y + cuda.blockIdx.y * cuda.blockDim.y

        if tx >= width or ty >= height:
            return

        n_candles = opens.shape[0]
        if n_candles == 0:
            return

        # Map x coordinate to candle index
        candle_idx = min(tx // (candle_width + gap), n_candles - 1)
        if candle_idx < 0:
            return

        # Get OHLCV values
        o = opens[candle_idx]
        h = highs[candle_idx]
        low_val = lows[candle_idx]
        c = closes[candle_idx]

        # Normalize to 0-1 range for this candle
        price_range = h - low_val
        if price_range <= 0:
            return

        # Candle body position
        body_top = max(o, c)
        body_bottom = min(o, c)
        body_top_norm = (body_top - low_val) / price_range
        body_bottom_norm = (body_bottom - low_val) / price_range
        wick_top_norm = (h - low_val) / price_range
        wick_bottom_norm = 0.0

        # Y coordinate in chart (inverted: 0 at top)
        y_norm = 1.0 - ty / height

        # Candle x position
        candle_x_start = candle_idx * (candle_width + gap)
        candle_x_end = candle_x_start + candle_width

        # Render candle
        if candle_x_start <= tx < candle_x_end:
            # Wick
            if wick_bottom_norm <= y_norm <= wick_top_norm:
                output[ty, tx, 0] = 0.8  # Gray wick
                output[ty, tx, 1] = 0.8
                output[ty, tx, 2] = 0.8
            # Body
            elif body_bottom_norm <= y_norm <= body_top_norm:
                if c >= o:  # Green/up
                    output[ty, tx, 0] = 0.0
                    output[ty, tx, 1] = 0.7
                    output[ty, tx, 2] = 0.0
                else:  # Red/down
                    output[ty, tx, 0] = 0.7
                    output[ty, tx, 1] = 0.0
                    output[ty, tx, 2] = 0.0

    async def render(self, ticker: str, bars: dict[str, list]) -> ChartTensor:
        """Render multi-timeframe charts to tensor."""
        timeframes = {}

        for tf, tf_bars in bars.items():
            if not tf_bars:
                continue

            # Convert to numpy arrays
            n = len(tf_bars)
            opens = np.array([b['open'] for b in tf_bars], dtype=np.float32)
            highs = np.array([b['high'] for b in tf_bars], dtype=np.float32)
            lows = np.array([b['low'] for b in tf_bars], dtype=np.float32)
            closes = np.array([b['close'] for b in tf_bars], dtype=np.float32)
            volumes = np.array([b.get('volume', 0) for b in tf_bars], dtype=np.float32)

            # Normalize volume
            if volumes.max() > 0:
                volumes = volumes / volumes.max()

            # Allocate output tensor on GPU
            output = cuda.device_array((self.height, self.width, 3), dtype=np.float32)

            # Launch kernel
            threads_per_block = (16, 16)
            blocks_per_grid = (
                (self.width + threads_per_block[0] - 1) // threads_per_block[0],
                (self.height + threads_per_block[1] - 1) // threads_per_block[1]
            )

            candle_width = max(1, self.width // max(n, 1) - 1)
            gap = 1

            self._render_ohlcv_kernel[blocks_per_grid, threads_per_block](
                opens, highs, lows, closes, volumes,
                output, self.height, self.width, candle_width, gap
            )

            # Copy back to host
            tensor = output.copy_to_host()
            timeframes[tf] = tensor

        return ChartTensor(
            ticker=ticker,
            timeframes=timeframes,
            metadata={"shape": self.output_shape, "renderer": "gpu"}
        )


class CPUChartRenderer(ChartRenderer):
    """CPU fallback chart renderer using NumPy."""

    def __init__(self, output_shape: tuple[int, int] = (224, 224)):
        self.output_shape = output_shape
        self.height, self.width = output_shape

    async def render(self, ticker: str, bars: dict[str, list]) -> ChartTensor:
        """Render charts on CPU."""
        timeframes = {}

        for tf, tf_bars in bars.items():
            if not tf_bars:
                continue

            n = len(tf_bars)
            tensor = np.zeros((self.height, self.width, 3), dtype=np.float32)

            opens = np.array([b['open'] for b in tf_bars])
            highs = np.array([b['high'] for b in tf_bars])
            lows = np.array([b['low'] for b in tf_bars])
            closes = np.array([b['close'] for b in tf_bars])

            candle_width = max(1, self.width // max(n, 1) - 1)
            gap = 1

            for i in range(n):
                o, h, low_val, c = opens[i], highs[i], lows[i], closes[i]
                price_range = h - low_val
                if price_range <= 0:
                    continue

                body_top = max(o, c)
                body_bottom = min(o, c)
                body_top_norm = (body_top - low_val) / price_range
                body_bottom_norm = (body_bottom - low_val) / price_range
                wick_top_norm = 1.0
                wick_bottom_norm = 0.0

                candle_x_start = i * (candle_width + gap)
                candle_x_end = min(candle_x_start + candle_width, self.width)

                for x in range(candle_x_start, candle_x_end):
                    for y in range(self.height):
                        y_norm = 1.0 - y / self.height

                        # Wick
                        if wick_bottom_norm <= y_norm <= wick_top_norm:
                            tensor[y, x] = [0.8, 0.8, 0.8]
                        # Body
                        elif body_bottom_norm <= y_norm <= body_top_norm:
                            if c >= o:
                                tensor[y, x] = [0.0, 0.7, 0.0]
                            else:
                                tensor[y, x] = [0.7, 0.0, 0.0]

            timeframes[tf] = tensor

        return ChartTensor(
            ticker=ticker,
            timeframes=timeframes,
            metadata={"shape": self.output_shape, "renderer": "cpu"}
        )


def create_chart_renderer(
    use_gpu: bool = True,
    output_shape: tuple[int, int] = (224, 224),
) -> ChartRenderer:
    """Factory function to create chart renderer."""
    if use_gpu:
        try:
            return GPUChartRenderer(output_shape)
        except Exception as e:
            logger.warning("gpu_renderer_failed_fallback", error=str(e))
            return CPUChartRenderer(output_shape)
    return CPUChartRenderer(output_shape)
