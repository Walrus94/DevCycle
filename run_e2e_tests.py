#!/usr/bin/env python3
"""
E2E Test Runner Script

This script runs E2E tests in separate batches to avoid terminal freezing issues.
Based on our testing experience, running 3-4 tests at a time works reliably.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_test_batch(batch_name: str, test_paths: list, verbose: bool = True) -> bool:
    """
    Run a batch of E2E tests.

    Args:
        batch_name: Name of the batch for logging
        test_paths: List of test paths to run
        verbose: Whether to run with verbose output

    Returns:
        True if all tests passed, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"🚀 Running E2E Test Batch: {batch_name}")
    print(f"{'='*60}")

    # Build the pytest command
    cmd = ["poetry", "run", "pytest"]

    if verbose:
        cmd.append("-v")

    # Add test paths
    cmd.extend(test_paths)

    print(f"Command: {' '.join(cmd)}")
    print(f"Tests: {len(test_paths)}")
    print(f"Test paths: {test_paths}")
    print("-" * 60)

    try:
        # Run the tests
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=False, text=True)
        end_time = time.time()

        duration = end_time - start_time
        print(f"\n{'='*60}")
        print(f"✅ Batch '{batch_name}' completed in {duration:.2f}s")
        print(f"Exit code: {result.returncode}")

        if result.returncode == 0:
            print(f"🎉 All tests in batch '{batch_name}' PASSED!")
        else:
            print(f"❌ Some tests in batch '{batch_name}' FAILED!")

        print(f"{'='*60}\n")

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Error running batch '{batch_name}': {e}")
        return False


def main():
    """Main function to run all E2E test batches."""
    print("🧪 DevCycle E2E Test Runner")
    print("=" * 60)
    print("This script runs E2E tests in separate batches to avoid terminal freezing.")
    print("Based on our testing experience, 3-4 tests per batch works reliably.\n")

    # Define test batches (3-4 tests per batch)
    test_batches = {
        "Batch 1 - Core Authentication": [
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_user_registration_and_login_flow",
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_user_profile_management",
        ],
        "Batch 2 - User Management": [
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_multiple_user_sessions",
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_logout_and_token_invalidation",
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_debug_routes",
        ],
        "Batch 3 - Health & SQLite": [
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_health_check_endpoint",
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_detailed_health_check",
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_readiness_check",
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_liveness_check",
        ],
        "Batch 4 - Performance & SQLite": [
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_health_endpoints_consistency",
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_health_endpoints_performance",
            "tests/e2e/test_auth_sqlite.py::test_auth_with_sqlite",
        ],
    }

    # Note: Skipped tests (password change, user deactivation) are not included
    print("📋 Test Batches:")
    for batch_name, tests in test_batches.items():
        print(f"  • {batch_name}: {len(tests)} tests")

    print(f"\n⏭️  Skipped tests (not yet implemented):")
    print(f"  • test_password_change_flow")
    print(f"  • test_user_deactivation")

    print(f"\n{'='*60}")

    # Run each batch
    all_passed = True
    batch_results = {}

    for batch_name, test_paths in test_batches.items():
        success = run_test_batch(batch_name, test_paths)
        batch_results[batch_name] = success

        if not success:
            all_passed = False

        # Add a small delay between batches to ensure clean state
        if batch_name != list(test_batches.keys())[-1]:  # Not the last batch
            print("⏳ Waiting 2 seconds before next batch...")
            time.sleep(2)

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 E2E Test Results Summary")
    print(f"{'='*60}")

    for batch_name, success in batch_results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {batch_name}: {status}")

    print(f"\n{'='*60}")
    if all_passed:
        print(f"🎉 ALL E2E TESTS PASSED! 🎉")
        print(f"Total batches: {len(test_batches)}")
        print(f"Total tests: {sum(len(tests) for tests in test_batches.values())}")
    else:
        print(f"❌ Some E2E tests failed. Check the output above.")

    print(f"{'='*60}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
