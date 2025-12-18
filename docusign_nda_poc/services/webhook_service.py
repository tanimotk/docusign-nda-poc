"""
DocuSign Webhook Service

Handles incoming webhook events from DocuSign Connect.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable, Awaitable
import logging

from ..models.webhook_event import WebhookEvent, WebhookEventType, WebhookSignatureVerifier
from ..auth.jwt_auth import DocuSignAuth
from .envelope_service import EnvelopeService

logger = logging.getLogger(__name__)


@dataclass
class WebhookResult:
    """Result of webhook processing"""

    success: bool
    envelope_id: str
    event_type: str
    message: str
    signed_pdf_path: Optional[str] = None
    signer_email: Optional[str] = None
    signer_name: Optional[str] = None


class WebhookService:
    """
    Service for handling DocuSign Connect webhooks.

    Processes envelope status change events and triggers
    appropriate actions (e.g., download signed PDF, update NDA status).
    """

    def __init__(
        self,
        auth: Optional[DocuSignAuth] = None,
        hmac_key: Optional[str] = None,
        on_completed: Optional[Callable[[WebhookEvent, bytes], Awaitable[None]]] = None,
        on_declined: Optional[Callable[[WebhookEvent], Awaitable[None]]] = None,
        on_voided: Optional[Callable[[WebhookEvent], Awaitable[None]]] = None,
    ):
        """
        Initialize webhook service.

        Args:
            auth: DocuSign authentication handler
            hmac_key: HMAC key for signature verification (optional but recommended)
            on_completed: Callback when envelope is completed
            on_declined: Callback when envelope is declined
            on_voided: Callback when envelope is voided
        """
        self.auth = auth or DocuSignAuth()
        self.envelope_service = EnvelopeService(self.auth)
        self.verifier = WebhookSignatureVerifier(hmac_key) if hmac_key else None
        self._on_completed = on_completed
        self._on_declined = on_declined
        self._on_voided = on_voided

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Raw request body
            signature: X-DocuSign-Signature-1 header value

        Returns:
            True if valid or if verification is disabled
        """
        if not self.verifier:
            logger.warning("Webhook signature verification is disabled")
            return True

        return self.verifier.verify(payload, signature)

    def parse_event(self, payload: dict) -> WebhookEvent:
        """
        Parse webhook payload into event object.

        Args:
            payload: JSON payload from DocuSign

        Returns:
            Parsed WebhookEvent
        """
        return WebhookEvent.from_json(payload)

    async def handle_event(self, event: WebhookEvent) -> WebhookResult:
        """
        Handle a webhook event.

        Args:
            event: Parsed webhook event

        Returns:
            WebhookResult with processing outcome
        """
        logger.info(f"Processing webhook event: {event.event} for envelope {event.envelope_id}")

        if event.is_completed:
            return await self._handle_completed(event)
        elif event.is_declined:
            return await self._handle_declined(event)
        elif event.is_voided:
            return await self._handle_voided(event)
        else:
            # Other events (sent, delivered, etc.) - just acknowledge
            return WebhookResult(
                success=True,
                envelope_id=event.envelope_id,
                event_type=event.event,
                message=f"Event {event.event} acknowledged",
            )

    async def _handle_completed(self, event: WebhookEvent) -> WebhookResult:
        """Handle envelope completed event"""
        logger.info(f"Envelope {event.envelope_id} completed")

        # Find the signer who completed
        signer = None
        for recipient in event.recipients:
            if recipient.status.lower() == "completed" and recipient.signed_datetime:
                signer = recipient
                break

        # Download signed PDF
        signed_pdf = None
        signed_pdf_path = None
        try:
            signed_pdf = self.envelope_service.get_signed_document(event.envelope_id)
            logger.info(f"Downloaded signed PDF for envelope {event.envelope_id}")
        except Exception as e:
            logger.error(f"Failed to download signed PDF: {e}")

        # Call custom callback if provided
        if self._on_completed and signed_pdf:
            try:
                await self._on_completed(event, signed_pdf)
            except Exception as e:
                logger.error(f"Error in on_completed callback: {e}")

        return WebhookResult(
            success=True,
            envelope_id=event.envelope_id,
            event_type=event.event,
            message="Envelope completed successfully",
            signed_pdf_path=signed_pdf_path,
            signer_email=signer.email if signer else None,
            signer_name=signer.name if signer else None,
        )

    async def _handle_declined(self, event: WebhookEvent) -> WebhookResult:
        """Handle envelope declined event"""
        logger.warning(f"Envelope {event.envelope_id} was declined")

        # Find who declined
        decliner = None
        for recipient in event.recipients:
            if recipient.status.lower() == "declined":
                decliner = recipient
                break

        # Call custom callback if provided
        if self._on_declined:
            try:
                await self._on_declined(event)
            except Exception as e:
                logger.error(f"Error in on_declined callback: {e}")

        return WebhookResult(
            success=True,
            envelope_id=event.envelope_id,
            event_type=event.event,
            message=f"Envelope declined by {decliner.name if decliner else 'unknown'}",
            signer_email=decliner.email if decliner else None,
            signer_name=decliner.name if decliner else None,
        )

    async def _handle_voided(self, event: WebhookEvent) -> WebhookResult:
        """Handle envelope voided event"""
        logger.warning(f"Envelope {event.envelope_id} was voided")

        # Call custom callback if provided
        if self._on_voided:
            try:
                await self._on_voided(event)
            except Exception as e:
                logger.error(f"Error in on_voided callback: {e}")

        return WebhookResult(
            success=True,
            envelope_id=event.envelope_id,
            event_type=event.event,
            message="Envelope voided",
        )

    def handle_event_sync(self, event: WebhookEvent) -> WebhookResult:
        """
        Synchronous version of handle_event for non-async contexts.

        Args:
            event: Parsed webhook event

        Returns:
            WebhookResult with processing outcome
        """
        logger.info(f"Processing webhook event (sync): {event.event} for envelope {event.envelope_id}")

        if event.is_completed:
            return self._handle_completed_sync(event)
        elif event.is_declined:
            return self._handle_declined_sync(event)
        elif event.is_voided:
            return self._handle_voided_sync(event)
        else:
            return WebhookResult(
                success=True,
                envelope_id=event.envelope_id,
                event_type=event.event,
                message=f"Event {event.event} acknowledged",
            )

    def _handle_completed_sync(self, event: WebhookEvent) -> WebhookResult:
        """Synchronous handler for completed event"""
        logger.info(f"Envelope {event.envelope_id} completed")

        signer = None
        for recipient in event.recipients:
            if recipient.status.lower() == "completed" and recipient.signed_datetime:
                signer = recipient
                break

        # Download signed PDF
        try:
            signed_pdf = self.envelope_service.get_signed_document(event.envelope_id)
            logger.info(f"Downloaded signed PDF ({len(signed_pdf)} bytes)")
        except Exception as e:
            logger.error(f"Failed to download signed PDF: {e}")

        return WebhookResult(
            success=True,
            envelope_id=event.envelope_id,
            event_type=event.event,
            message="Envelope completed successfully",
            signer_email=signer.email if signer else None,
            signer_name=signer.name if signer else None,
        )

    def _handle_declined_sync(self, event: WebhookEvent) -> WebhookResult:
        """Synchronous handler for declined event"""
        logger.warning(f"Envelope {event.envelope_id} was declined")

        decliner = None
        for recipient in event.recipients:
            if recipient.status.lower() == "declined":
                decliner = recipient
                break

        return WebhookResult(
            success=True,
            envelope_id=event.envelope_id,
            event_type=event.event,
            message=f"Envelope declined by {decliner.name if decliner else 'unknown'}",
            signer_email=decliner.email if decliner else None,
            signer_name=decliner.name if decliner else None,
        )

    def _handle_voided_sync(self, event: WebhookEvent) -> WebhookResult:
        """Synchronous handler for voided event"""
        logger.warning(f"Envelope {event.envelope_id} was voided")

        return WebhookResult(
            success=True,
            envelope_id=event.envelope_id,
            event_type=event.event,
            message="Envelope voided",
        )
