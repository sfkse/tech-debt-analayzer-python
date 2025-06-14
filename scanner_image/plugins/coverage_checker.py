from .base_plugin import BasePlugin
from constants import ISSUE_TYPES
import json
import os
import sys


class CoverageChecker(BasePlugin):
    """
    A plugin to check for test coverage reports.
    This is a placeholder and looks for a 'coverage.json' file.
    """

    def run(self, repo_path: str) -> list[dict]:
        """
        Looks for a coverage.json file and reports the overall coverage.
        """
        print("Running Coverage checker...")
        issues = []
        coverage_file = os.path.join(repo_path, "coverage.json")

        if os.path.exists(coverage_file):
            try:
                with open(coverage_file, "r") as f:
                    data = json.load(f)

                # Assuming a standard coverage.py JSON format
                if "meta" in data and "totals" in data:
                    coverage_percent = data["totals"]["percent_covered"]
                    if coverage_percent < 80.0:
                        issues.append(
                            {
                                "type": ISSUE_TYPES.COVERAGE,
                                "file": "coverage.json",
                                "line": 1,
                                "code": "LOW_COVERAGE",
                                "message": f"Test coverage is {coverage_percent:.2f}%, which is below the 80% threshold.",
                            }
                        )
            except json.JSONDecodeError:
                print(
                    f"Coverage checker: Could not decode {coverage_file}",
                    file=sys.stderr,
                )
            except Exception as e:
                print(
                    f"An unexpected error occurred in CoverageChecker: {e}",
                    file=sys.stderr,
                )
        else:
            print("Coverage checker: No coverage.json file found.")

        print(f"Coverage checker found {len(issues)} issues.")
        return issues
