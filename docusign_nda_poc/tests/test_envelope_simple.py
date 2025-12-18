"""
Test script for Simple Envelope Creation (Single Signer)
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from docusign_esign.client.api_exception import ApiException
from docusign_nda_poc.auth.jwt_auth import DocuSignAuth
from docusign_nda_poc.services.envelope_service import EnvelopeService


def test_simple_envelope():
    """Test simple envelope creation with a single signer"""
    print("=" * 60)
    print("DocuSign Simple Envelope Creation Test")
    print("=" * 60)

    # Get test parameters
    print("\n[Input] Enter test parameters:")
    signer_email = input("  Signer email: ").strip()
    signer_name = input("  Signer name: ").strip()

    # Use demo PDF from existing static files or specify path
    demo_docs_path = Path(__file__).parent.parent.parent / "app" / "static" / "demo_documents"
    pdf_path = demo_docs_path / "World_Wide_Corp_lorem.pdf"

    if not pdf_path.exists():
        print(f"\n[ERROR] Demo PDF not found at: {pdf_path}")
        custom_path = input("  Enter path to a PDF file: ").strip()
        pdf_path = Path(custom_path)
        if not pdf_path.exists():
            print(f"[ERROR] File not found: {pdf_path}")
            return False

    print(f"\n  Using document: {pdf_path}")

    try:
        print("\n[1] Initializing services...")
        auth = DocuSignAuth()
        service = EnvelopeService(auth)

        print("\n[2] Creating envelope...")
        response = service.create_envelope_simple(
            document_path=pdf_path,
            signer_name=signer_name,
            signer_email=signer_email,
            email_subject="【テスト】DocuSign署名テスト",
        )

        print("\n[SUCCESS] Envelope created!")
        print(f"  - Envelope ID: {response.envelope_id}")
        print(f"  - Status: {response.status}")
        if response.status_datetime:
            print(f"  - Status DateTime: {response.status_datetime}")

        print(f"\n[INFO] A signing request has been sent to: {signer_email}")
        print("  Please check your email and sign the document.")

        # Optionally check status
        check_status = input("\n[3] Check envelope status? (y/n): ").strip().lower()
        if check_status == "y":
            status_response = service.get_envelope_status(response.envelope_id)
            print(f"  - Current Status: {status_response.status}")

        print("\n" + "=" * 60)
        print("Simple envelope test completed!")
        print("=" * 60)
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
    success = test_simple_envelope()
    sys.exit(0 if success else 1)
