import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_results(filepath: str) -> Dict[str, Any]:
    with open(filepath, "r") as f:
        return json.load(f)


def calc_z_score(current_mean, base_mean, base_stddev):
    """
    Z-Score indicates how many standard deviations
    away current run is from baseline
    """

    if base_stddev == 0:
        return 0 if current_mean == base_mean else 100.0

    return (current_mean - base_mean) / base_stddev


def compare_benchmarks(
    baseline: Dict[str, Any], current: Dict[str, Any], threshold_pct: float = 10.0
):
    """
    Uses Mean for % change and Z-score for noise detection.
    """

    # colors for terminal
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    header = f"{'Benchmark':<60} | {'CHANGE %':<12} | {'SIGMA (Z)':<10} | {'STATUS'}"
    print(header)
    print("=" * len(header))

    baseline_map = {b["name"]: b for b in baseline["benchmarks"]}
    current_map = {b["name"]: b for b in current["benchmarks"]}

    regressions = []

    for name, curr in current_map.items():
        base = baseline_map.get(name)
        if not base:
            print(f"{name:<60} | {'NEW':<12} | {'N/A':<10} | NEW")
            continue

        m1 = base["stats"]["mean"]
        s1 = base["stats"]["stddev"]
        m2 = curr["stats"]["mean"]

        if m1 == 0:
            delta_pct = 0.0
        else:
            delta_pct = ((m2 - m1) / m1) * 100

        z_score = calc_z_score(m2, m1, s1)

        status = f"{GREEN} OK{RESET}"

        if delta_pct > threshold_pct:
            if abs(z_score) > 2.0:
                status = f"{RED} REGRESSION{RESET}"
                regressions.append(name)
            else:
                status = f"{YELLOW} NOISE{RESET}"
        elif delta_pct < -threshold_pct and abs(z_score) > 2.0:
            status = f"{GREEN} IMPROVED{RESET}"

        print(f"{name:<60} | {delta_pct:>+10.2f}% | {z_score:>9.2f} | {status}")

    if regressions:
        print(
            f"\n{RED}FAILURE: Performance regression detected in {len(regressions)} tests.{RESET}"
        )
        return True
    print(f"\n{GREEN}SUCCESS: No significant regressions.{RESET}")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", help="Gold standard JSON")
    parser.add_argument("current", help="NEW RUN JSON")
    parser.add_argument(
        "--threshold", type=float, default=10.0, help="FAIL if slower by %"
    )
    args = parser.parse_args()

    try:
        failed = compare_benchmarks(
            load_results(args.baseline), load_results(args.current), args.threshold
        )
        sys.exit(1 if failed else 0)
    except FileNotFoundError as e:
        print(f"Error loading files: {e}")
        sys.exit(0)
