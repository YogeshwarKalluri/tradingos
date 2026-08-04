"""TradingOS Main Entry Point."""

import asyncio
import signal
import sys
from pathlib import Path
import structlog

import click

from tradingos.core.config import get_config, reset_config
from tradingos.core.logging import setup_logging, get_logger
from tradingos.core.events import get_event_bus, set_event_bus
from tradingos.core.models import get_model_manager, set_model_manager
from tradingos.core.health import create_health_app

logger = get_logger(__name__)


class TradingOS:
    """Main TradingOS application."""
    
    def __init__(self, env: str = "development"):
        self.env = env
        self.config = None
        self.event_bus = None
        self.model_manager = None
        self.health_server = None
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize all components."""
        # Reset config for new environment
        reset_config()
        self.config = get_config(self.env)
        
        # Setup logging
        setup_logging(self.config.logging)
        logger.info("tradingos_initializing", env=self.env, version=self.config.app.version)
        
        # Initialize event bus
        self.event_bus = get_event_bus()
        await self.event_bus.start()
        
        # Initialize model manager
        self.model_manager = get_model_manager()
        self.model_manager.load_registry_yaml("config/models/registry.yaml")
        
        # Create health server app
        self.health_server = create_health_app(self.config.health)
        
        logger.info("tradingos_initialized")
    
    async def start_market_hours(self):
        """Start for market hours operation."""
        logger.info("starting_market_hours_mode")
        
        # Load market hours models
        await self.model_manager.load_market_hours_models()
        
        # Start health checks
        await self.model_manager.start_health_checks()
        
        self._running = True
        logger.info("market_hours_ready")
    
    async def start_after_hours(self):
        """Start for after-hours operation."""
        logger.info("starting_after_hours_mode")
        
        # Load after-hours models
        await self.model_manager.load_after_hours_models()
        
        self._running = True
        logger.info("after_hours_ready")
    
    async def run(self):
        """Run the main application loop."""
        if not self._running:
            raise RuntimeError("Must call start_market_hours() or start_after_hours() first")
        
        logger.info("tradingos_running")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        logger.info("tradingos_shutdown_requested")
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("tradingos_shutting_down")
        self._running = False
        
        # Stop health checks
        if self.model_manager:
            await self.model_manager.stop_health_checks()
        
        # Unload all models
        if self.model_manager:
            await self.model_manager.unload_all()
        
        # Stop event bus
        if self.event_bus:
            await self.event_bus.stop()
        
        self._shutdown_event.set()
        logger.info("tradingos_shutdown_complete")
    
    def signal_shutdown(self):
        """Signal shutdown from signal handler."""
        self._shutdown_event.set()


@click.group()
@click.option("--env", default="development", help="Environment (development/production)")
@click.pass_context
def cli(ctx, env):
    """TradingOS - Local AI-Powered Momentum Day Trading Platform."""
    ctx.ensure_object(dict)
    ctx.obj["env"] = env


@cli.command()
@click.pass_context
def start(ctx):
    """Start TradingOS in market hours mode."""
    env = ctx.obj["env"]
    app = TradingOS(env)
    
    async def run():
        await app.initialize()
        await app.start_market_hours()
        
        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, app.signal_shutdown)
        
        await app.run()
        await app.shutdown()
    
    asyncio.run(run())


@cli.command()
@click.pass_context
def after_hours(ctx):
    """Start TradingOS in after-hours mode (video processing, evaluation)."""
    env = ctx.obj["env"]
    app = TradingOS(env)
    
    async def run():
        await app.initialize()
        await app.start_after_hours()
        
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, app.signal_shutdown)
        
        await app.run()
        await app.shutdown()
    
    asyncio.run(run())


@cli.command()
@click.pass_context
def health(ctx):
    """Run health check server only."""
    env = ctx.obj["env"]
    reset_config()
    config = get_config(env)
    setup_logging(config.logging)
    
    import uvicorn
    health_app = create_health_app(config.health)
    uvicorn.run(health_app, host="0.0.0.0", port=config.health.port, log_level="warning")


@cli.command()
@click.pass_context
def migrate(ctx):
    """Run database migrations."""
    env = ctx.obj["env"]
    reset_config()
    config = get_config(env)
    setup_logging(config.logging)
    
    logger.info("running_migrations")
    # TODO: Implement migration runner
    logger.info("migrations_complete")


@cli.command()
@click.pass_context
def shell(ctx):
    """Start interactive shell with app context."""
    env = ctx.obj["env"]
    reset_config()
    config = get_config(env)
    setup_logging(config.logging)
    
    # Import common objects
    from tradingos.core.config import get_config as _get_config
    from tradingos.core.events import get_event_bus
    from tradingos.core.models import get_model_manager
    
    banner = f"""
TradingOS Interactive Shell
Environment: {env}
Config: {config.app.name} v{config.app.version}

Available:
  config     - get_config()
  events     - get_event_bus()
  models     - get_model_manager()
"""
    
    try:
        import IPython
        IPython.embed(banner1=banner, colors="Linux")
    except ImportError:
        import code
        code.interact(banner=banner, local=locals())


@cli.command()
@click.pass_context
def version(ctx):
    """Show version."""
    env = ctx.obj["env"]
    reset_config()
    config = get_config(env)
    click.echo(f"{config.app.name} v{config.app.version} ({env})")


if __name__ == "__main__":
    cli()