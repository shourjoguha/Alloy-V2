#!/usr/bin/env python3
"""
Script to run performance tests and generate a summary report.

Usage:
    python tests/run_performance_tests.py [options]

Options:
    --update-baselines    Update performance baselines after run
    --html                Generate HTML benchmark report
    --verbose             Show detailed output
    --category CATEGORY    Run only specific category (program, session, movement)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run performance tests and generate summary report"
    )
    parser.add_argument(
        "--update-baselines",
        action="store_true",
        help="Update performance baselines after run",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML benchmark report",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--category",
        choices=["program", "session", "movement", "all"],
        default="all",
        help="Run only specific test category",
    )
    return parser.parse_args()


def build_test_command(args):
    """Build pytest command based on arguments."""
    cmd = ["pytest", "tests/performance/", "--benchmark-only"]

    if args.category != "all":
        if args.category == "program":
            cmd.append("tests/performance/test_program_creation.py")
        elif args.category == "session":
            cmd.append("tests/performance/test_session_generation.py")
        elif args.category == "movement":
            cmd.append("tests/performance/test_movement_queries.py")

    if args.update_baselines:
        cmd.append("--benchmark-update-baselines")

    if args.html:
        cmd.append("--benchmark-html=benchmark_report.html")

    if args.verbose:
        cmd.append("-v")

    return cmd


def run_tests(cmd):
    """Run the tests and return exit code."""
    print("=" * 80)
    print("Running Performance Regression Tests")
    print("=" * 80)
    print(f"Command: {' '.join(cmd)}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

    print()
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return result.returncode


def generate_summary():
    """Generate summary report from benchmark results."""
    results_file = Path("benchmark_results.json")

    if not results_file.exists():
        print("\nNo benchmark results file found. Skipping summary.")
        return

    print("\n" + "=" * 80)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 80)

    try:
        with open(results_file, "r") as f:
            data = json.load(f)

        benchmarks = data.get("benchmarks", [])
        total_tests = len(benchmarks)
        failed_tests = 0
        improved_tests = 0
        stable_tests = 0

        print(f"\nTotal benchmarks run: {total_tests}")
        print()

        # Group by test group
        groups = {}
        for bench in benchmarks:
            name = bench.get("name", "Unknown")
            group_name = name.split("::")[1] if "::" in name else "Other"
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(bench)

        # Print results by group
        for group_name, group_benchmarks in sorted(groups.items()):
            print(f"\n{group_name}")
            print("-" * 80)

            for bench in group_benchmarks:
                name = bench.get("name", "Unknown")
                stats = bench.get("stats", {})
                median = stats.get("median", 0)
                mean = stats.get("mean", 0)
                min_time = stats.get("min", 0)
                max_time = stats.get("max", 0)
                rounds = stats.get("rounds", 0)

                # Extract test name from full path
                test_name = name.split("::")[-1] if "::" in name else name

                # Check for regression
                has_regression = stats.get("has_regression", False)
                degradation = stats.get("degradation_percent", 0)

                if has_regression:
                    status = "❌ REGRESSION"
                    failed_tests += 1
                elif degradation < -5:  # More than 5% improvement
                    status = "✅ IMPROVED"
                    improved_tests += 1
                else:
                    status = "✓ STABLE"
                    stable_tests += 1

                print(f"  {test_name}")
                print(f"    Status: {status}")
                print(f"    Median: {median:.2f}ms, Mean: {mean:.2f}ms")
                print(f"    Range: {min_time:.2f}ms - {max_time:.2f}ms")
                print(f"    Rounds: {rounds}")
                if has_regression:
                    print(f"    Degradation: +{degradation:.1f}%")
                print()

        # Summary statistics
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total tests: {total_tests}")
        print(f"Stable: {stable_tests}")
        print(f"Improved: {improved_tests}")
        print(f"Regressions: {failed_tests}")

        if failed_tests > 0:
            print(f"\n⚠️  {failed_tests} benchmark(s) showed performance regression!")
            print("   Review the output above for details.")
        elif improved_tests > 0:
            print(f"\n✨ {improved_tests} benchmark(s) showed performance improvement!")
        else:
            print(f"\n✅ All performance baselines maintained!")

    except json.JSONDecodeError as e:
        print(f"\nError parsing benchmark results: {e}")
    except Exception as e:
        print(f"\nError generating summary: {e}")

    print("=" * 80)


def check_baseline_file():
    """Check if baseline file exists and is valid."""
    baseline_file = Path("tests/performance_data/performance_baselines.json")

    if not baseline_file.exists():
        print("\n⚠️  Warning: Performance baselines file not found.")
        print(f"   Expected location: {baseline_file}")
        print("   A new baseline file will be created on first run.")
        return False

    try:
        with open(baseline_file, "r") as f:
            data = json.load(f)
        print(f"\n✓ Loaded {len(data)} baseline(s) from {baseline_file}")
        return True
    except json.JSONDecodeError:
        print(f"\n⚠️  Warning: Invalid JSON in baseline file {baseline_file}")
        return False


def main():
    args = parse_args()

    # Check baseline file
    check_baseline_file()

    # Build and run test command
    cmd = build_test_command(args)
    exit_code = run_tests(cmd)

    # Generate summary if tests ran
    if exit_code == 0:
        generate_summary()
    else:
        print("\n⚠️  Tests failed or were interrupted. Check output above for details.")

    # Print additional info
    print()
    print("Additional information:")
    print("  - Benchmark results saved to: benchmark_results.json")
    if args.html:
        print("  - HTML report saved to: benchmark_report.html")
    print("  - Benchmark storage: .benchmarks/")
    print("  - Baseline file: tests/performance_data/performance_baselines.json")
    print()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
