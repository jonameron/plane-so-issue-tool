#!/usr/bin/env python3
import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

from src.api.plane_client import PlaneClient
from src.models.issue import Issue, Module, ModuleIssue

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_work_packages(file_path: str) -> Dict[str, List[ModuleIssue]]:
    """Load work packages from JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            # Convert the data to our expected format
            return {
                module_name: [
                    ModuleIssue(
                        body=issue["name"] if isinstance(issue, dict) else issue,
                        description=issue["description"] if isinstance(issue, dict) else f"Task: {issue}"
                    )
                    for issue in issues
                ]
                for module_name, issues in data.items()
            }
    except Exception as e:
        logger.error(f"Error loading work packages: {e}")
        raise

def export_issues(client: PlaneClient, output_file: str):
    """Export all issues and their comments to a JSON file."""
    try:
        # Get all modules
        modules = client.get_modules()
        export_data = {}
        
        for module in modules:
            module_id = module['id']
            module_name = module['name']
            export_data[module_name] = []
            
            # Get all issues for this module
            module_issues = client.get_module_issues(module_id)
            for issue in module_issues:
                issue_id = issue['id']
                # Get comments for this issue
                comments = client.get_issue_comments(issue_id)
                
                # Add issue with its comments to the export data
                export_data[module_name].append({
                    'name': issue['name'],
                    'id': issue_id,
                    'comments': [
                        {
                            'text': comment['comment'],
                            'created_at': comment['created_at']
                        }
                        for comment in comments
                    ]
                })
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported issues and comments to {output_file}")
        
    except Exception as e:
        logger.error(f"Error exporting issues: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Create Plane.so modules and issues from work packages')
    parser.add_argument('--input', help='Path to work packages JSON file')
    parser.add_argument('--dry-run', action='store_true', help='Simulate the process without making API calls')
    parser.add_argument('--export', help='Export issues and comments to JSON file')
    parser.add_argument('--cleanup', action='store_true', help='Delete all issues and modules')
    parser.add_argument('--delete-all-issues', action='store_true', help='Delete all issues in the project (regardless of module)')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Debug printout of loaded environment variables
    api_key = os.getenv('PLANE_API_KEY', '')
    logger.debug(f"Loaded PLANE_API_KEY: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key else 'None'}")
    logger.debug(f"Loaded PLANE_WORKSPACE_SLUG: {os.getenv('PLANE_WORKSPACE_SLUG')}")
    logger.debug(f"Loaded PLANE_PROJECT_ID: {os.getenv('PLANE_PROJECT_ID')}")
    logger.debug(f"Loaded PLANE_HOST: {os.getenv('PLANE_HOST')}")

    # Validate required environment variables
    required_env_vars = ['PLANE_API_KEY', 'PLANE_WORKSPACE_SLUG', 'PLANE_PROJECT_ID', 'PLANE_HOST']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return

    try:
        client = PlaneClient()
        
        if args.cleanup:
            logger.info("Cleaning up project - deleting all issues and modules")
            client.cleanup_project()
            return
            
        if args.export:
            export_issues(client, args.export)
            return
            
        if args.delete_all_issues:
            logger.info("Deleting all issues in the project (regardless of module association)")
            client.delete_all_issues_in_project()
            return
            
        if not args.input:
            logger.error("Input file is required when not exporting")
            return
            
        work_packages = load_work_packages(args.input)
        logger.info(f"Loaded {len(work_packages)} work packages")
        
        if args.dry_run:
            logger.info("Dry run mode - no API calls will be made")
            for module, issues in work_packages.items():
                logger.info(f"Would create module: {module}")
                for issue in issues:
                    logger.info(f"  Would create issue: {issue.body}")
                    logger.info(f"    Description: {issue.description}")
        else:
            # Try to get issue types, but continue if not available
            try:
                issue_types = client.get_issue_types()
                issue_type_id = issue_types[0]['id'] if issue_types else None
                if issue_type_id:
                    logger.info(f"Using issue type ID: {issue_type_id}")
            except Exception as e:
                logger.warning(f"Could not fetch issue types, continuing without them: {e}")
                issue_type_id = None
            
            for module_name, issues in work_packages.items():
                # Create module
                try:
                    module_id = client.create_module(module_name)
                    logger.info(f"Created module: {module_name} (ID: {module_id})")
                    
                    # Create issues for the module
                    for module_issue in issues:
                        issue = Issue(
                            name=module_issue.body,
                            description=module_issue.description,
                            module_id=module_id
                        )
                        created_issue = client.create_issue(issue)
                        logger.info(f"Created issue: {issue.name} (ID: {created_issue['id']})")
                except Exception as e:
                    logger.error(f"Error processing module {module_name}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Error processing work packages: {e}")
        return

if __name__ == '__main__':
    main() 