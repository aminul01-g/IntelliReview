"""
Webhooks Routes for IntelliReview.
Handles incoming events from GitHub/GitLab to trigger automated AI code reviews.
"""

import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from api.database import get_db
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

def verify_github_signature(payload: bytes, signature: str) -> bool:
    """
    Verify that the webhook request was sent by GitHub.
    Uses the GITHUB_WEBHOOK_SECRET from environment variables.
    """
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured. Skipping signature verification.")
        return True

    secret = settings.GITHUB_WEBHOOK_SECRET.encode()
    mac = hmac.new(secret, msg=payload, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + mac.hexdigest()

    return hmac.compare_digest(expected_signature, signature)

@router.post("/github")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    GitHub Webhook endpoint.
    Processes 'pull_request' events to trigger an automated AI audit.
    """
    # 1. Verify Signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub signature missing"
        )

    body = await request.body()
    if not verify_github_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub signature"
        )

    # 2. Parse Event
    event_type = request.headers.get("X-GitHub-Event")
    if event_type != "pull_request":
        return {"message": f"Event {event_type} ignored."}

    payload = await request.json()

    # We only care about 'opened' and 'synchronize' (new commits)
    action = payload.get("action")
    if action not in ["opened", "synchronize"]:
        return {"message": f"Action {action} ignored."}

    # 3. Extract PR Data
    pr_data = {
        "repository": payload.get("repository", {}).get("full_name"),
        "pr_number": payload.get("number"),
        "commit_sha": payload.get("pull_request", {}).get("head", {}).get("sha"),
        "diff_url": payload.get("pull_request", {}).get("diff_url"),
        "user": payload.get("sender", {}).get("login"),
    }

    logger.info(f"Triggering AI audit for PR #{pr_data['pr_number']} in {pr_data['repository']}")

    # 4. Dispatch to Celery
    try:
        from api.tasks.analysis_tasks import analyze_pr_task
        task = analyze_pr_task.apply_async(args=[pr_data])
        return {"status": "queued", "task_id": task.id, "message": "AI Review triggered."}
    except Exception as e:
        logger.error(f"Failed to enqueue PR analysis: {e}")
        # Fallback to BackgroundTasks if Celery is down
        background_tasks.add_task(handle_pr_fallback, pr_data)
        return {"status": "processing_local", "message": "AI Review queued locally."}

async def handle_pr_fallback(pr_data: dict):
    """Fallback local processing for PR webhooks if Celery is unavailable."""
    logger.info(f"Running fallback local analysis for PR #{pr_data['pr_number']}")
    # In a real implementation, this would call the analyzer engine directly
    pass
