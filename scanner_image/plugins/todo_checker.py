from .base_plugin import BasePlugin
import os
import re
import sys

class TodoChecker(BasePlugin):
    """
    A plugin to find TODO, FIXME, and XXX comments in the code.
    """

    def run(self, repo_path: str) -> list[dict]:
        """
        Scans all text-based files for common 'to-do' keywords.
        """
        print("Running TODO checker...")
        issues = []
        todo_pattern = re.compile(r".*(TODO|FIXME|XXX):(.*)", re.IGNORECASE)
        
        # Exclude common binary file extensions and large files
        exclude_ext = {'.png', '.jpg', '.jpeg', '.gif', '.zip', '.tar', '.gz', '.ico', '.pdf', '.svg'}

        for root, _, files in os.walk(repo_path):
            if '.git' in root:
                continue
            for file in files:
                if any(file.endswith(ext) for ext in exclude_ext):
                    continue
                
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, "r", encoding="utf-8", errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            match = todo_pattern.match(line)
                            if match:
                                keyword = match.group(1).upper()
                                message = match.group(2).strip()
                                issues.append({
                                    "type": "todo_comment",
                                    "file": os.path.relpath(filepath, repo_path),
                                    "line": line_num,
                                    "code": f"FOUND_{keyword}",
                                    "message": message,
                                })
                except Exception as e:
                    print(f"TODO checker could not read file {filepath}: {e}", file=sys.stderr)
        
        print(f"TODO checker found {len(issues)} issues.")
        return issues 