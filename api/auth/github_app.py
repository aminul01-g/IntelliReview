import time
import requests
from jose import jwt
from typing import Optional
import os

# Using ENV vars for GitHub App credentials
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
# This should be the raw string with '\n' or loaded from a file path
GITHUB_APP_PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY")

class GitHubAppAuth:
    """Handles GitHub App authentication lifecycle."""
    
    @staticmethod
    def generate_app_jwt() -> str:
        """
        Generate a JWT for the GitHub App.
        The JWT is valid for a maximum of 10 minutes.
        """
        if not GITHUB_APP_ID or not GITHUB_APP_PRIVATE_KEY:
            raise ValueError("GitHub App credentials (APP_ID or PRIVATE_KEY) are not configured.")
        
        now = int(time.time())
        payload = {
            # issued at time, 60 seconds in the past to allow for clock drift
            "iat": now - 60,
            # JWT expiration time (10 minute maximum)
            "exp": now + (10 * 60),
            # GitHub App's identifier
            "iss": GITHUB_APP_ID
        }
        
        # Replace explicit literal escaped newlines if passed via some env managers
        private_key = GITHUB_APP_PRIVATE_KEY.replace('\\n', '\n')
        
        encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
        return encoded_jwt

    @staticmethod
    def get_installation_access_token(installation_id: str) -> Optional[str]:
        """
        Exchange the JWT for an installation-level access token.
        Requires the target installation ID where the App is active/installed.
        """
        try:
            app_jwt = GitHubAppAuth.generate_app_jwt()
        except Exception as e:
            print(f"JWT Generation Error: {str(e)}")
            return None
            
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        resp = requests.post(url, headers=headers)
        
        if resp.status_code == 201:
            data = resp.json()
            return data.get("token")
        else:
            print(f"Failed to get installation token for {installation_id}: {resp.status_code} {resp.text}")
            return None

    @staticmethod
    def get_user_installation_repo_permissions(user_token: str, owner: str, repo: str, username: str) -> dict:
        """
        Get the specific user permissions on a repository to verify write access.
        Used primarily by the middleware.
        """
        headers = {
            "Authorization": f"token {user_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"https://api.github.com/repos/{owner}/{repo}/collaborators/{username}/permission"
        resp = requests.get(url, headers=headers)
        
        if resp.status_code == 200:
            return resp.json()
        return {}
