"""
DocuSign Envelope Service

Handles envelope creation with Recipient Group support.
"""
import base64
from pathlib import Path
from typing import Optional

import uuid

from docusign_esign import (
    EnvelopesApi,
    EnvelopeDefinition,
    Document,
    Signer,
    Recipients,
    SignHere,
    DateSigned,
    Tabs,
    EventNotification,
    EnvelopeEvent,
    SigningGroupsApi,
    SigningGroupInformation,
    SigningGroup,
    SigningGroupUser,
)

from ..auth.jwt_auth import DocuSignAuth
from ..models.nda_request import NDARequest, EnvelopeResponse, EnvelopeStatus


class EnvelopeService:
    """Service for creating and managing DocuSign envelopes"""

    def __init__(self, auth: Optional[DocuSignAuth] = None):
        self.auth = auth or DocuSignAuth()

    def create_envelope_simple(
        self,
        document_path: Path,
        signer_name: str,
        signer_email: str,
        email_subject: str = "署名をお願いします",
    ) -> EnvelopeResponse:
        """
        Create a simple envelope with a single signer.
        Useful for testing basic functionality.

        Args:
            document_path: Path to the PDF document
            signer_name: Name of the signer
            signer_email: Email of the signer
            email_subject: Subject of the email

        Returns:
            EnvelopeResponse with envelope_id and status
        """
        # Read and encode document
        with open(document_path, "rb") as f:
            document_bytes = f.read()
        document_base64 = base64.b64encode(document_bytes).decode("ascii")

        # Create document
        document = Document(
            document_base64=document_base64,
            name=document_path.name,
            file_extension="pdf",
            document_id="1",
        )

        # Create signer with signature tab
        signer = Signer(
            email=signer_email,
            name=signer_name,
            recipient_id="1",
            routing_order="1",
        )

        # Add signature tab using anchor string
        # サンプルPDF (World_Wide_Corp_lorem.pdf) は /sn1/ を使用
        sign_here = SignHere(
            anchor_string="/sn1/",
            anchor_units="pixels",
            anchor_x_offset="20",
            anchor_y_offset="10",
        )
        signer.tabs = Tabs(sign_here_tabs=[sign_here])

        # Create envelope definition
        envelope_definition = EnvelopeDefinition(
            email_subject=email_subject,
            documents=[document],
            recipients=Recipients(signers=[signer]),
            status="sent",
        )

        # Get authenticated API client
        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        # Create envelope
        envelopes_api = EnvelopesApi(api_client)
        result = envelopes_api.create_envelope(
            account_id=token.account_id,
            envelope_definition=envelope_definition,
        )

        return EnvelopeResponse.from_api_response(result)

    def create_envelope_with_signing_group(
        self, request: NDARequest
    ) -> EnvelopeResponse:
        """
        Create an envelope with Signing Group.
        All group members receive the signing request email,
        but only one signature is required.

        This method:
        1. Creates a temporary Signing Group via API
        2. Creates the envelope with that Signing Group
        3. Deletes the Signing Group after envelope is sent

        Args:
            request: NDARequest with document and signers

        Returns:
            EnvelopeResponse with envelope_id and status
        """
        if not request.signers:
            raise ValueError("At least one signer is required")

        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        # Step 1: Create temporary Signing Group
        signing_groups_api = SigningGroupsApi(api_client)
        group_name = f"{request.group_name}_{uuid.uuid4().hex[:8]}"

        group_users = [
            SigningGroupUser(user_name=s.name, email=s.email)
            for s in request.signers
        ]

        signing_group = SigningGroup(
            group_name=group_name,
            group_type="sharedSigningGroup",
            users=group_users,
        )

        signing_group_info = SigningGroupInformation(groups=[signing_group])
        created_groups = signing_groups_api.create_list(
            account_id=token.account_id,
            signing_group_information=signing_group_info,
        )

        signing_group_id = created_groups.groups[0].signing_group_id

        try:
            # Step 2: Create document
            document = Document(
                document_base64=request.document_base64,
                name=request.document_name,
                file_extension="pdf",
                document_id="1",
            )

            # Step 3: Create signer with signing group
            signer = Signer(
                signing_group_id=signing_group_id,
                recipient_id="1",
                routing_order="1",
            )

            # Add signature tabs
            sign_here = SignHere(
                anchor_string=request.signature_position.anchor_string,
                anchor_units=request.signature_position.anchor_units,
                anchor_x_offset=request.signature_position.anchor_x_offset,
                anchor_y_offset=request.signature_position.anchor_y_offset,
            )
            date_signed = DateSigned(
                anchor_string=request.date_signed_position.anchor_string,
                anchor_units=request.date_signed_position.anchor_units,
                anchor_x_offset=request.date_signed_position.anchor_x_offset,
                anchor_y_offset=request.date_signed_position.anchor_y_offset,
            )
            signer.tabs = Tabs(sign_here_tabs=[sign_here], date_signed_tabs=[date_signed])

            # Build event notification if webhook configured
            event_notification = None
            if request.webhook_config:
                event_notification = EventNotification(
                    url=request.webhook_config.url,
                    logging_enabled=str(request.webhook_config.logging_enabled).lower(),
                    require_acknowledgment=str(request.webhook_config.require_acknowledgment).lower(),
                    include_documents=str(request.webhook_config.include_documents).lower(),
                    envelope_events=[
                        EnvelopeEvent(envelope_event_status_code=event)
                        for event in request.webhook_config.envelope_events
                    ],
                )

            # Step 4: Create envelope definition
            envelope_definition = EnvelopeDefinition(
                email_subject=request.email_subject,
                email_blurb=request.email_blurb,
                documents=[document],
                recipients=Recipients(signers=[signer]),
                status=request.status.value,
                event_notification=event_notification,
            )

            # Step 5: Create envelope
            envelopes_api = EnvelopesApi(api_client)
            result = envelopes_api.create_envelope(
                account_id=token.account_id,
                envelope_definition=envelope_definition,
            )

            return EnvelopeResponse.from_api_response(result)

        finally:
            # Step 6: Delete temporary Signing Group
            signing_groups_api.delete_list(
                account_id=token.account_id,
                signing_group_information=SigningGroupInformation(
                    groups=[SigningGroup(signing_group_id=signing_group_id)]
                ),
            )

    def get_envelope_status(self, envelope_id: str) -> EnvelopeResponse:
        """
        Get the current status of an envelope.

        Args:
            envelope_id: The envelope ID to check

        Returns:
            EnvelopeResponse with current status
        """
        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        envelopes_api = EnvelopesApi(api_client)
        result = envelopes_api.get_envelope(
            account_id=token.account_id,
            envelope_id=envelope_id,
        )

        return EnvelopeResponse.from_api_response(result)

    def get_signed_document(self, envelope_id: str) -> bytes:
        """
        Get the signed document (combined PDF) from a completed envelope.

        Args:
            envelope_id: The envelope ID

        Returns:
            PDF document as bytes
        """
        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        envelopes_api = EnvelopesApi(api_client)
        document = envelopes_api.get_document(
            account_id=token.account_id,
            envelope_id=envelope_id,
            document_id="combined",
        )

        return document

    def void_envelope(self, envelope_id: str, reason: str = "Voided") -> EnvelopeResponse:
        """
        Void an envelope that has not been completed.

        Args:
            envelope_id: The envelope ID to void
            reason: Reason for voiding

        Returns:
            EnvelopeResponse with updated status
        """
        from docusign_esign import Envelope

        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        envelope_update = Envelope(status="voided", voided_reason=reason)

        envelopes_api = EnvelopesApi(api_client)
        result = envelopes_api.update(
            account_id=token.account_id,
            envelope_id=envelope_id,
            envelope=envelope_update,
        )

        return EnvelopeResponse.from_api_response(result)
