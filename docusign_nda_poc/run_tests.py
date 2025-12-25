#!/usr/bin/env python3
"""
DocuSign NDA POC - Test Runner

Usage:
    python run_tests.py [test_number]

Tests:
    1. JWT Authentication
    2. Signing Group Envelope with Anchor (1+ signers, one signature required)
    3. Signing Group Envelope with Free Form (1+ signers, signer chooses position)
    4. Check Status / Download Document
    ---
    5. Create Template (upload PDF to DocuSign)
    6. Send from Template (use stored template)
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def show_menu():
    """Display test menu"""
    print("\n" + "=" * 60)
    print("DocuSign NDA POC - Test Menu")
    print("=" * 60)
    print("\n[PDF Upload Method - 毎回PDFをアップロード]")
    print("  1. JWT Authentication Test")
    print("     - Verifies JWT token generation and API access")
    print("")
    print("  2. Signing Group Envelope Test (Anchor)")
    print("     - Creates envelope with 1+ signers")
    print("     - Only ONE signature required (NDA use case)")
    print("     - Uses anchor tag /sn1/ for signature position")
    print("")
    print("  3. Signing Group Envelope Test (Free Form)")
    print("     - Creates envelope with 1+ signers")
    print("     - Only ONE signature required")
    print("     - Signer chooses where to place signature")
    print("     - For PDFs without anchor tags")
    print("")
    print("  4. Check Status / Download Document")
    print("     - Check envelope status")
    print("     - Download signed PDF if completed")
    print("")
    print("-" * 60)
    print("[Template Method - DocuSign上にPDFを保存]")
    print("  5. Create Template")
    print("     - Upload PDF to DocuSign as a template")
    print("     - Template is stored on DocuSign for reuse")
    print("")
    print("  6. Send from Template")
    print("     - Send signing request using existing template")
    print("     - No PDF upload required (uses stored template)")
    print("     - Supports single signer or Signing Group")
    print("")
    print("  0. Exit")
    print("")


def run_test(test_number: int) -> bool:
    """Run the specified test"""
    if test_number == 1:
        from docusign_nda_poc.tests.test_auth import test_jwt_authentication
        return test_jwt_authentication()

    elif test_number == 2:
        from docusign_nda_poc.tests.test_envelope_recipient_group import test_signing_group_envelope
        return test_signing_group_envelope()

    elif test_number == 3:
        from docusign_nda_poc.tests.test_envelope_free_form import test_free_form_envelope
        return test_free_form_envelope()

    elif test_number == 4:
        from docusign_nda_poc.tests.test_check_status import test_check_status
        return test_check_status()

    elif test_number == 5:
        from docusign_nda_poc.tests.test_template_create import test_create_template
        return test_create_template()

    elif test_number == 6:
        from docusign_nda_poc.tests.test_template_send import test_send_from_template
        return test_send_from_template()

    else:
        print(f"Unknown test number: {test_number}")
        return False


def main():
    """Main entry point"""
    # Check for command line argument
    if len(sys.argv) > 1:
        try:
            test_number = int(sys.argv[1])
            if test_number == 0:
                print("Exiting.")
                return
            success = run_test(test_number)
            sys.exit(0 if success else 1)
        except ValueError:
            print(f"Invalid test number: {sys.argv[1]}")
            sys.exit(1)

    # Interactive menu
    while True:
        show_menu()
        try:
            choice = input("Select test (0-6): ").strip()
            if not choice:
                continue

            test_number = int(choice)
            if test_number == 0:
                print("\nExiting. Goodbye!")
                break

            if test_number < 1 or test_number > 6:
                print("Invalid choice. Please select 0-6.")
                continue

            run_test(test_number)

            input("\nPress Enter to continue...")

        except ValueError:
            print("Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting.")
            break


if __name__ == "__main__":
    main()
