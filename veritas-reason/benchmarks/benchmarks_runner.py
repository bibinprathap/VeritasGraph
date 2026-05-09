import argparse
import os
import subprocess
import sys
from datetime import datetime


def run_benchmarks():
    """
    Master Runner for VeritasReason Benchmarks.
    """
    parser = argparse.ArgumentParser(description="Run VeritasReason Benchmarks")
    parser.add_argument(
        "--strict", action="store_true", help="Fail script if performance regresses"
    )
    args = parser.parse_args()

    print("Starting VeritasReason Benchmark Suite...")

    timestamp = datetime.now().strftime("%Y%m%d_%H_%M_%S")
    os.makedirs("benchmarks/results", exist_ok=True)

    current_json = f"benchmarks/results/run_{timestamp}.json"
    baseline_json = "benchmarks/results/baseline.json"

    # Run Benchmarks
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "benchmarks/",
        "-p",
        "no:typeguard",
        "-p",
        "no:langsmith",
        "--benchmark-only",
        f"--benchmark-json={current_json}",
        "--benchmark-columns=min,mean,stddev,ops",
        "--benchmark-sort=mean",
    ]

    print(f"Executing benchmarks... (saving to {current_json})")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Benchmarks failed to execute (runtime errors).")
        sys.exit(result.returncode)

    print("Benchmarks completed execution.")

    # Compare against Baseline
    if os.path.exists(baseline_json):
        print(f"Comparing against Baseline ({baseline_json})...")

        if os.path.exists("benchmarks/infrastructure/compare.py"):
            compare_cmd = [
                sys.executable,
                "benchmarks/infrastructure/compare.py",
                baseline_json,
                current_json,
            ]

            compare_result = subprocess.run(compare_cmd)

            if compare_result.returncode != 0:
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("   PERFORMANCE REGRESSION DETECTED")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                if args.strict:
                    sys.exit(1)
            else:
                print("Performance is within acceptable limits.")
        else:
            print(
                "Comparison script not found (benchmarks/infrastructure/compare.py). Skipping comparison."
            )
    else:
        print("No baseline found. This run effectively sets the new baseline.")

    print(f"\n[Action] To update baseline: cp {current_json} {baseline_json}")


if __name__ == "__main__":
    run_benchmarks()
