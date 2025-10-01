"""
Google Cloud Function Entry Point
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CampaignAutomationError(Exception):
    """Custom exception for campaign automation errors"""
    pass


class NotionJiraAutomation:
    """
    Main automation class that handles the Notion to Jira workflow
    """

    def __init__(self):
        """Initialize with environment variables and validate configuration"""
        self.notion_api_key = self._get_env_var("NOTION_API_KEY")
        self.jira_api_token = self._get_env_var("JIRA_API_TOKEN")
        self.jira_domain = self._get_env_var("JIRA_DOMAIN")
        self.jira_project_key = self._get_env_var("JIRA_PROJECT_KEY", default="MKTG")
        self.jira_username = self._get_env_var("JIRA_USERNAME")

        # API endpoints
        self.notion_api_base = "https://api.notion.com/v1"
        self.jira_api_base = f"https://{self.jira_domain}/rest/api/3"

        # Headers for API requests (using stable API version)
        self.notion_headers = {
            "Authorization": f"Bearer {self.notion_api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"  # Using stable version, latest is 2025-09-03
        }

        logger.info("CampaignAutomation initialized successfully")

    def _get_env_var(self, var_name: str, default: Optional[str] = None) -> str:
        """
        Safely retrieve environment variables with validation
        """
        value = os.getenv(var_name, default)
        if value is None:
            raise CampaignAutomationError(f"Required environment variable {var_name} is not set")
        return value

    def validate_webhook_payload(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate the incoming Notion webhook payload
        """
        try:
            # Handle Notion automation webhook format
            if "data" in payload:
                data = payload.get("data", {})
                page_id = data.get("id")
                properties = data.get("properties", {})

                # Check if status is "Ready for Legal Review"
                status_prop = properties.get("Status", {})
                status_obj = status_prop.get("status", {})
                status_name = status_obj.get("name")

                if status_name != "Ready for Legal Review":
                    logger.info(f"Status is '{status_name}', not 'Ready for Legal Review'. Ignoring.")
                    return False, None

                logger.info(f"Valid webhook payload for page {page_id} with status 'Ready for Legal Review'")
                return True, page_id

            # Handle test format (backwards compatibility)
            elif payload.get("event") == "page_updated":
                page_id = payload.get("page_id")
                if not page_id:
                    logger.error("Missing page_id in webhook payload")
                    return False, None

                properties = payload.get("properties", {})
                status_prop = properties.get("status", {})
                status_obj = status_prop.get("status", {})
                status_name = status_obj.get("name")

                if status_name != "Ready for Legal Review":
                    logger.info(f"Status is '{status_name}', not 'Ready for Legal Review'. Ignoring.")
                    return False, None

                return True, page_id

            else:
                logger.info("Unrecognized webhook format")
                return False, None

        except Exception as e:
            logger.error(f"Error validating webhook payload: {str(e)}")
            return False, None

    def fetch_campaign_details(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch full campaign details from Notion
        """
        try:
            url = f"{self.notion_api_base}/pages/{page_id}"
            response = requests.get(url, headers=self.notion_headers, timeout=30)

            if response.status_code != 200:
                raise CampaignAutomationError(
                    f"Failed to fetch Notion page. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )

            page_data = response.json()
            logger.info(f"Successfully fetched page data for {page_id}")

            # Extract required properties
            properties = page_data.get("properties", {})

            # Get campaign name (assuming it's the page title)
            title_prop = properties.get("Name") or properties.get("title") or {}
            title_content = title_prop.get("title", [])
            campaign_name = ""
            if title_content:
                campaign_name = "".join([t.get("plain_text", "") for t in title_content])

            # Get Final Copy URL
            copy_url_prop = properties.get("Final Copy URL", {})
            copy_url = copy_url_prop.get("url") or copy_url_prop.get("rich_text", [{}])[0].get("plain_text", "")

            # Get Final Design URL
            design_url_prop = properties.get("Final Design URL", {})
            design_url = design_url_prop.get("url") or design_url_prop.get("rich_text", [{}])[0].get("plain_text", "")

            # Validate required fields
            if not campaign_name:
                raise CampaignAutomationError("Campaign name is missing or empty")
            if not copy_url:
                raise CampaignAutomationError("Final Copy URL is missing or empty")
            if not design_url:
                raise CampaignAutomationError("Final Design URL is missing or empty")

            campaign_details = {
                "campaign_name": campaign_name.strip(),
                "copy_url": copy_url.strip(),
                "design_url": design_url.strip()
            }

            logger.info(f"Campaign details extracted: {campaign_name}")
            return campaign_details

        except requests.RequestException as e:
            raise CampaignAutomationError(f"Network error fetching Notion page: {str(e)}")
        except Exception as e:
            raise CampaignAutomationError(f"Error fetching campaign details: {str(e)}")

    def create_jira_payload(self, campaign_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform campaign data into Jira API payload format
        """
        campaign_name = campaign_details["campaign_name"]
        copy_url = campaign_details["copy_url"]
        design_url = campaign_details["design_url"]

        # Create the Jira payload with the exact structure specified
        jira_payload = {
            "fields": {
                "project": {
                    "key": self.jira_project_key
                },
                "summary": f"{campaign_name} - Legal Review",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "heading",
                            "attrs": {
                                "level": 3
                            },
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Campaign Legal Review Request"
                                }
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Campaign \"{campaign_name}\" is ready for legal and compliance review."
                                }
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": []
                        },
                        {
                            "type": "heading",
                            "attrs": {
                                "level": 4
                            },
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Review Materials:",
                                    "marks": [
                                        {
                                            "type": "strong"
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "bulletList",
                            "content": [
                                {
                                    "type": "listItem",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Final Copy: ",
                                                    "marks": [
                                                        {
                                                            "type": "strong"
                                                        }
                                                    ]
                                                },
                                                {
                                                    "type": "text",
                                                    "text": copy_url,
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": copy_url
                                                            }
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "type": "listItem",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "Final Design: ",
                                                    "marks": [
                                                        {
                                                            "type": "strong"
                                                        }
                                                    ]
                                                },
                                                {
                                                    "type": "text",
                                                    "text": design_url,
                                                    "marks": [
                                                        {
                                                            "type": "link",
                                                            "attrs": {
                                                                "href": design_url
                                                            }
                                                        }
                                                    ]
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": []
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Please review for compliance with legal requirements and brand guidelines.",
                                    "marks": [
                                        {
                                            "type": "em"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": "Task"
                }
            }
        }

        logger.info(f"Created Jira payload for campaign: {campaign_name}")
        return jira_payload

    def create_jira_ticket(self, jira_payload: Dict[str, Any]) -> str:
        """
        Create a Jira ticket using the API
        """
        try:
            url = f"{self.jira_api_base}/issue"
            auth = (self.jira_username, self.jira_api_token)
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            response = requests.post(
                url,
                json=jira_payload,
                headers=headers,
                auth=auth,
                timeout=30
            )

            if response.status_code not in [200, 201]:
                raise CampaignAutomationError(
                    f"Failed to create Jira ticket. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )

            response_data = response.json()
            ticket_key = response_data.get("key")

            if not ticket_key:
                raise CampaignAutomationError("Jira ticket created but no key returned")

            logger.info(f"Successfully created Jira ticket: {ticket_key}")
            return ticket_key

        except requests.RequestException as e:
            raise CampaignAutomationError(f"Network error creating Jira ticket: {str(e)}")
        except Exception as e:
            raise CampaignAutomationError(f"Error creating Jira ticket: {str(e)}")

    def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing function for webhook events
        """
        try:
            # Step 1: Validate webhook payload
            is_valid, page_id = self.validate_webhook_payload(payload)
            if not is_valid:
                return {
                    "status": "ignored",
                    "message": "Webhook payload validation failed or not actionable"
                }

            # Step 2: Fetch campaign details from Notion
            logger.info(f"Processing campaign automation for page: {page_id}")
            campaign_details = self.fetch_campaign_details(page_id)

            # Step 3: Transform data for Jira
            jira_payload = self.create_jira_payload(campaign_details)

            # Step 4: Create Jira ticket
            ticket_key = self.create_jira_ticket(jira_payload)

            # Step 5: Log success and return result
            success_message = (
                f"Successfully processed campaign '{campaign_details['campaign_name']}'. "
                f"Created Jira ticket: {ticket_key} for Notion page: {page_id}"
            )
            logger.info(success_message)

            return {
                "status": "success",
                "notion_page_id": page_id,
                "campaign_name": campaign_details['campaign_name'],
                "jira_ticket_key": ticket_key,
                "message": success_message
            }

        except CampaignAutomationError as e:
            error_message = f"Campaign automation error: {str(e)}"
            logger.error(error_message)
            return {
                "status": "error",
                "error": error_message,
                "notion_page_id": page_id if 'page_id' in locals() else None
            }
        except Exception as e:
            error_message = f"Unexpected error in campaign automation: {str(e)}"
            logger.error(error_message)
            return {
                "status": "error",
                "error": error_message,
                "notion_page_id": page_id if 'page_id' in locals() else None
            }


def notion_jira_webhook(request):
    """Google Cloud Function entry point"""
    try:
        # Parse the incoming payload
        payload = request.get_json()
        if not payload:
            return json.dumps({
                'status': 'error',
                'error': 'No JSON payload received'
            }), 400

        # Initialize automation and process
        automation = NotionJiraAutomation()
        result = automation.process_webhook(payload)

        # Return appropriate HTTP response
        status_code = 200 if result['status'] in ['success', 'ignored'] else 500
        return json.dumps(result), status_code

    except Exception as e:
        error_response = {
            'status': 'error',
            'error': f'Cloud Function handler error: {str(e)}'
        }
        logger.error(f"Cloud Function handler error: {str(e)}")
        return json.dumps(error_response), 500