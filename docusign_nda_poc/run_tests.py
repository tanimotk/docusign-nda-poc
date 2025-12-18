#!/usr/bin/env python3
"""
DocuSign NDA POC - Test Runner

Usage:
    python run_tests.py [test_number]

Tests:
    1. JWT Authentication
    2. Simple Envelope (single signer)
    3. Recipient Group Envelope (multiple signers, one signature)
    4. Check Status / Download Document
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
    print("\nAvailable tests:")
    print("  1. JWT Authentication Test")
    print("     - Verifies JWT token generation and API access")
    print("")
    print("  2. Simple Envelope Test (Single Signer)")
    print("     - Creates envelope with one signer")
    print("     - Good for basic functionality verification")
    print("")
    print("  3. Recipient Group Envelope Test")
    print("     - Creates envelope with multiple signers")
    print("     - Only ONE signature required (NDA use case)")
    print("")
    print("  4. Check Status / Download Document")
    print("     - Check envelope status")
    print("     - Download signed PDF if completed")
    print("")
    print("  0. Exit")
    print("")


def run_test(test_number: int) -> bool:
    """Run the specified test"""
    if test_number == 1:
        from docusign_nda_poc.tests.test_auth import test_jwt_authentication
        return test_jwt_authentication()

    elif test_number == 2:
        from docusign_nda_poc.tests.test_envelope_simple import test_simple_envelope
        return test_simple_envelope()

    elif test_number == 3:
        from docusign_nda_poc.tests.test_envelope_recipient_group import test_signing_group_envelope
        return test_signing_group_envelope()

    elif test_number == 4:
        from docusign_nda_poc.tests.test_check_status import test_check_status
        return test_check_status()

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
            choice = input("Select test (0-4): ").strip()
            if not choice:
                continue

            test_number = int(choice)
            if test_number == 0:
                print("\nExiting. Goodbye!")
                break

            if test_number < 1 or test_number > 4:
                print("Invalid choice. Please select 0-4.")
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
