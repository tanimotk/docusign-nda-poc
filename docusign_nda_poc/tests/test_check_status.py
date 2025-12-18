"""
Test script for checking envelope status and downloading signed documents
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from docusign_esign.client.api_exception import ApiException
from docusign_nda_poc.auth.jwt_auth import DocuSignAuth
from docusign_nda_poc.services.envelope_service import EnvelopeService
from docusign_nda_poc.models.nda_request import EnvelopeStatus


def test_check_status():
    """Test envelope status checking and document download"""
    print("=" * 60)
    print("DocuSign Envelope Status Check / Document Download")
    print("=" * 60)

    # Try to load last envelope ID
    envelope_id_file = Path(__file__).parent / "last_envelope_id.txt"
    default_envelope_id = ""
    if envelope_id_file.exists():
        with open(envelope_id_file, "r") as f:
            default_envelope_id = f.read().strip()
        print(f"\n[INFO] Found last envelope ID: {default_envelope_id}")

    # Get envelope ID
    envelope_id = input(f"\nEnter Envelope ID [{default_envelope_id}]: ").strip()
    if not envelope_id:
        envelope_id = default_envelope_id

    if not envelope_id:
        print("[ERROR] Envelope ID is required")
        return False

    try:
        print("\n[1] Initializing services...")
        auth = DocuSignAuth()
        service = EnvelopeService(auth)

        print(f"\n[2] Checking status for envelope: {envelope_id}")
        response = service.get_envelope_status(envelope_id)

        print(f"\n[STATUS] Envelope Status:")
        print(f"  - Envelope ID: {response.envelope_id}")
        print(f"  - Status: {response.status.value}")
        if response.status_datetime:
            print(f"  - Status DateTime: {response.status_datetime}")

        # If completed, offer to download document
        if response.status == EnvelopeStatus.COMPLETED:
            print("\n[INFO] Envelope is completed!")
            download = input("  Download signed document? (y/n): ").strip().lower()
            if download == "y":
                print("\n[3] Downloading signed document...")
                pdf_bytes = service.get_signed_document(envelope_id)

                output_path = Path(__file__).parent / f"signed_{envelope_id[:8]}.pdf"
                with open(output_path, "wb") as f:
                    f.write(pdf_bytes)

                print(f"\n[SUCCESS] Document saved to: {output_path}")
                print(f"  - File size: {len(pdf_bytes):,} bytes")

        elif response.status == EnvelopeStatus.SENT:
            print("\n[INFO] Envelope has been sent and is waiting for signature.")
            print("  Check recipient email for the signing link.")

        elif response.status == EnvelopeStatus.DECLINED:
            print("\n[WARNING] Envelope was declined by a recipient.")

        elif response.status == EnvelopeStatus.VOIDED:
            print("\n[WARNING] Envelope has been voided.")

        print("\n" + "=" * 60)
        print("Status check completed!")
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
    success = test_check_status()
    sys.exit(0 if success else 1)
