import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import boto3
from supabase import create_client

from logging import getLogger
logger = getLogger(__name__)

class SupabaseStorageService:
    """Centralized storage service for all database operations."""

    def __init__(self):
        """Initialize storage service only once."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
        if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not found in environment variables. Storage will be disabled.")
                logger.debug("Missing environment variables: SUPABASE_URL and/or SUPABASE_ANON_KEY")
                return
            
        self.supabase = create_client(supabase_url, supabase_key)
        logger.info("Storage service initialized successfully")
    
    def store_scan_results(self, git_url: str, results: List[Dict]) -> Optional[str]:
        """
        Store scan results in database.
        
        Returns:
            scan_id if successful, None if storage unavailable or failed
        """    
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
            
            # Upload the report to S3
            self._upload_report_to_s3(scan_id, results)
            
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
    
    def _upload_report_to_s3(self, scan_id: str, results: List[Dict]):
        """Upload the report to S3."""
        try:
            logger.debug(f"Uploading report to S3: {scan_id}")   
            s3 = boto3.resource('s3')
            bucket_name = os.getenv('S3_BUCKET_NAME')
            key = f"scans/{scan_id}.json"
            s3.Bucket(bucket_name).put_object(Key=key, Body=json.dumps(results))
            logger.info(f"Uploaded report to S3: s3://{bucket_name}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload report to S3: {e}", exc_info=True)

    def store_failed_scan(self, git_url: str, error_message: str) -> Optional[str]:
        """
        Store failed scan record.
        
        Returns:
            scan_id if successful, None if storage unavailable or failed
        """
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
