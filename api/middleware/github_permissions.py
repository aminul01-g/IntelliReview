from fastapi import Request, HTTPException, status, Depends
import httpx
from typing import Optional

from api.auth import get_current_user
from api.models.user import User
from api.auth.github_app import GitHubAppAuth

async def verify_github_repo_access(request: Request, user: User = Depends(get_current_user)):
    """
    Middleware / Dependency to handle 'user-to-server' requests.
    Ensures the AI agent only accesses repositories where both:
    1. The IntelliReview GitHub App is installed.
    2. The specific user has 'Write' or 'Admin' permissions.
    """
    
    owner = request.path_params.get("owner")
    repo = request.path_params.get("repo")
    
    if not owner or not repo:
        # Require 'owner' and 'repo' to be in the path for endpoints using this middleware
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository owner and name not provided in the request path."
        )

    try:
        app_jwt = GitHubAppAuth.generate_app_jwt()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration Error: {str(e)}"
        )
        
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    async with httpx.AsyncClient() as client:
        # 1. Check if App is installed on the repo
        repo_install_url = f"https://api.github.com/repos/{owner}/{repo}/installation"
        resp = await client.get(repo_install_url, headers=headers)
        
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IntelliReview GitHub App is not installed on this repository."
            )
            
        installation_data = resp.json()
        installation_id = installation_data.get("id")
        
        # 2. Get an installation access token
        installation_token = GitHubAppAuth.get_installation_access_token(str(installation_id))
        if not installation_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate installation token for the repository."
            )
            
        # 3. Check if the specific user has 'Write' or 'Admin' permissions
        # Assuming user.username resolves to their GitHub handle since we use GitHub Apps
        collab_headers = {
            "Authorization": f"token {installation_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        perm_url = f"https://api.github.com/repos/{owner}/{repo}/collaborators/{user.username}/permission"
        perm_resp = await client.get(perm_url, headers=collab_headers)
        
        if perm_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User {user.username} does not have access to this repository or user not found."
            )
            
        perm_data = perm_resp.json()
        permission = perm_data.get("permission")
        
        if permission not in ["admin", "write"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User requires 'Write' or 'Admin' permissions. Current permission: {permission}"
            )
            
    # Provide the token to downstream handlers safely
    request.state.github_installation_token = installation_token
    return True
