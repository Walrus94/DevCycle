#!/usr/bin/env python3
"""
Test runner script for DevCycle.

This script provides convenient commands to run different types of tests:
- Unit tests (fast, no external dependencies)
- Integration tests (may use mocks)
- E2E tests (use testcontainers, slower)
- All tests
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        print(f"\n💥 Some tests failed!")
        return False
    except FileNotFoundError:
        print(f"\nError: Command not found. Make sure '{cmd[0]}' is in your PATH.")
        return False


def main():
    parser = argparse.ArgumentParser(description="DevCycle Test Runner")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "api", "e2e", "all"],
        help="Type of tests to run",
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Only collect tests, don't run them",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print(f"🚀 DevCycle Test Runner")
    print(f"📁 Working directory: {Path.cwd()}")
    print(f"🎯 Test type: {args.test_type}")

    base_cmd = ["poetry", "run", "pytest", "--tb=short", "-v"]
    if args.collect_only:
        base_cmd.append("--collect-only")

    if args.test_type == "unit":
        cmd = base_cmd + ["tests/unit/"]
        description = "Unit Tests"
    elif args.test_type == "integration":
        cmd = base_cmd + ["tests/integration/"]
        description = "Integration Tests"
    elif args.test_type == "api":
        cmd = base_cmd + ["tests/api/"]
        description = "API Tests"
    elif args.test_type == "e2e":
        cmd = base_cmd + ["tests/e2e/"]
        description = "E2E Tests"
    elif args.test_type == "all":
        cmd = base_cmd + ["tests/", "--durations=10"]  # Show slowest 10 tests
        description = "All Tests"
    else:
        parser.print_help()
        sys.exit(1)

    if not run_command(cmd, description):
        sys.exit(1)

    print("\n🎉 All tests completed successfully!")


if __name__ == "__main__":
    import os

    main()
