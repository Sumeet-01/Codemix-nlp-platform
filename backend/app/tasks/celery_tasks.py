"""
Celery Tasks - Async Batch Processing
"""
import asyncio
import uuid
from typing import List

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="process_batch_analysis",
    max_retries=3,
    default_retry_delay=60,
)
def process_batch_analysis(
    self,
    job_id: str,
    texts: List[str],
    user_id: str,
) -> dict:
    """
    Celery task for processing batch text analysis.
    Runs ML inference on each text and stores results.
    """
    logger.info("Starting batch analysis", job_id=job_id, total=len(texts))

    results = []
    failed = 0

    # Create new event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        from app.services.ml_service import ml_service

        async def run_batch():
            nonlocal failed
            batch_results = []

            for i, text in enumerate(texts):
                try:
                    if not ml_service.is_loaded:
                        await ml_service.load_model()

                    result = await ml_service.predict(text)
                    batch_results.append({
                        "text": text[:200],
                        "success": True,
                        "sarcasm": {
                            "label": result["sarcasm_label"],
                            "confidence": round(result["sarcasm_score"], 4),
                        },
                        "misinformation": {
                            "label": result["misinformation_label"],
                            "confidence": round(result["misinformation_score"], 4),
                        },
                        "model_version": result["model_version"],
                        "processing_time_ms": result["processing_time_ms"],
                    })

                    # Update task progress
                    self.update_state(
                        state="PROGRESS",
                        meta={"current": i + 1, "total": len(texts), "failed": failed},
                    )
                except Exception as exc:
                    failed += 1
                    logger.error("Batch item failed", index=i, error=str(exc))
                    batch_results.append({
                        "text": text[:200],
                        "success": False,
                        "error": str(exc),
                    })

            return batch_results

        results = loop.run_until_complete(run_batch())

    except Exception as exc:
        logger.error("Batch job failed", job_id=job_id, exc_info=exc)
        raise self.retry(exc=exc)
    finally:
        loop.close()

    logger.info(
        "Batch analysis completed",
        job_id=job_id,
        total=len(texts),
        successful=len(texts) - failed,
        failed=failed,
    )

    return {
        "job_id": job_id,
        "status": "completed",
        "total": len(texts),
        "successful": len(texts) - failed,
        "failed": failed,
        "results": results,
    }
