import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from supabase import create_client

# Use centralized logging
from config.app_config import get_logger
logger = get_logger(__name__)

class StorageService:
    """Centralized storage service for all database operations."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one storage instance."""
        if cls._instance is None:
            cls._instance = super(StorageService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize storage service only once."""
        if not self._initialized:
            self.supabase = None
            self._available = False
            self._initialize()
            StorageService._initialized = True
    
    def _initialize(self):
        """Initialize Supabase connection."""
        logger.info("Initializing storage service...")
        
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not found in environment variables. Storage will be disabled.")
                logger.debug("Missing environment variables: SUPABASE_URL and/or SUPABASE_ANON_KEY")
                return
            
            logger.debug(f"Connecting to Supabase at: {supabase_url[:50]}...")
            self.supabase = create_client(supabase_url, supabase_key)
            self._available = True
            logger.info("Storage service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize storage service: {e}", exc_info=True)
            self._available = False
    
    def is_available(self) -> bool:
        """Check if storage service is available."""
        return self._available
    
    def store_scan_results(self, git_url: str, results: List[Dict]) -> Optional[str]:
        """
        Store scan results in database.
        
        Returns:
            scan_id if successful, None if storage unavailable or failed
        """
        if not self.is_available():
            logger.warning("Storage not available, skipping result storage")
            return None
        
        scan_id = str(uuid.uuid4())
        logger.info(f"Storing scan results for {git_url} with ID: {scan_id}")
        logger.debug(f"Storing {len(results)} issues for scan {scan_id}")
        
        try:
            # Store scan metadata
            scan_data = {
                'id': scan_id,
                'git_url': git_url,
                'status': 'completed',
                'total_issues': len(results),
                'scanned_at': datetime.utcnow().isoformat(),
                'report_json': json.dumps(results)
            }
            
            logger.debug(f"Inserting scan metadata for {scan_id}")
            self.supabase.table('scans').insert(scan_data).execute()
            
            # Store individual issues for easier querying
            if results:
                issues_data = []
                for issue in results:
                    issue_data = {
                        'scan_id': scan_id,
                        'type': issue.get('type'),
                        'file_path': issue.get('file'),
                        'line_number': issue.get('line'),
                        'code': issue.get('code'),
                        'message': issue.get('message'),
                        'severity': self._determine_severity(issue.get('type'))
                    }
                    issues_data.append(issue_data)
                
                logger.debug(f"Inserting {len(issues_data)} individual issues for scan {scan_id}")
                self.supabase.table('issues').insert(issues_data).execute()
            
            logger.info(f"Successfully stored scan results with ID: {scan_id}")
            return scan_id
            
        except Exception as e:
            logger.error(f"Failed to store scan results for {git_url}: {e}", exc_info=True)
            # Try to store failed scan record
            self._store_failed_scan_record(scan_id, git_url, str(e))
            return None
    
    def store_failed_scan(self, git_url: str, error_message: str) -> Optional[str]:
        """
        Store failed scan record.
        
        Returns:
            scan_id if successful, None if storage unavailable or failed
        """
        if not self.is_available():
            logger.warning("Storage not available, skipping failed scan storage")
            return None
        
        scan_id = str(uuid.uuid4())
        logger.info(f"Storing failed scan record for {git_url} with ID: {scan_id}")
        return self._store_failed_scan_record(scan_id, git_url, error_message)
    
    def _store_failed_scan_record(self, scan_id: str, git_url: str, error_message: str) -> Optional[str]:
        """Internal method to store failed scan record."""
        try:
            failed_scan_data = {
                'id': scan_id,
                'git_url': git_url,
                'status': 'failed',
                'total_issues': 0,
                'scanned_at': datetime.utcnow().isoformat(),
                'error_message': error_message
            }
            
            logger.debug(f"Inserting failed scan record for {scan_id}")
            self.supabase.table('scans').insert(failed_scan_data).execute()
            logger.info(f"Successfully stored failed scan record with ID: {scan_id}")
            return scan_id
            
        except Exception as e:
            logger.error(f"Failed to store failed scan record for {scan_id}: {e}", exc_info=True)
            return None
    
    def get_scan_results(self, scan_id: str) -> Optional[Dict]:
        """Retrieve scan results by scan ID."""
        if not self.is_available():
            logger.warning("Storage not available for scan retrieval")
            return None
        
        logger.debug(f"Retrieving scan results for ID: {scan_id}")
        
        try:
            response = self.supabase.table('scans').select('*').eq('id', scan_id).execute()
            
            if response.data:
                scan = response.data[0]
                logger.debug(f"Found scan record for {scan_id}")
                
                # Parse the JSON report
                if scan.get('report_json'):
                    try:
                        scan['issues'] = json.loads(scan['report_json'])
                        logger.debug(f"Parsed {len(scan['issues'])} issues from JSON report")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON report for scan {scan_id}: {e}")
                
                logger.info(f"Successfully retrieved scan results for ID: {scan_id}")
                return scan
            else:
                logger.warning(f"No scan found with ID: {scan_id}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve scan results for scan_id {scan_id}: {e}", exc_info=True)
            return None
    
    def get_scans_by_repo(self, git_url: str, limit: int = 10) -> List[Dict]:
        """Get recent scans for a specific repository."""
        if not self.is_available():
            logger.warning("Storage not available for repository scan history")
            return []
        
        logger.debug(f"Retrieving scan history for {git_url} (limit: {limit})")
        
        try:
            response = (self.supabase.table('scans')
                       .select('id, git_url, status, total_issues, scanned_at')
                       .eq('git_url', git_url)
                       .order('scanned_at', desc=True)
                       .limit(limit)
                       .execute())
            
            scans = response.data or []
            logger.info(f"Retrieved {len(scans)} scans for repository {git_url}")
            return scans
            
        except Exception as e:
            logger.error(f"Failed to retrieve scans for repo {git_url}: {e}", exc_info=True)
            return []
    
    def get_recent_scans(self, limit: int = 20) -> List[Dict]:
        """Get recent scans across all repositories."""
        if not self.is_available():
            logger.warning("Storage not available for recent scans")
            return []
        
        logger.debug(f"Retrieving recent scans (limit: {limit})")
        
        try:
            response = (self.supabase.table('scans')
                       .select('id, git_url, status, total_issues, scanned_at')
                       .order('scanned_at', desc=True)
                       .limit(limit)
                       .execute())
            
            scans = response.data or []
            logger.info(f"Retrieved {len(scans)} recent scans")
            return scans
            
        except Exception as e:
            logger.error(f"Failed to retrieve recent scans: {e}", exc_info=True)
            return []
    
    def _determine_severity(self, issue_type: str) -> str:
        """Determine severity based on issue type."""
        severity_map = {
            'flake8': 'medium',
            'radon_complexity': 'high',
            'git_churn': 'medium',
            'todo_comment': 'low',
            'coverage': 'high'
        }
        severity = severity_map.get(issue_type, 'medium')
        logger.debug(f"Determined severity '{severity}' for issue type '{issue_type}'")
        return severity

# Global storage service instance
storage_service = StorageService()

