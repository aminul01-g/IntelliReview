import logging
import structlog
from config.settings import settings

def setup_logging():
    """
    Configures structured JSON logging for production.
    Ensures all logs include request IDs and are machine-readable.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(time_utc=True),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Setup standard logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )

    logger = structlog.get_logger()
    logger.info("Structured logging initialized", environment=settings.ENV)
    return logger
