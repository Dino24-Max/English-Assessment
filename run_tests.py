#!/usr/bin/env python3
"""
Test Runner for English Assessment Platform
Runs all tests with coverage reporting
"""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all tests with coverage"""

    print("=" * 70)
    print("RUNNING TEST SUITE - English Assessment Platform")
    print("=" * 70)
    print()

    # Change to project root
    project_root = Path(__file__).parent

    # Commands to run
    commands = [
        # Install test dependencies if needed
        {
            "name": "Install Dependencies",
            "cmd": ["pip", "install", "-q", "pytest", "pytest-asyncio", "pytest-cov", "httpx"]
        },

        # Run unit tests
        {
            "name": "Unit Tests",
            "cmd": ["pytest", "src/test/unit/", "-v", "--tb=short"]
        },

        # Run integration tests
        {
            "name": "Integration Tests",
            "cmd": ["pytest", "src/test/integration/", "-v", "--tb=short"]
        },

        # Run all tests with coverage
        {
            "name": "Full Test Suite with Coverage",
            "cmd": [
                "pytest",
                "src/test/",
                "-v",
                "--cov=src/main/python",
                "--cov-report=term-missing",
                "--cov-report=html",
                "--tb=short"
            ]
        }
    ]

    results = []

    for test_run in commands:
        print(f"\n[{test_run['name']}]")
        print("-" * 70)

        try:
            result = subprocess.run(
                test_run['cmd'],
                cwd=project_root,
                capture_output=False,
                text=True
            )

            success = result.returncode == 0
            results.append({
                "name": test_run['name'],
                "success": success
            })

            if not success and test_run['name'] != "Install Dependencies":
                print(f"[FAIL] {test_run['name']}")
            elif success and test_run['name'] != "Install Dependencies":
                print(f"[PASS] {test_run['name']}")

        except Exception as e:
            print(f"[ERROR] {test_run['name']}: {e}")
            results.append({
                "name": test_run['name'],
                "success": False
            })

    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r['success'])
    total = len(results)

    for result in results:
        status = "[PASS]" if result['success'] else "[FAIL]"
        print(f"{status} - {result['name']}")

    print()
    print(f"Total: {passed}/{total} test runs passed")

    if passed == total:
        print()
        print("ALL TESTS PASSED!")
        print()
        print("Coverage report generated in: htmlcov/index.html")
        print("You can view detailed coverage by opening that file in a browser")
        return 0
    else:
        print()
        print("WARNING: SOME TESTS FAILED - Please review the output above")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
