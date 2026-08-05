"""Dashboard module - HTMX + WebSocket real-time UI."""


from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from tradingos.core.logging import get_logger

logger = get_logger(__name__)


class Dashboard:
    """HTMX dashboard with WebSocket real-time updates."""

    def __init__(self, app: FastAPI):
        self.app = app
        # Use absolute path for templates (project root / templates)
        from pathlib import Path
        template_dir = Path(__file__).parent.parent.parent.parent.parent / "templates"
        self.templates = Jinja2Templates(directory=str(template_dir))
        self.active_connections: set[WebSocket] = set()
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            # Render template directly to avoid Jinja2 cache issue
            template = self.templates.env.get_template("index.html")
            content = template.render(request=request)
            return HTMLResponse(content=content)

        @self.app.websocket("/ws")
        async def websocket_endpoint(ws: WebSocket):
            await ws.accept()
            self.active_connections.add(ws)
            try:
                while True:
                    await ws.receive_text()
            except WebSocketDisconnect:
                self.active_connections.discard(ws)

        @self.app.get("/health")
        async def health():
            return {"status": "ok", "connections": len(self.active_connections)}

    async def broadcast(self, event: dict) -> None:
        """Broadcast event to all connected clients."""
        disconnected = set()
        for ws in self.active_connections:
            try:
                await ws.send_json(event)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            self.active_connections.discard(ws)


def create_dashboard(app: FastAPI) -> Dashboard:
    """Factory function to create dashboard."""
    return Dashboard(app)
