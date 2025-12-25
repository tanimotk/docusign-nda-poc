"""
DocuSign Template Service

Handles template creation, management, and envelope creation from templates.
"""
from dataclasses import dataclass
from typing import Optional

from docusign_esign import (
    TemplatesApi,
    EnvelopeTemplate,
    Document,
    Signer,
    Recipients,
    SignHere,
    DateSigned,
    Tabs,
    EnvelopesApi,
    EnvelopeDefinition,
    TemplateRole,
)

from ..auth.jwt_auth import DocuSignAuth
from ..models.nda_request import EnvelopeResponse


@dataclass
class TemplateInfo:
    """Template information"""

    template_id: str
    name: str
    description: Optional[str] = None
    uri: Optional[str] = None

    @classmethod
    def from_api_response(cls, response) -> "TemplateInfo":
        """Create from DocuSign API response"""
        return cls(
            template_id=response.template_id,
            name=response.name,
            description=getattr(response, "description", None),
            uri=getattr(response, "uri", None),
        )


class TemplateService:
    """Service for creating and managing DocuSign templates"""

    def __init__(self, auth: Optional[DocuSignAuth] = None):
        self.auth = auth or DocuSignAuth()

    def create_template(
        self,
        document_base64: str,
        document_name: str,
        template_name: str,
        template_description: str = "",
        role_name: str = "signer",
        anchor_string: Optional[str] = "/sn1/",
        anchor_x_offset: str = "20",
        anchor_y_offset: str = "10",
        date_anchor_x_offset: str = "120",
        date_anchor_y_offset: str = "10",
    ) -> TemplateInfo:
        """
        Create a new template with a document and signature tab.

        Args:
            document_base64: Base64 encoded PDF document
            document_name: Name of the document
            template_name: Name for the template
            template_description: Description of the template
            role_name: Role name for the signer (default: "signer")
            anchor_string: Anchor string for signature placement (default: "/sn1/")
            anchor_x_offset: X offset from anchor
            anchor_y_offset: Y offset from anchor
            date_anchor_x_offset: X offset for date tab
            date_anchor_y_offset: Y offset for date tab

        Returns:
            TemplateInfo with template_id and name
        """
        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        # Create document
        document = Document(
            document_base64=document_base64,
            name=document_name,
            file_extension="pdf",
            document_id="1",
        )

        # Create signer placeholder with tabs
        signer = Signer(
            role_name=role_name,
            recipient_id="1",
            routing_order="1",
        )

        # Add signature tabs if anchor string is provided
        if anchor_string:
            sign_here = SignHere(
                anchor_string=anchor_string,
                anchor_units="pixels",
                anchor_x_offset=anchor_x_offset,
                anchor_y_offset=anchor_y_offset,
                recipient_id="1",
            )
            date_signed = DateSigned(
                anchor_string=anchor_string,
                anchor_units="pixels",
                anchor_x_offset=date_anchor_x_offset,
                anchor_y_offset=date_anchor_y_offset,
                recipient_id="1",
            )
            signer.tabs = Tabs(
                sign_here_tabs=[sign_here],
                date_signed_tabs=[date_signed],
            )

        # Create template definition
        template = EnvelopeTemplate(
            name=template_name,
            description=template_description,
            documents=[document],
            recipients=Recipients(signers=[signer]),
            email_subject="【DCP】NDA締結のお願い",
            email_blurb="秘密保持契約書への署名をお願いいたします。",
            status="created",
        )

        # Create template via API
        templates_api = TemplatesApi(api_client)
        result = templates_api.create_template(
            account_id=token.account_id,
            envelope_template=template,
        )

        return TemplateInfo(
            template_id=result.template_id,
            name=template_name,
            description=template_description,
            uri=getattr(result, "uri", None),
        )

    def get_template(self, template_id: str) -> TemplateInfo:
        """
        Get template information by ID.

        Args:
            template_id: The template ID

        Returns:
            TemplateInfo with template details
        """
        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        templates_api = TemplatesApi(api_client)
        result = templates_api.get(
            account_id=token.account_id,
            template_id=template_id,
        )

        return TemplateInfo.from_api_response(result)

    def list_templates(self, search_text: Optional[str] = None) -> list[TemplateInfo]:
        """
        List all templates in the account.

        Args:
            search_text: Optional search text to filter templates

        Returns:
            List of TemplateInfo objects
        """
        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        templates_api = TemplatesApi(api_client)

        kwargs = {}
        if search_text:
            kwargs["search_text"] = search_text

        result = templates_api.list_templates(
            account_id=token.account_id,
            **kwargs,
        )

        templates = []
        if result.envelope_templates:
            for t in result.envelope_templates:
                templates.append(TemplateInfo.from_api_response(t))

        return templates

    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.

        Args:
            template_id: The template ID to delete

        Returns:
            True if successful
        """
        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        templates_api = TemplatesApi(api_client)
        templates_api.delete(
            account_id=token.account_id,
            template_id=template_id,
        )

        return True

    def update_template_document(
        self,
        template_id: str,
        document_base64: str,
        document_name: str,
    ) -> TemplateInfo:
        """
        Update the document in an existing template.

        Args:
            template_id: The template ID to update
            document_base64: New base64 encoded PDF document
            document_name: Name of the new document

        Returns:
            Updated TemplateInfo
        """
        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        templates_api = TemplatesApi(api_client)

        # Update document
        document = Document(
            document_base64=document_base64,
            name=document_name,
            file_extension="pdf",
            document_id="1",
        )

        templates_api.update_documents(
            account_id=token.account_id,
            template_id=template_id,
            envelope_definition=EnvelopeDefinition(documents=[document]),
        )

        return self.get_template(template_id)

    def create_envelope_from_template(
        self,
        template_id: str,
        signer_email: str,
        signer_name: str,
        role_name: str = "signer",
        email_subject: Optional[str] = None,
        email_blurb: Optional[str] = None,
        status: str = "sent",
    ) -> EnvelopeResponse:
        """
        Create and send an envelope from a template.

        Args:
            template_id: The template ID to use
            signer_email: Email address of the signer
            signer_name: Name of the signer
            role_name: Role name defined in the template (default: "signer")
            email_subject: Optional email subject (overrides template default)
            email_blurb: Optional email body (overrides template default)
            status: Envelope status - "sent" to send immediately, "created" for draft

        Returns:
            EnvelopeResponse with envelope_id and status
        """
        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        # Create template role for the signer
        template_role = TemplateRole(
            email=signer_email,
            name=signer_name,
            role_name=role_name,
        )

        # Build envelope definition
        envelope_definition = EnvelopeDefinition(
            template_id=template_id,
            template_roles=[template_role],
            status=status,
        )

        if email_subject:
            envelope_definition.email_subject = email_subject
        if email_blurb:
            envelope_definition.email_blurb = email_blurb

        # Create envelope
        envelopes_api = EnvelopesApi(api_client)
        result = envelopes_api.create_envelope(
            account_id=token.account_id,
            envelope_definition=envelope_definition,
        )

        return EnvelopeResponse.from_api_response(result)

    def create_envelope_from_template_with_signing_group(
        self,
        template_id: str,
        signers: list[dict],
        group_name: str = "NDA_SigningGroup",
        role_name: str = "signer",
        email_subject: Optional[str] = None,
        email_blurb: Optional[str] = None,
        status: str = "sent",
    ) -> EnvelopeResponse:
        """
        Create an envelope from a template with Signing Group support.
        All group members receive the signing request, but only one signature is required.

        Args:
            template_id: The template ID to use
            signers: List of dicts with 'name' and 'email' keys
            group_name: Name for the signing group
            role_name: Role name defined in the template (default: "signer")
            email_subject: Optional email subject
            email_blurb: Optional email body
            status: Envelope status

        Returns:
            EnvelopeResponse with envelope_id and status
        """
        import uuid
        from docusign_esign import (
            SigningGroupsApi,
            SigningGroupInformation,
            SigningGroup,
            SigningGroupUser,
        )

        if not signers:
            raise ValueError("At least one signer is required")

        api_client = self.auth.get_api_client()
        token = self.auth.authenticate()

        # Step 1: Create temporary Signing Group
        signing_groups_api = SigningGroupsApi(api_client)
        unique_group_name = f"{group_name}_{uuid.uuid4().hex[:8]}"

        group_users = [
            SigningGroupUser(user_name=s["name"], email=s["email"]) for s in signers
        ]

        signing_group = SigningGroup(
            group_name=unique_group_name,
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
            # Step 2: Create template role with signing group
            template_role = TemplateRole(
                signing_group_id=signing_group_id,
                role_name=role_name,
            )

            # Build envelope definition
            envelope_definition = EnvelopeDefinition(
                template_id=template_id,
                template_roles=[template_role],
                status=status,
            )

            if email_subject:
                envelope_definition.email_subject = email_subject
            if email_blurb:
                envelope_definition.email_blurb = email_blurb

            # Create envelope
            envelopes_api = EnvelopesApi(api_client)
            result = envelopes_api.create_envelope(
                account_id=token.account_id,
                envelope_definition=envelope_definition,
            )

            return EnvelopeResponse.from_api_response(result)

        finally:
            # Step 3: Delete temporary Signing Group
            signing_groups_api.delete_list(
                account_id=token.account_id,
                signing_group_information=SigningGroupInformation(
                    groups=[SigningGroup(signing_group_id=signing_group_id)]
                ),
            )
