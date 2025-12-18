"""
Test script for Envelope Creation with Signing Group
"""
import base64
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from docusign_esign.client.api_exception import ApiException
from docusign_nda_poc.auth.jwt_auth import DocuSignAuth
from docusign_nda_poc.services.envelope_service import EnvelopeService
from docusign_nda_poc.models.nda_request import NDARequest, Signer, WebhookConfig


def test_signing_group_envelope():
    """Test envelope creation with Signing Group (multiple signers, one signature required)"""
    print("=" * 60)
    print("DocuSign Signing Group Envelope Test")
    print("=" * 60)
    print("\nThis test creates an envelope where multiple recipients")
    print("receive the signing request, but only ONE signature is required.")

    # Get test parameters
    print("\n[Input] Enter test parameters:")

    signers = []
    print("\nEnter signers (minimum 2 for Signing Group test):")
    print("(Enter empty email to finish adding signers)\n")

    i = 1
    while True:
        email = input(f"  Signer {i} email: ").strip()
        if not email:
            if len(signers) < 2:
                print("  [Warning] At least 2 signers required for Signing Group test.")
                continue
            break
        name = input(f"  Signer {i} name: ").strip()
        signers.append(Signer(name=name, email=email))
        i += 1

    print(f"\n  Total signers: {len(signers)}")
    for s in signers:
        print(f"    - {s.name} <{s.email}>")

    # Use demo PDF from existing static files or specify path
    demo_docs_path = Path(__file__).parent.parent.parent / "app" / "static" / "demo_documents"
    pdf_path = demo_docs_path / "World_Wide_Corp_lorem.pdf"

    if not pdf_path.exists():
        print(f"\n[WARNING] Demo PDF not found at: {pdf_path}")
        custom_path = input("  Enter path to a PDF file: ").strip()
        pdf_path = Path(custom_path)
        if not pdf_path.exists():
            print(f"[ERROR] File not found: {pdf_path}")
            return False

    print(f"\n  Using document: {pdf_path}")

    # Webhook configuration (optional)
    print("\n[Webhook Configuration]")
    webhook_url = input("  Enter webhook URL (or press Enter to skip): ").strip()
    webhook_config = None
    if webhook_url:
        webhook_config = WebhookConfig(url=webhook_url)
        print(f"  Webhook configured: {webhook_url}")
        print(f"  Events: {webhook_config.envelope_events}")
    else:
        print("  Webhook skipped (no URL provided)")

    try:
        print("\n[1] Initializing services...")
        auth = DocuSignAuth()
        service = EnvelopeService(auth)

        print("\n[2] Preparing NDA request...")
        # Read and encode document
        with open(pdf_path, "rb") as f:
            document_bytes = f.read()
        document_base64 = base64.b64encode(document_bytes).decode("ascii")

        # Create NDA request with Signing Group
        nda_request = NDARequest(
            document_base64=document_base64,
            document_name="NDA_テスト用秘密保持契約書.pdf",
            email_subject="【DCP】NDA締結のお願い（テスト）",
            email_blurb="秘密保持契約書への署名をお願いいたします。グループ内のどなたか1名が署名すれば完了となります。",
            signers=signers,
            group_name="DCP_NDA_SigningGroup",
            webhook_config=webhook_config,
        )

        print(f"\n  Request prepared:")
        print(f"    - Document: {nda_request.document_name}")
        print(f"    - Group Name: {nda_request.group_name}")
        print(f"    - Signers: {len(nda_request.signers)}")
        print(f"    - Webhook: {'Configured' if nda_request.webhook_config else 'Not configured'}")

        print("\n[3] Creating envelope with Signing Group...")
        response = service.create_envelope_with_signing_group(nda_request)

        print("\n[SUCCESS] Envelope created!")
        print(f"  - Envelope ID: {response.envelope_id}")
        print(f"  - Status: {response.status}")
        if response.status_datetime:
            print(f"  - Status DateTime: {response.status_datetime}")

        print(f"\n[INFO] Signing requests have been sent to all {len(signers)} recipients.")
        print("  Any ONE of them can sign to complete the envelope.")

        # Save envelope ID for later use
        envelope_id_file = Path(__file__).parent / "last_envelope_id.txt"
        with open(envelope_id_file, "w") as f:
            f.write(response.envelope_id)
        print(f"\n  Envelope ID saved to: {envelope_id_file}")

        # Optionally check status
        check_status = input("\n[4] Check envelope status? (y/n): ").strip().lower()
        if check_status == "y":
            status_response = service.get_envelope_status(response.envelope_id)
            print(f"  - Current Status: {status_response.status}")

        print("\n" + "=" * 60)
        print("Signing Group envelope test completed!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Check email for all recipients")
        print("  2. Have ONE recipient sign the document")
        print("  3. Verify that the envelope status changes to 'completed'")
        print(f"  4. Use envelope ID: {response.envelope_id} to check status later")
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
    success = test_signing_group_envelope()
    sys.exit(0 if success else 1)
