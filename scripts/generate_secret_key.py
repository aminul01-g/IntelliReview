"""Generate a secure secret key."""

import secrets

def generate_secret_key(length: int = 50) -> str:
    """Generate a secure random secret key."""
    return secrets.token_urlsafe(length)

if __name__ == "__main__":
    key = generate_secret_key()
    print("Generated Secret Key:")
    print(key)
    print("\nAdd this to your .env file:")
    print(f"SECRET_KEY={key}")

