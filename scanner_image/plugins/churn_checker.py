from .base_plugin import BasePlugin
import subprocess
import sys
import os

class ChurnChecker(BasePlugin):
    """
    A plugin to analyze code churn using git history.
    """

    def run(self, repo_path: str) -> list[dict]:
        """
        Analyzes the git log to find files with high churn.
        NOTE: This requires a full git clone (not shallow) to work properly.
        """
        print("Running Churn checker...")
        issues = []
        
        # Check if this is a git repository
        git_dir = os.path.join(repo_path, '.git')
        if not os.path.exists(git_dir):
            print("Churn checker: No .git directory found. Skipping git analysis.")
            return issues
            
        try:
            # First, let's check if git works at all
            test_result = subprocess.run([
                "git", "-C", repo_path, "rev-parse", "--git-dir"
            ], capture_output=True, text=True, check=False)
            
            if test_result.returncode != 0:
                print(f"Churn checker: Git repository test failed: {test_result.stderr}")
                return issues
            
            # Get the git log
            result = subprocess.run([
                "git", "-C", repo_path, "log", "--pretty=format:", "--name-only"
            ], capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                print(f"Churn checker: Git log command failed: {result.stderr}")
                return issues
            
            if result.stdout.strip():
                # Process the output: count occurrences, sort, and take top 10
                lines = result.stdout.strip().split('\n')
                files = [line for line in lines if line.strip()]
                
                if not files:
                    return issues
                
                file_counts = {}
                for file in files:
                    file_counts[file] = file_counts.get(file, 0) + 1
                
                # Sort by count (descending) and take top 10
                sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                for file_path, commit_count in sorted_files:
                    if commit_count > 5:  # Only report files with more than 5 commits
                        issues.append({
                            "type": "git_churn",
                            "file": file_path,
                            "line": 1, # Churn is file-level, so line is not applicable
                            "code": "HIGH_CHURN",
                            "message": f"File has a high churn rate with {commit_count} commits.",
                        })

        except subprocess.CalledProcessError as e:
            print(f"Churn checker failed with CalledProcessError: {e}", file=sys.stderr)
        except Exception as e:
            print(f"An unexpected error occurred in ChurnChecker: {e}", file=sys.stderr)
            
        print(f"Churn checker found {len(issues)} issues.")
        return issues 