"""
Test script for Template Creation

This test creates a template from a PDF document.
Templates can be reused to send multiple signing requests.
"""
import base64
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from docusign_esign.client.api_exception import ApiException
from docusign_nda_poc.auth.jwt_auth import DocuSignAuth
from docusign_nda_poc.services.template_service import TemplateService


def test_create_template():
    """Test template creation from a PDF document"""
    print("=" * 60)
    print("DocuSign Template Creation Test")
    print("=" * 60)
    print("\nThis test uploads a PDF to DocuSign and creates a template.")
    print("Templates are stored on DocuSign and can be reused for signing requests.")

    # Get template parameters
    print("\n[Input] Enter template parameters:")

    template_name = input("  Template name (e.g., 'VC Company A NDA'): ").strip()
    if not template_name:
        template_name = "NDA Template Test"

    template_description = input(
        "  Template description (optional): "
    ).strip()

    # PDF file selection
    demo_docs_path = (
        Path(__file__).parent.parent.parent / "app" / "static" / "demo_documents"
    )
    pdf_path = demo_docs_path / "World_Wide_Corp_lorem.pdf"

    print(f"\n[Document Selection]")
    print(f"  Default: {pdf_path}")
    custom_path = input("  Enter custom PDF path (or press Enter for default): ").strip()

    if custom_path:
        pdf_path = Path(custom_path)

    if not pdf_path.exists():
        print(f"[ERROR] File not found: {pdf_path}")
        return False

    print(f"\n  Using document: {pdf_path}")

    # Signature position configuration
    print("\n[Signature Position Configuration]")
    print("  1. Anchor tag (fixed position based on text in PDF)")
    print("  2. Free Form (signer chooses position)")
    position_mode = input("  Select mode (1/2, default: 1): ").strip()

    if position_mode == "2":
        anchor_string = None
        print("\n  Mode: Free Form (signer will choose signature position)")
    else:
        anchor_string = input("  Anchor string (default: /sn1/): ").strip()
        if not anchor_string:
            anchor_string = "/sn1/"
        print(f"\n  Mode: Anchor tag")
        print(f"  Anchor string: {anchor_string}")

    try:
        print("\n[1] Initializing services...")
        auth = DocuSignAuth()
        service = TemplateService(auth)

        print("\n[2] Reading document...")
        with open(pdf_path, "rb") as f:
            document_bytes = f.read()
        document_base64 = base64.b64encode(document_bytes).decode("ascii")

        print(f"  Document size: {len(document_bytes)} bytes")

        print("\n[3] Creating template on DocuSign...")
        template_info = service.create_template(
            document_base64=document_base64,
            document_name=pdf_path.name,
            template_name=template_name,
            template_description=template_description,
            role_name="signer",
            anchor_string=anchor_string,
        )

        print("\n[SUCCESS] Template created!")
        print(f"  - Template ID: {template_info.template_id}")
        print(f"  - Name: {template_info.name}")
        if template_info.description:
            print(f"  - Description: {template_info.description}")

        # Save template ID for later use
        template_id_file = Path(__file__).parent / "last_template_id.txt"
        with open(template_id_file, "w") as f:
            f.write(template_info.template_id)
        print(f"\n  Template ID saved to: {template_id_file}")

        # Optionally list all templates
        list_templates = input("\n[4] List all templates? (y/n): ").strip().lower()
        if list_templates == "y":
            templates = service.list_templates()
            print(f"\n  Found {len(templates)} template(s):")
            for t in templates:
                print(f"    - {t.name} (ID: {t.template_id})")

        print("\n" + "=" * 60)
        print("Template creation test completed!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Run Test 6 to send a signing request using this template")
        print(f"  2. Template ID: {template_info.template_id}")
        print("  3. You can also manage this template in the DocuSign web console")
        return True

    except ApiException as e:
        print(f"\n[ERROR] API Exception: {e.status} - {e.reason}")
        if e.body:
            body = e.body.decode("utf8") if isinstance(e.body, bytes) else e.body
            print(f"Body: {body}")
        return False

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_create_template()
    sys.exit(0 if success else 1)
