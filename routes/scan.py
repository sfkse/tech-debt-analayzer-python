from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from logging import getLogger
from scan_task import scan_repo

logger = getLogger(__name__)

router = APIRouter()

class ScanResponse(BaseModel):
    task_id: str
    git_url: str
    status: str
    message: str

class ScanRequest(BaseModel):
    git_url: HttpUrl

@router.post("/scan", response_model=ScanResponse)
async def scan(request: ScanRequest):
    """
    Start a new repository scan.
    Returns a task ID that can be used to check the status.
    """
    git_url = str(request.git_url)
    logger.info(f"Starting scan for repository: {git_url}")
    
    try:
        # Submit the task to Celery
        task = scan_repo.delay(git_url)
        logger.info(f"Scan task submitted with ID: {task.id}")
        
        return ScanResponse(
            task_id=task.id,
            git_url=git_url,
            status="submitted",
            message="Scan task submitted successfully"
        )
    except Exception as e:
        logger.error(f"Failed to submit scan task for {git_url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit scan task: {str(e)}")
