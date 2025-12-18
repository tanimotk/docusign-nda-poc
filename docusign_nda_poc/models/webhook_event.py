"""
DocuSign Webhook Event Models
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Any
import hashlib
import hmac
import base64


class WebhookEventType(str, Enum):
    """DocuSign Connect webhook event types"""

    ENVELOPE_SENT = "envelope-sent"
    ENVELOPE_DELIVERED = "envelope-delivered"
    ENVELOPE_COMPLETED = "envelope-completed"
    ENVELOPE_DECLINED = "envelope-declined"
    ENVELOPE_VOIDED = "envelope-voided"
    RECIPIENT_SENT = "recipient-sent"
    RECIPIENT_DELIVERED = "recipient-delivered"
    RECIPIENT_COMPLETED = "recipient-completed"
    RECIPIENT_DECLINED = "recipient-declined"


@dataclass
class RecipientInfo:
    """Recipient information from webhook"""

    recipient_id: str
    name: str
    email: str
    status: str
    signed_datetime: Optional[datetime] = None


@dataclass
class WebhookEvent:
    """
    DocuSign Connect webhook event.

    DocuSign sends XML by default, but can be configured to send JSON.
    This model handles JSON format.
    """

    event: str
    envelope_id: str
    status: str
    status_changed_datetime: Optional[datetime] = None
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    recipients: list[RecipientInfo] = None
    raw_data: Optional[dict] = None

    def __post_init__(self):
        if self.recipients is None:
            self.recipients = []

    @property
    def event_type(self) -> Optional[WebhookEventType]:
        """Get typed event type"""
        try:
            return WebhookEventType(self.event)
        except ValueError:
            return None

    @property
    def is_completed(self) -> bool:
        """Check if envelope is completed"""
        return self.status.lower() == "completed"

    @property
    def is_declined(self) -> bool:
        """Check if envelope is declined"""
        return self.status.lower() == "declined"

    @property
    def is_voided(self) -> bool:
        """Check if envelope is voided"""
        return self.status.lower() == "voided"

    @classmethod
    def from_json(cls, data: dict) -> "WebhookEvent":
        """
        Parse webhook event from JSON payload.

        DocuSign Connect can send different JSON structures.
        This handles the common envelope status change format.
        """
        # Handle nested structure
        envelope_data = data.get("data", data)
        envelope_summary = envelope_data.get("envelopeSummary", envelope_data)

        # Extract envelope info
        envelope_id = (
            envelope_summary.get("envelopeId")
            or data.get("envelopeId")
            or ""
        )
        status = (
            envelope_summary.get("status")
            or data.get("status")
            or ""
        )
        event = data.get("event", f"envelope-{status.lower()}")

        # Parse datetime
        status_changed_dt = None
        dt_str = envelope_summary.get("statusChangedDateTime") or data.get("statusChangedDateTime")
        if dt_str:
            try:
                status_changed_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Extract sender info
        sender = envelope_summary.get("sender", {})
        sender_email = sender.get("email")
        sender_name = sender.get("userName") or sender.get("name")

        # Extract recipients
        recipients = []
        recipients_data = envelope_summary.get("recipients", {})
        signers = recipients_data.get("signers", [])

        for signer in signers:
            signed_dt = None
            if signer.get("signedDateTime"):
                try:
                    signed_dt = datetime.fromisoformat(
                        signer["signedDateTime"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            recipients.append(
                RecipientInfo(
                    recipient_id=signer.get("recipientId", ""),
                    name=signer.get("name", ""),
                    email=signer.get("email", ""),
                    status=signer.get("status", ""),
                    signed_datetime=signed_dt,
                )
            )

        return cls(
            event=event,
            envelope_id=envelope_id,
            status=status,
            status_changed_datetime=status_changed_dt,
            sender_email=sender_email,
            sender_name=sender_name,
            recipients=recipients,
            raw_data=data,
        )


class WebhookSignatureVerifier:
    """
    Verify DocuSign webhook signatures using HMAC.

    DocuSign Connect can be configured to include HMAC signatures
    for webhook verification.
    """

    def __init__(self, hmac_key: str):
        """
        Initialize verifier with HMAC key.

        Args:
            hmac_key: The HMAC key configured in DocuSign Connect
        """
        self.hmac_key = hmac_key

    def verify(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Raw request body bytes
            signature: Value from X-DocuSign-Signature-1 header

        Returns:
            True if signature is valid
        """
        if not signature:
            return False

        # Compute HMAC-SHA256
        computed = hmac.new(
            self.hmac_key.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).digest()

        # Base64 encode
        computed_b64 = base64.b64encode(computed).decode("utf-8")

        # Compare
        return hmac.compare_digest(computed_b64, signature)
