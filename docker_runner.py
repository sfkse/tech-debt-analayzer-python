import docker
import git
import json
import os
import shutil
import tempfile
import uuid
import subprocess

# Use centralized logging
from logging import getLogger

log = getLogger(__name__)


def scan_repo_with_docker(
    git_url: str, scanner_image: str = "scanner-image:latest", timeout: int = 60
):
    """
    Clones a Git repository, runs a Docker-based scan on it, and returns the results.

    Args:
        git_url: The URL of the Git repository to scan.
        scanner_image: The name of the Docker image to use for scanning.
        timeout: The maximum time in seconds to allow the scanner container to run.

    Returns:
        A dictionary containing the scan results, or an error message.
    """
    job_id = str(uuid.uuid4())
    log.info(f"Starting scan job {job_id} for {git_url}")
    base_temp_dir = tempfile.gettempdir()
    job_dir = os.path.join(base_temp_dir, job_id)
    repo_dir = os.path.join(job_dir, "repo")
    output_dir = os.path.join(job_dir, "output")
    results_file = os.path.join(output_dir, "results.json")

    try:
        # Create temporary directories
        os.makedirs(repo_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        log.info(f"[{job_id}] Created temporary directories: {job_dir}")

        # Clone the repository
        log.info(f"[{job_id}] Cloning repository: {git_url}")
        # Use subprocess to ensure we get full history
        try:
            subprocess.run(
                ["git", "clone", git_url, repo_dir],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            log.error(f"[{job_id}] Git clone failed for {git_url}. Error: {e.stderr}")
            raise  # Re-raise the exception to be caught by the main handler

        log.info(f"[{job_id}] Repository cloned to: {repo_dir}")

        # Initialize Docker client
        client = docker.from_env()
        log.info(f"[{job_id}] Docker client initialized")
        # Define volume mounts
        volumes = {
            repo_dir: {"bind": "/repo", "mode": "ro"},
            output_dir: {"bind": "/output", "mode": "rw"},
        }

        log.info(f"[{job_id}] Running scanner container '{scanner_image}'")
        container = client.containers.run(
            scanner_image,
            volumes=volumes,
            detach=True,
        )

        # Wait for the container to finish, with a timeout
        result = container.wait(timeout=timeout)

        container_logs = container.logs().decode("utf-8")
        log.info(
            f"[{job_id}] Container finished with exit code {result['StatusCode']}."
        )
        log.debug(f"[{job_id}] Full container logs:\n{container_logs}")

        # Check if results file exists
        if os.path.exists(results_file):
            with open(results_file, "r") as f:
                scan_results = json.load(f)
            log.info(f"[{job_id}] Scan complete. Found {len(scan_results)} issues.")
            return scan_results
        else:
            log.error(
                f"[{job_id}] Scan failed: results.json not found. Container logs: {container_logs}"
            )
            return {"error": "results.json not found", "logs": container_logs}

    except git.GitCommandError as e:
        log.error(f"[{job_id}] Git clone command error: {e}")
        return {"error": f"Git clone failed: {e}"}
    except docker.errors.ContainerError as e:
        log.error(
            f"[{job_id}] Docker container execution failed: {e.stderr}", exc_info=True
        )
        return {"error": f"Docker container failed: {e}"}
    except docker.errors.ImageNotFound:
        log.error(f"[{job_id}] Docker image not found: {scanner_image}")
        return {"error": f"Docker image not found: {scanner_image}"}
    except Exception as e:
        # This will catch the timeout from container.wait
        if "Timeout" in str(e):
            log.error(f"[{job_id}] Scan timed out after {timeout} seconds.")
            return {"error": f"Scan timed out after {timeout} seconds."}
        log.error(
            f"[{job_id}] An unexpected error occurred in docker_runner: {e}",
            exc_info=True,
        )
        return {"error": f"An unexpected error occurred: {e}"}
    finally:
        # Clean up the temporary directory
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
            log.info(f"[{job_id}] Cleaned up temporary directory: {job_dir}")

        # Stop and remove the container if it's still running (e.g., on timeout)
        try:
            if "container" in locals() and container.status == "running":
                container.stop()
                log.info(f"[{job_id}] Stopped container.")
            if "container" in locals():
                container.remove()
                log.info(f"[{job_id}] Removed container.")
        except docker.errors.NotFound:
            pass  # Container already removed
        except Exception as e:
            log.error(f"[{job_id}] Error during container cleanup: {e}", exc_info=True)


if __name__ == "__main__":
    # Example usage:
    # Make sure you have a repository to test with.
    # For example, you can use this simple flask app: https://github.com/pallets/flask
    test_repo_url = "https://github.com/pallets/flask.git"
    results = scan_repo_with_docker(test_repo_url)
    print("\n--- Scan Results ---")
    # print(json.dumps(results, indent=2))
    print("--------------------")
