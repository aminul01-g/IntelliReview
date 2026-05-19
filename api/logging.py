import logging
import structlog
from config.settings import settings

def setup_logging():
    """
    Configures structured JSON logging for production.
    Ensures all logs include request IDs and are machine-readable.
    """
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )

    # Silence noisy loggers that don't add value in normal operation
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
    # Suppress optional dependency warnings (e.g. sarif_om plugin)
    logging.getLogger("sarif").setLevel(logging.ERROR)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger()
    logger.info("Structured logging initialized", debug=settings.DEBUG)
    return logger
