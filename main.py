import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from routes.scan import router as scan_router
from storage import SupabaseStorageService
from config.logging_config import setup_logging

load_dotenv()

logger = setup_logging()

storage_service = SupabaseStorageService()


app = FastAPI(
    title="Tech Debt Analyzer API",
    description="API for scanning Git repositories for technical debt",
    version="1.0.0",
)

app.include_router(scan_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    logger.info("Health check endpoint accessed")
    return {"message": "Tech Debt Analyzer API is running"}


if __name__ == "__main__":
    logger.info("Starting FastAPI server")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
