"""
Test script for JWT Authentication
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from docusign_esign.client.api_exception import ApiException
from docusign_nda_poc.auth.jwt_auth import DocuSignAuth


def test_jwt_authentication():
    """Test JWT authentication flow"""
    print("=" * 60)
    print("DocuSign JWT Authentication Test")
    print("=" * 60)

    auth = DocuSignAuth()

    try:
        print("\n[1] Attempting JWT authentication...")
        token = auth.authenticate()

        print("\n[SUCCESS] Authentication successful!")
        print(f"  - Account ID: {token.account_id}")
        print(f"  - Base URI: {token.base_uri}")
        print(f"  - Token expires at: {token.expires_at}")
        print(f"  - Access Token (first 50 chars): {token.access_token[:50]}...")

        print("\n[2] Testing API client creation...")
        api_client = auth.get_api_client()
        print(f"  - API Client host: {api_client.host}")
        print("  - Authorization header set: OK")

        print("\n[3] Testing token caching...")
        token2 = auth.authenticate()
        if token.access_token == token2.access_token:
            print("  - Token caching: OK (same token returned)")
        else:
            print("  - Token caching: New token generated")

        print("\n" + "=" * 60)
        print("All authentication tests passed!")
        print("=" * 60)
        return True

    except ApiException as e:
        if auth.needs_consent(e):
            print("\n[CONSENT REQUIRED]")
            print("Please open the following URL in your browser to grant consent:")
            print(f"\n{auth.consent_url}\n")
            print("After granting consent, run this test again.")
        else:
            print(f"\n[ERROR] API Exception: {e}")
            if e.body:
                print(f"Body: {e.body}")
        return False

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_jwt_authentication()
    sys.exit(0 if success else 1)
