"""
Test script for Sending Envelope from Template

This test sends a signing request using an existing template.
Supports both single signer and Signing Group (multiple signers, one signature required).
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from docusign_esign.client.api_exception import ApiException
from docusign_nda_poc.auth.jwt_auth import DocuSignAuth
from docusign_nda_poc.services.template_service import TemplateService


def test_send_from_template():
    """Test sending envelope from an existing template"""
    print("=" * 60)
    print("DocuSign Send from Template Test")
    print("=" * 60)
    print("\nThis test sends a signing request using an existing template.")
    print("The PDF is already stored on DocuSign - no upload required.")

    # Get template ID
    print("\n[Input] Enter template information:")

    # Try to load saved template ID
    template_id_file = Path(__file__).parent / "last_template_id.txt"
    default_template_id = ""
    if template_id_file.exists():
        default_template_id = template_id_file.read_text().strip()

    if default_template_id:
        print(f"  Last used template ID: {default_template_id}")
        template_id = input(
            "  Enter template ID (or press Enter to use above): "
        ).strip()
        if not template_id:
            template_id = default_template_id
    else:
        template_id = input("  Enter template ID: ").strip()

    if not template_id:
        print("[ERROR] Template ID is required")
        return False

    # Choose signing mode
    print("\n[Signing Mode]")
    print("  1. Single signer")
    print("  2. Signing Group (multiple signers, one signature required)")
    mode = input("  Select mode (1/2): ").strip()

    try:
        print("\n[1] Initializing services...")
        auth = DocuSignAuth()
        service = TemplateService(auth)

        # Verify template exists
        print("\n[2] Verifying template...")
        try:
            template_info = service.get_template(template_id)
            print(f"  Template found: {template_info.name}")
        except ApiException as e:
            if e.status == 400:
                print(f"[ERROR] Template not found: {template_id}")
                return False
            raise

        if mode == "2":
            # Signing Group mode
            return _send_with_signing_group(service, template_id)
        else:
            # Single signer mode
            return _send_single_signer(service, template_id)

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


def _send_single_signer(service: TemplateService, template_id: str) -> bool:
    """Send envelope to a single signer"""
    print("\n[Single Signer Mode]")

    signer_email = input("  Signer email: ").strip()
    signer_name = input("  Signer name: ").strip()

    if not signer_email or not signer_name:
        print("[ERROR] Email and name are required")
        return False

    print("\n[3] Sending envelope from template...")
    response = service.create_envelope_from_template(
        template_id=template_id,
        signer_email=signer_email,
        signer_name=signer_name,
    )

    print("\n[SUCCESS] Envelope sent!")
    print(f"  - Envelope ID: {response.envelope_id}")
    print(f"  - Status: {response.status}")

    # Save envelope ID
    envelope_id_file = Path(__file__).parent / "last_envelope_id.txt"
    with open(envelope_id_file, "w") as f:
        f.write(response.envelope_id)
    print(f"\n  Envelope ID saved to: {envelope_id_file}")

    print("\n" + "=" * 60)
    print("Template send test completed!")
    print("=" * 60)
    print("\nNext steps:")
    print(f"  1. Check email for: {signer_email}")
    print("  2. Sign the document")
    print(f"  3. Use envelope ID: {response.envelope_id} to check status")
    return True


def _send_with_signing_group(service: TemplateService, template_id: str) -> bool:
    """Send envelope to a Signing Group"""
    print("\n[Signing Group Mode]")
    print("All signers will receive the signing request email.")
    print("Only ONE signature is required to complete.\n")

    signers = []
    print("Enter signers (1 or more):")
    print("(Enter empty email to finish adding signers)\n")

    i = 1
    while True:
        email = input(f"  Signer {i} email: ").strip()
        if not email:
            if len(signers) < 1:
                print("  [Warning] At least 1 signer is required.")
                continue
            break
        name = input(f"  Signer {i} name: ").strip()
        signers.append({"name": name, "email": email})
        i += 1

    print(f"\n  Total signers: {len(signers)}")
    for s in signers:
        print(f"    - {s['name']} <{s['email']}>")

    print("\n[3] Creating envelope with Signing Group...")
    response = service.create_envelope_from_template_with_signing_group(
        template_id=template_id,
        signers=signers,
    )

    print("\n[SUCCESS] Envelope sent!")
    print(f"  - Envelope ID: {response.envelope_id}")
    print(f"  - Status: {response.status}")

    # Save envelope ID
    envelope_id_file = Path(__file__).parent / "last_envelope_id.txt"
    with open(envelope_id_file, "w") as f:
        f.write(response.envelope_id)
    print(f"\n  Envelope ID saved to: {envelope_id_file}")

    print(f"\n[INFO] Signing requests sent to all {len(signers)} recipients.")
    print("  Any ONE of them can sign to complete the envelope.")

    print("\n" + "=" * 60)
    print("Template send with Signing Group test completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Check email for all recipients")
    print("  2. Have ONE recipient sign the document")
    print("  3. Verify that the envelope status changes to 'completed'")
    print(f"  4. Use envelope ID: {response.envelope_id} to check status")
    return True


if __name__ == "__main__":
    success = test_send_from_template()
    sys.exit(0 if success else 1)
