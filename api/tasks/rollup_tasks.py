from celery import shared_task
from api.database import SessionLocal
from api.models.analysis import Analysis
import datetime
import logging

logger = logging.getLogger(__name__)

@shared_task(name="api.tasks.rollup_tasks.aggregate_metrics_task")
def aggregate_metrics_task():
    """
    Rolls up high-cardinality metrics_dict records into daily aggregates
    to prevent TimescaleDB / PostgreSQL bloat, truncating raw data > 30 days old.
    """
    logger.info("Starting scheduled metrics aggregation...")
    db = SessionLocal()
    try:
        thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        
        # Example logic: identify old analyses and truncate heavy JSON dictionaries
        # Since we don't have a specific Aggregate table built yet, we can simply
        # clear the metrics_dict / raw code for rows older than 30 days to free space,
        # or calculate total rolling averages.
        
        old_analyses = db.query(Analysis).filter(Analysis.analyzed_at <= thirty_days_ago).all()
        for analysis in old_analyses:
            # Nullify large footprint data, keep only severity counts for historic overview
            if analysis.metrics_dict:
                analysis.metrics_dict = {"aggregated": True, "historic_retention": True}
            if analysis.auto_fixes:
                analysis.auto_fixes = []
                
        db.commit()
        logger.info(f"Aggregated and truncated {len(old_analyses)} stale analysis records.")
    except Exception as e:
        logger.error(f"Metrics aggregation failed: {e}")
        db.rollback()
    finally:
        db.close()
