import os
from typing import Dict, List, Optional
import requests
from requests.exceptions import RequestException
import json
import time
import logging

from src.models.issue import Issue, IssueProperty

class PlaneClient:
    def __init__(self):
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Create console handler with formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Load and validate environment variables
        self.api_key = os.getenv('PLANE_API_KEY')
        self.workspace_slug = os.getenv('PLANE_WORKSPACE_SLUG')
        self.project_id = os.getenv('PLANE_PROJECT_ID')
        self.base_url = os.getenv('PLANE_HOST', 'https://lub.11data.de')
        
        # Validate API key format
        if not self.api_key or len(self.api_key) < 32:  # API keys are typically longer
            raise ValueError("Invalid API key format. Please check your PLANE_API_KEY environment variable.")
            
        # Validate other required variables
        if not all([self.workspace_slug, self.project_id]):
            raise ValueError("Missing required environment variables: PLANE_WORKSPACE_SLUG and/or PLANE_PROJECT_ID")
        
        self.retry_delay = 5  # seconds to wait between retries
        self.max_retries = 3  # maximum number of retries
        
        # Configure headers with proper API key format for Plane.so
        self.headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,  # Plane.so uses x-api-key header
            'Accept': '*/*',
            'User-Agent': 'curl/8.7.1'
        }
        
        self.logger.info(f"Initialized PlaneClient for workspace {self.workspace_slug} and project {self.project_id}")
        
        # Validate API connection
        self._validate_api_connection()

    def _validate_api_connection(self):
        """Validate the API connection and token."""
        try:
            # Try to get project details as validation
            response = requests.get(
                f"{self.base_url}/api/v1/workspaces/{self.workspace_slug}/projects/{self.project_id}/",
                headers=self.headers
            )
            
            if response.status_code == 401:
                self.logger.error("Authentication failed. Please check your API key.")
                raise ValueError("Authentication failed. Invalid API key.")
            
            response.raise_for_status()
            self.logger.info("Successfully validated API connection")
            
        except Exception as e:
            self.logger.error(f"API connection validation failed: {str(e)}")
            raise ValueError(f"Failed to validate API connection: {str(e)}")

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a request to the Plane.so API with rate limiting handling."""
        url = f"{self.base_url}/api/v1{endpoint}"
        retries = 0
        
        while retries < self.max_retries:
            try:
                self.logger.debug(f"Making {method} request to {endpoint}")
                self.logger.debug(f"Request headers: {json.dumps(self.headers, indent=2)}")
                if data:
                    self.logger.debug(f"Request data: {json.dumps(data, indent=2)}")
                
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data
                )
                
                # Log response details
                self.logger.debug(f"Response status: {response.status_code}")
                self.logger.debug(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
                if response.text:
                    self.logger.debug(f"Response body: {response.text}")
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    self.logger.warning(f"Rate limited. Waiting {retry_after} seconds before retry...")
                    time.sleep(retry_after)
                    retries += 1
                    continue
                
                if response.status_code in [400, 403]:
                    error_body = response.text
                    # If it's a module exists error, extract the ID
                    if response.status_code == 400 and "Module with this name already exists" in error_body:
                        error_data = json.loads(error_body)
                        self.logger.info(f"Module already exists, returning existing ID")
                        return {"id": error_data["id"]}
                    self.logger.error(f"API error {response.status_code}: {error_body}")
                    raise Exception(f"{response.status_code} Error. Response: {error_body}")
                
                response.raise_for_status()
                
                # For DELETE requests or empty responses, return an empty dict
                if method == 'DELETE' or not response.text:
                    return {}
                    
                response_data = response.json()
                self.logger.debug(f"Request successful. Response length: {len(str(response_data))}")
                return response_data
                
            except RequestException as e:
                if retries < self.max_retries - 1:
                    self.logger.warning(f"Request failed. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    retries += 1
                    continue
                self.logger.error(f"API request failed after {self.max_retries} retries: {str(e)}")
                raise Exception(f"API request failed after {self.max_retries} retries: {str(e)}")
        
        self.logger.error(f"Maximum retries ({self.max_retries}) exceeded")
        raise Exception(f"Maximum retries ({self.max_retries}) exceeded")

    def get_modules(self) -> List[Dict]:
        """Get all modules for the project."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/modules/"
        response = self._make_request('GET', endpoint)
        return response.get('results', [])

    def create_module(self, name: str) -> str:
        """Create a new module or get existing one and return its ID."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/modules/"
        data = {
            "name": name,
            "description": f"Module for {name}"
        }
        try:
            response = self._make_request('POST', endpoint, data)
            return response['id']
        except Exception as e:
            # If the error response contains an ID, it means the module exists
            if hasattr(e, 'response') and e.response.status_code == 400:
                error_data = json.loads(e.response.text)
                if 'id' in error_data:
                    return error_data['id']
            raise

    def get_issue_types(self) -> List[Dict]:
        """Get available issue types for the project."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/issue-types/"
        try:
            response = self._make_request('GET', endpoint)
            return response.get('results', [])
        except Exception as e:
            if "Payment required" in str(e):
                return []
            raise

    def create_issue_property(self, issue_type_id: str, property_data: IssueProperty) -> Dict:
        """Create a new issue property."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/issue-types/{issue_type_id}/issue-properties/"
        return self._make_request('POST', endpoint, property_data.model_dump())

    def create_comment(self, issue_id: str, comment: str) -> Dict:
        """Create a comment on an issue."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/issues/{issue_id}/comments/"
        data = {
            "comment": comment,
            "comment_html": comment,  # Plane.so uses HTML for comments
            "comment_json": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment
                            }
                        ]
                    }
                ]
            }
        }
        return self._make_request('POST', endpoint, data)

    def link_issue_to_module(self, issue_id: str, module_id: str) -> Dict:
        """Link an issue to a module."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/modules/{module_id}/module-issues/"
        data = {
            "issues": [issue_id]  # API expects an array of issue IDs
        }
        return self._make_request('POST', endpoint, data)

    def create_issue(self, issue: Issue) -> Dict:
        """Create a new issue, add description as a comment, and link it to its module."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/issues/"
        data = {
            "name": issue.name,
            "state": "7ee23e4f-6c29-49c6-8220-06991ecd95f2"  # Default state ID from the API response
        }
        response = self._make_request('POST', endpoint, data)
        
        # Add description as a comment if it exists
        if issue.description:
            try:
                self.create_comment(response['id'], issue.description)
            except Exception as e:
                # Log the error but continue - the issue is still created
                print(f"Warning: Could not add description comment: {e}")
        
        # Link the issue to its module
        if issue.module_id:
            self.link_issue_to_module(response['id'], issue.module_id)
        
        return response

    def get_issue_comments(self, issue_id: str) -> List[Dict]:
        """Get all comments for an issue."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/issues/{issue_id}/comments/"
        response = self._make_request('GET', endpoint)
        return response.get('results', [])

    def get_module_issues(self, module_id: str) -> List[Dict]:
        """Get all issues for a module."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/modules/{module_id}/module-issues/"
        response = self._make_request('GET', endpoint)
        self.logger.debug(f"Module issues response: {json.dumps(response, indent=2)}")
        return response.get('results', [])

    def delete_issue(self, issue_id: str) -> None:
        """Delete an issue."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/issues/{issue_id}/"
        self._make_request('DELETE', endpoint)

    def delete_module(self, module_id: str) -> None:
        """Delete a module."""
        endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/modules/{module_id}/"
        self._make_request('DELETE', endpoint)

    def cleanup_project(self) -> None:
        """Delete all issues and modules in the project."""
        # First get all modules
        try:
            modules = self.get_modules()
            self.logger.info(f"Found {len(modules)} modules to clean up")
            
            # For each module, get and delete its issues
            for module in modules:
                module_id = module['id']
                module_name = module['name']
                self.logger.info(f"Processing module: {module_name}")
                
                try:
                    # Get all issues for this module
                    module_issues = self.get_module_issues(module_id)
                    self.logger.info(f"Found {len(module_issues)} issues in module {module_name}")
                    
                    # Delete each issue
                    for module_issue in module_issues:
                        try:
                            # Log the raw module issue data for debugging
                            self.logger.debug(f"Processing module issue: {json.dumps(module_issue, indent=2)}")
                            
                            # The issue data structure can be in different formats:
                            # 1. Direct issue object
                            # 2. Nested under 'issue' key
                            # 3. Nested under 'issue_detail' key
                            issue_data = None
                            if isinstance(module_issue, dict):
                                if 'issue' in module_issue:
                                    issue_data = module_issue['issue']
                                elif 'issue_detail' in module_issue:
                                    issue_data = module_issue['issue_detail']
                                else:
                                    issue_data = module_issue
                            
                            if not issue_data or not isinstance(issue_data, dict):
                                self.logger.warning(f"Skipping invalid issue data: {module_issue}")
                                continue
                                
                            issue_id = issue_data.get('id')
                            issue_name = issue_data.get('name', 'Unknown')
                            
                            if not issue_id:
                                self.logger.warning(f"Skipping issue without ID: {issue_name}")
                                continue
                            
                            self.logger.info(f"Attempting to delete issue: {issue_name} (ID: {issue_id})")
                            self.delete_issue(issue_id)
                            self.logger.info(f"Successfully deleted issue: {issue_name}")
                            
                        except Exception as e:
                            self.logger.error(f"Error deleting issue {issue_name}: {str(e)}")
                            self.logger.debug(f"Full error details: {str(e)}", exc_info=True)
                    
                    # Delete the module after all its issues are processed
                    self.logger.info(f"Attempting to delete module: {module_name} (ID: {module_id})")
                    self.delete_module(module_id)
                    self.logger.info(f"Successfully deleted module: {module_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing module {module_name}: {str(e)}")
                    self.logger.debug(f"Full error details: {str(e)}", exc_info=True)
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            self.logger.debug(f"Full error details: {str(e)}", exc_info=True)
            raise 

    def delete_all_issues_in_project(self) -> None:
        """Delete all issues in the project, regardless of module association."""
        try:
            endpoint = f"/workspaces/{self.workspace_slug}/projects/{self.project_id}/issues/"
            response = self._make_request('GET', endpoint)
            issues = response.get('results', [])
            self.logger.info(f"Found {len(issues)} issues in project to delete.")
            for issue in issues:
                issue_id = issue.get('id')
                issue_name = issue.get('name', 'Unknown')
                if not issue_id:
                    self.logger.warning(f"Skipping issue without ID: {issue}")
                    continue
                try:
                    self.logger.info(f"Attempting to delete issue: {issue_name} (ID: {issue_id})")
                    self.delete_issue(issue_id)
                    self.logger.info(f"Successfully deleted issue: {issue_name}")
                except Exception as e:
                    self.logger.error(f"Error deleting issue {issue_name}: {str(e)}")
                    self.logger.debug(f"Full error details: {str(e)}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Error fetching or deleting issues: {str(e)}")
            self.logger.debug(f"Full error details: {str(e)}", exc_info=True) 