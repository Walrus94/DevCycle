#!/usr/bin/env python3
"""
DevCycle Test Runner Script

This script provides options to run different types of tests:
- Unit tests
- Integration tests
- E2E tests (in batches to avoid freezing)
- All tests
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """
    Run a command and return success status.

    Args:
        cmd: Command to run
        description: Description of what's being run

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=False, text=True)
        end_time = time.time()

        duration = end_time - start_time
        print(f"\n{'='*60}")
        print(f"✅ {description} completed in {duration:.2f}s")
        print(f"Exit code: {result.returncode}")

        if result.returncode == 0:
            print(f"🎉 SUCCESS!")
        else:
            print(f"❌ FAILED!")

        print(f"{'='*60}\n")

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False


def run_unit_tests(verbose: bool = True) -> bool:
    """Run unit tests."""
    cmd = ["poetry", "run", "pytest", "tests/unit/"]
    if verbose:
        cmd.append("-v")

    return run_command(cmd, "Unit Tests")


def run_integration_tests(verbose: bool = True) -> bool:
    """Run integration tests."""
    cmd = ["poetry", "run", "pytest", "tests/integration/"]
    if verbose:
        cmd.append("-v")

    return run_command(cmd, "Integration Tests")


def run_e2e_tests_batch(
    batch_name: str, test_paths: list, verbose: bool = True
) -> bool:
    """Run a specific batch of E2E tests."""
    cmd = ["poetry", "run", "pytest"]
    if verbose:
        cmd.append("-v")

    cmd.extend(test_paths)

    return run_command(cmd, f"E2E Tests - {batch_name}")


def run_all_e2e_tests(verbose: bool = True) -> bool:
    """Run all E2E tests in batches."""
    print("🧪 DevCycle E2E Test Runner")
    print("=" * 60)
    print("Running E2E tests in batches to avoid terminal freezing.\n")

    # Define test batches (3-4 tests per batch)
    test_batches = {
        "Core Authentication": [
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_user_registration_and_login_flow",
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_user_profile_management",
        ],
        "User Management": [
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_multiple_user_sessions",
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_logout_and_token_invalidation",
            "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_debug_routes",
        ],
        "Health Endpoints": [
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_health_check_endpoint",
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_detailed_health_check",
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_readiness_check",
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_liveness_check",
        ],
        "Performance & SQLite": [
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_health_endpoints_consistency",
            "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_health_endpoints_performance",
            "tests/e2e/test_auth_sqlite.py::test_auth_with_sqlite",
        ],
    }

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
        success = run_e2e_tests_batch(batch_name, test_paths, verbose)
        batch_results[batch_name] = success

        if not success:
            all_passed = False

        # Add delay between batches
        if batch_name != list(test_batches.keys())[-1]:
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

    return all_passed


def run_all_tests(verbose: bool = True) -> bool:
    """Run all tests in sequence."""
    print("🧪 DevCycle Complete Test Suite")
    print("=" * 60)

    # Run unit tests
    if not run_unit_tests(verbose):
        print("❌ Unit tests failed. Stopping.")
        return False

    # Run integration tests
    if not run_integration_tests(verbose):
        print("❌ Integration tests failed. Stopping.")
        return False

    # Run E2E tests
    if not run_all_e2e_tests(verbose):
        print("❌ E2E tests failed.")
        return False

    print("🎉 ALL TESTS COMPLETED SUCCESSFULLY! 🎉")
    return True


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description="DevCycle Test Runner")
    parser.add_argument(
        "--type",
        "-t",
        choices=["unit", "integration", "e2e", "all"],
        default="all",
        help="Type of tests to run (default: all)",
    )
    parser.add_argument(
        "--batch",
        "-b",
        type=int,
        choices=[1, 2, 3, 4],
        help="Specific E2E batch to run (1-4)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Run without verbose output"
    )

    args = parser.parse_args()

    verbose = not args.quiet

    try:
        if args.type == "unit":
            success = run_unit_tests(verbose)
        elif args.type == "integration":
            success = run_integration_tests(verbose)
        elif args.type == "e2e":
            if args.batch:
                # Run specific batch
                batches = {
                    1: "Core Authentication",
                    2: "User Management",
                    3: "Health Endpoints",
                    4: "Performance & SQLite",
                }
                batch_name = batches[args.batch]
                test_paths = {
                    "Core Authentication": [
                        "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_user_registration_and_login_flow",
                        "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_user_profile_management",
                    ],
                    "User Management": [
                        "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_multiple_user_sessions",
                        "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_logout_and_token_invalidation",
                        "tests/e2e/test_auth_fastapi_users_e2e.py::TestFastAPIUsersAuthenticationE2E::test_debug_routes",
                    ],
                    "Health Endpoints": [
                        "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_health_check_endpoint",
                        "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_detailed_health_check",
                        "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_readiness_check",
                        "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_liveness_check",
                    ],
                    "Performance & SQLite": [
                        "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_health_endpoints_consistency",
                        "tests/e2e/test_health_e2e.py::TestHealthEndpointsE2E::test_health_endpoints_performance",
                        "tests/e2e/test_auth_sqlite.py::test_auth_with_sqlite",
                    ],
                }
                success = run_e2e_tests_batch(
                    batch_name, test_paths[batch_name], verbose
                )
            else:
                success = run_all_e2e_tests(verbose)
        else:  # all
            success = run_all_tests(verbose)

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Test run interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
