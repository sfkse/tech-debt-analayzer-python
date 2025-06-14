# Initialize application (env vars + logging) - must be first
from config.app_config import initialize_app, get_logger

# Now import everything else
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict
from celery.result import AsyncResult

from scan_task import scan_repo
from storage import storage_service

logger = get_logger(__name__)

app = FastAPI(
    title="Tech Debt Analyzer API",
    description="API for scanning Git repositories for technical debt",
    version="1.0.0"
)

class ScanRequest(BaseModel):
    git_url: HttpUrl
    
class ScanResponse(BaseModel):
    task_id: str
    git_url: str
    status: str
    message: str

class ScanResult(BaseModel):
    task_id: str
    git_url: str
    status: str
    total_issues: Optional[int] = None
    scan_id: Optional[str] = None
    results: Optional[List[Dict]] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    """Health check endpoint."""
    logger.info("Health check endpoint accessed")
    return {"message": "Tech Debt Analyzer API is running"}

@app.post("/scan", response_model=ScanResponse)
async def start_scan(request: ScanRequest):
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

@app.get("/scan/{task_id}", response_model=ScanResult)
async def get_scan_status(task_id: str):
    """
    Get the status and results of a scan task.
    """
    logger.debug(f"Checking status for task: {task_id}")
    
    try:
        # Get the Celery task result
        task_result = AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            logger.debug(f"Task {task_id} is still pending")
            return ScanResult(
                task_id=task_id,
                git_url="unknown",
                status="pending",
            )
        elif task_result.state == 'SUCCESS':
            result_data = task_result.result
            logger.info(f"Task {task_id} completed successfully")
            return ScanResult(
                task_id=task_id,
                git_url=result_data.get('git_url', 'unknown'),
                status="completed",
                total_issues=result_data.get('total_issues'),
                scan_id=result_data.get('scan_id'),
                results=result_data.get('results')
            )
        elif task_result.state == 'FAILURE':
            logger.error(f"Task {task_id} failed: {task_result.info}")
            return ScanResult(
                task_id=task_id,
                git_url="unknown",
                status="failed",
                error=str(task_result.info)
            )
        else:
            logger.warning(f"Task {task_id} in unexpected state: {task_result.state}")
            return ScanResult(
                task_id=task_id,
                git_url="unknown",
                status=task_result.state.lower()
            )
            
    except Exception as e:
        logger.error(f"Error retrieving task status for {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving task status: {str(e)}")

@app.get("/scans/recent")
async def get_recent_scans(limit: int = 10):
    """
    Get recent scans from the database.
    """
    logger.info(f"Retrieving {limit} recent scans")
    
    if not storage_service.is_available():
        logger.warning("Storage service not available for recent scans request")
        raise HTTPException(status_code=503, detail="Storage service not available")
    
    try:
        scans = storage_service.get_recent_scans(limit=limit)
        logger.info(f"Retrieved {len(scans)} recent scans")
        return {"scans": scans}
    except Exception as e:
        logger.error(f"Error retrieving recent scans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving recent scans: {str(e)}")

@app.get("/scans/history")
async def get_scan_history(git_url: str, limit: int = 10):
    """
    Get scan history for a specific repository.
    """
    logger.info(f"Retrieving scan history for {git_url} (limit: {limit})")
    
    if not storage_service.is_available():
        logger.warning("Storage service not available for scan history request")
        raise HTTPException(status_code=503, detail="Storage service not available")
    
    try:
        scans = storage_service.get_scans_by_repo(git_url, limit=limit)
        logger.info(f"Retrieved {len(scans)} scans for repository {git_url}")
        return {"git_url": git_url, "scans": scans}
    except Exception as e:
        logger.error(f"Error retrieving scan history for {git_url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving scan history: {str(e)}")

@app.get("/scans/{scan_id}")
async def get_scan_by_id(scan_id: str):
    """
    Get detailed scan results by scan ID.
    """
    logger.info(f"Retrieving scan details for ID: {scan_id}")
    
    if not storage_service.is_available():
        logger.warning("Storage service not available for scan details request")
        raise HTTPException(status_code=503, detail="Storage service not available")
    
    try:
        scan = storage_service.get_scan_results(scan_id)
        if not scan:
            logger.warning(f"Scan not found: {scan_id}")
            raise HTTPException(status_code=404, detail="Scan not found")
        
        logger.info(f"Successfully retrieved scan details for ID: {scan_id}")
        return scan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving scan {scan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving scan: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server")
    initialize_app()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 