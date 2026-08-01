"""
auth.py — Auth0 authentication for the Nexora backend.

The frontend logs users in via Auth0's Universal Login (redirect flow) using
the SPA JS SDK. Every authenticated request from the browser then carries an
`Authorization: Bearer <token>` header. This module verifies that token
against your Auth0 tenant's public keys (JWKS) — it never trusts a client-
supplied "is_guest" flag; guest status is derived from whether a valid,
signed, unexpired token was presented.

Two verification modes, chosen automatically based on what you've configured:

1. AUTH0_AUDIENCE set (recommended — you created a custom API in the Auth0
   dashboard under Applications > APIs, and the frontend requests tokens for
   that audience). The token is a real access-token JWT scoped to your API.
2. AUTH0_AUDIENCE not set. The frontend instead sends the ID token, which is
   always a JWT (access tokens without a configured API audience are opaque
   and can't be verified locally). Still cryptographically verified against
   Auth0's JWKS and checked against your Client ID as the audience.

If AUTH0_DOMAIN isn't configured at all, verify_token() always returns None
— every request is treated as a guest, same as before Auth0 was wired in.
"""

import os
import jwt
from jwt import PyJWKClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "").strip()
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "").strip()
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "").strip()

_jwk_client = None
if AUTH0_DOMAIN:
    try:
        _jwk_client = PyJWKClient(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
    except Exception as e:
        print(f"[auth] Failed to initialize JWKS client: {e}")


def is_configured() -> bool:
    return _jwk_client is not None


def verify_token(token: str):
    """Return decoded claims dict for a valid Auth0 token, or None. Never raises."""
    if not token or not _jwk_client:
        return None
    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(token)
        issuer = f"https://{AUTH0_DOMAIN}/"
        if AUTH0_AUDIENCE:
            claims = jwt.decode(token, signing_key.key, algorithms=["RS256"],
                                 audience=AUTH0_AUDIENCE, issuer=issuer)
        elif AUTH0_CLIENT_ID:
            claims = jwt.decode(token, signing_key.key, algorithms=["RS256"],
                                 audience=AUTH0_CLIENT_ID, issuer=issuer)
        else:
            claims = jwt.decode(token, signing_key.key, algorithms=["RS256"],
                                 issuer=issuer, options={"verify_aud": False})
        return claims
    except Exception as e:
        print(f"[auth] Token verification failed: {e}")
        return None


def user_from_claims(claims: dict):
    if not claims:
        return None
    return {
        "sub": claims.get("sub"),
        "name": claims.get("name") or claims.get("nickname") or claims.get("email"),
        "email": claims.get("email"),
        "picture": claims.get("picture"),
    }
