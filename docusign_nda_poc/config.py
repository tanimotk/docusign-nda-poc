"""
DocuSign NDA POC - Configuration
"""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocuSignConfig:
    """DocuSign API configuration"""

    # Integration Key (Client ID)
    client_id: str = "3bb3d9b1-b1ab-429c-97d3-1ecc327468cc"

    # User ID for impersonation
    impersonated_user_id: str = "979fdc12-75c6-4fea-9c0f-310a0a00d19a"

    # RSA Private Key file path
    private_key_path: Path = Path(__file__).parent.parent / "app" / "private.key"

    # Authorization server (demo environment)
    authorization_server: str = "account-d.docusign.com"

    # API base URL (demo environment)
    api_base_url: str = "https://demo.docusign.net/restapi"

    # OAuth scopes
    scopes: tuple = ("signature", "impersonation")

    # Token expiration buffer (seconds)
    token_expiry_buffer: int = 300

    @property
    def consent_url(self) -> str:
        """Generate consent URL for initial authorization"""
        scopes = "+".join(self.scopes)
        redirect_uri = "https://developers.docusign.com/platform/auth/consent"
        return (
            f"https://{self.authorization_server}/oauth/auth?"
            f"response_type=code&scope={scopes}&"
            f"client_id={self.client_id}&redirect_uri={redirect_uri}"
        )


# Default configuration instance
config = DocuSignConfig()
