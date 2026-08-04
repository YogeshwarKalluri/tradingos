"""TradingOS Health & Metrics Endpoints."""

from typing import Optional
from fastapi import FastAPI, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import structlog

from tradingos.core.config import get_config, HealthConfig
from tradingos.core.models import get_model_manager
from tradingos.core.events import get_event_bus

logger = structlog.get_logger(__name__)

# Prometheus metrics
EVENT_COUNTER = Counter("tradingos_events_total", "Total events processed", ["event_type"])
EVENT_LATENCY = Histogram("tradingos_event_latency_ms", "Event processing latency", ["event_type"])
PIPELINE_LATENCY = Histogram("tradingos_pipeline_latency_ms", "Full pipeline latency")
VRAM_USED = Gauge("tradingos_vram_used_mb", "VRAM used in MB")
VRAM_BUDGET = Gauge("tradingos_vram_budget_mb", "VRAM budget in MB")
MODELS_LOADED = Gauge("tradingos_models_loaded", "Number of models loaded")
ACTIVE_CANDIDATES = Gauge("tradingos_active_candidates", "Active candidates in pipeline")
DAILY_PNL = Gauge("tradingos_daily_pnl_usd", "Daily P&L in USD")
OPEN_POSITIONS = Gauge("tradingos_open_positions", "Number of open positions")


class HealthServer:
    """Health check and metrics HTTP server."""
    
    def __init__(self, config: Optional[HealthConfig] = None):
        self.config = config or get_config().health
        self.app = FastAPI(title="TradingOS Health", lifespan=self._lifespan)
        self._setup_routes()
    
    async def _lifespan(self, app: FastAPI):
        """Application lifespan manager."""
        logger.info("health_server_starting")
        yield
        logger.info("health_server_stopping")
    
    def _setup_routes(self):
        """Setup HTTP routes."""
        
        @self.app.get(self.config.path)
        async def health_check():
            """Health check endpoint."""
            model_manager = get_model_manager()
            event_bus = get_event_bus()
            
            vram = model_manager.get_vram_usage()
            event_stats = event_bus.get_stats()
            
            # Determine health status
            healthy = True
            issues = []
            
            # Check VRAM
            if vram["used_mb"] > self.config.vram_budget_mb * 0.95:
                healthy = False
                issues.append("VRAM near capacity")
            
            # Check model health
            for name in model_manager._loaded_models:
                model = model_manager._loaded_models[name]
                if not model.health_check():
                    healthy = False
                    issues.append(f"Model {name} unhealthy")
            
            return {
                "status": "healthy" if healthy else "degraded",
                "issues": issues,
                "vram": vram,
                "models_loaded": len(model_manager._loaded_models),
                "event_stats": event_stats,
                "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            }
        
        @self.app.get(self.config.metrics_path)
        async def metrics():
            """Prometheus metrics endpoint."""
            # Update dynamic metrics
            model_manager = get_model_manager()
            vram = model_manager.get_vram_usage()
            VRAM_USED.set(vram["used_mb"])
            VRAM_BUDGET.set(vram["budget_mb"])
            MODELS_LOADED.set(len(model_manager._loaded_models))
            
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        
        @self.app.get("/models")
        async def models_status():
            """Model status endpoint."""
            model_manager = get_model_manager()
            return model_manager.get_stats()
        
        @self.app.get("/events")
        async def events_status():
            """Event bus status endpoint."""
            event_bus = get_event_bus()
            return event_bus.get_stats()


def create_health_app(config: Optional[HealthConfig] = None) -> FastAPI:
    """Create health check FastAPI app."""
    server = HealthServer(config)
    return server.app


async def run_health_server(config: Optional[HealthConfig] = None):
    """Run health server standalone."""
    import uvicorn
    config = config or get_config().health
    app = create_health_app(config)
    server_config = uvicorn.Config(app, host="0.0.0.0", port=config.port, log_level="warning")
    server = uvicorn.Server(server_config)
    await server.serve()