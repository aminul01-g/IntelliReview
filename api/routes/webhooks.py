from fastapi import APIRouter, Request, Header, HTTPException, status
import hmac
import hashlib
import os
from typing import Optional

router = APIRouter()

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """Handle GitHub PR webhooks."""
    payload = await request.body()
    
    # Verify signature if secret is set
    if GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature missing")
        
        hash_object = hmac.new(
            GITHUB_WEBHOOK_SECRET.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        
        if not hmac.compare_digest(expected_signature, x_hub_signature_256):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    data = await request.json()
    event = request.headers.get("X-GitHub-Event")
    
    if event == "pull_request":
        action = data.get("action")
        if action in ["opened", "synchronize"]:
            pull_request = data.get("pull_request")
            repo = data.get("repository")
            pr_number = pull_request.get("number")
            repo_name = repo.get("full_name")
            
            print(f"Received PR {action} event for {repo_name} PR #{pr_number}")
            
            # Simulate automated PR commenting
            comment_body = f"🚀 **IntelliReview Analysis** for PR #{pr_number}\n\n" \
                           f"Analysis triggered for repository: {repo_name}\n" \
                           f"Results will be available at: http://localhost:3000/metrics\n\n" \
                           f"Found 0 critical, 0 high severity issues."
            
            print(f"Simulating PR Comment on {repo_name}#{pr_number}:\n{comment_body}")
            
            return {
                "message": "PR analysis triggered and comment simulated",
                "pr": pr_number,
                "repo": repo_name
            }
            
    return {"message": "Event ignored"}
