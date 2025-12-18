"""
DocuSign JWT Authentication
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from docusign_esign import ApiClient
from docusign_esign.client.api_exception import ApiException

from ..config import DocuSignConfig, config as default_config


@dataclass
class AuthToken:
    """Authentication token data"""

    access_token: str
    expires_at: datetime
    account_id: str
    base_uri: str

    @property
    def is_expired(self) -> bool:
        """Check if token is expired or about to expire"""
        return datetime.now() >= self.expires_at - timedelta(minutes=5)


class DocuSignAuth:
    """DocuSign JWT Authentication handler"""

    def __init__(self, config: Optional[DocuSignConfig] = None):
        self.config = config or default_config
        self._token: Optional[AuthToken] = None
        self._api_client: Optional[ApiClient] = None

    def _get_private_key(self) -> str:
        """Read private key from file"""
        with open(self.config.private_key_path, "r") as f:
            return f.read()

    def _create_api_client(self) -> ApiClient:
        """Create and configure API client"""
        api_client = ApiClient()
        api_client.set_base_path(self.config.authorization_server)
        api_client.set_oauth_host_name(self.config.authorization_server)
        return api_client

    def authenticate(self, force_refresh: bool = False) -> AuthToken:
        """
        Authenticate with DocuSign using JWT Grant.

        Args:
            force_refresh: Force token refresh even if current token is valid

        Returns:
            AuthToken with access token and account info

        Raises:
            ApiException: If authentication fails (may need consent)
        """
        # Return cached token if still valid
        if self._token and not self._token.is_expired and not force_refresh:
            return self._token

        api_client = self._create_api_client()
        private_key = self._get_private_key()

        # Request JWT token
        token_response = api_client.request_jwt_user_token(
            client_id=self.config.client_id,
            user_id=self.config.impersonated_user_id,
            oauth_host_name=self.config.authorization_server,
            private_key_bytes=private_key,
            expires_in=3600,
            scopes=list(self.config.scopes),
        )

        # Get user info to retrieve account_id and base_uri
        user_info = api_client.get_user_info(token_response.access_token)
        accounts = user_info.get_accounts()

        if not accounts:
            raise ValueError("No accounts found for this user")

        # Use the first (default) account
        account = accounts[0]

        self._token = AuthToken(
            access_token=token_response.access_token,
            expires_at=datetime.now() + timedelta(seconds=3600),
            account_id=account.account_id,
            base_uri=account.base_uri + "/restapi",
        )

        return self._token

    def get_api_client(self) -> ApiClient:
        """
        Get configured API client with valid access token.

        Returns:
            ApiClient configured with authorization header
        """
        token = self.authenticate()

        api_client = ApiClient()
        api_client.host = token.base_uri
        api_client.set_default_header(
            header_name="Authorization", header_value=f"Bearer {token.access_token}"
        )

        return api_client

    def needs_consent(self, exception: ApiException) -> bool:
        """Check if exception indicates consent is required"""
        if exception.body:
            body = (
                exception.body.decode("utf8")
                if isinstance(exception.body, bytes)
                else exception.body
            )
            return "consent_required" in body
        return False

    @property
    def consent_url(self) -> str:
        """Get URL for granting consent"""
        return self.config.consent_url
