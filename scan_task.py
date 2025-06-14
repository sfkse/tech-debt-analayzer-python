from logging import getLogger
from celery import Celery
from docker_runner import scan_repo_with_docker
from storage import SupabaseStorageService
from dotenv import load_dotenv

logger = getLogger(__name__)
load_dotenv()

# Create Celery app
celery_app = Celery('tech_debt_analyzer')
celery_app.config_from_object('config.celery_config')

@celery_app.task(bind=True)
def scan_repo(self, git_url: str):
    """
    Celery task to scan a repository for technical debt.
    
    Args:
        git_url: The URL of the Git repository to scan
        
    Returns:
        Dictionary containing scan results and metadata
    """
    task_id = self.request.id
    logger.info(f"Starting scan task {task_id} for repository: {git_url}")
    
    try:
        # Run the Docker-based scan
        logger.info(f"[{task_id}] Running Docker scan for {git_url}")
        scan_results = scan_repo_with_docker(git_url)
        
        # Check if scan was successful
        if "error" in scan_results:
            logger.error(f"[{task_id}] Scan failed: {scan_results['error']}")
            raise Exception(f"Scan failed: {scan_results['error']}")
        
        logger.info(f"[{task_id}] Docker scan completed successfully. Found {len(scan_results)} issues.")
        storage_service = SupabaseStorageService()

        try:
            logger.info(f"[{task_id}] Storing scan results in database")
            scan_id = storage_service.store_scan_results(git_url, scan_results)
            logger.info(f"[{task_id}] Scan results stored with ID: {scan_id}")
        except Exception as e:
            logger.error(f"[{task_id}] Failed to store scan results: {e}", exc_info=True)

        result = {
            'git_url': git_url,
            'total_issues': len(scan_results),
            'scan_id': scan_id,
            'results': scan_results
        }
        
        logger.info(f"[{task_id}] Scan task completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"[{task_id}] Scan task failed: {e}", exc_info=True)
        raise
