"""
Test Script for Campaign Automation
====================================
Use this to test the automation without needing webhooks
"""

from campaign_automation import NotionJiraAutomation
import json
import sys

def test_with_notion_page(page_id):
    """Test the full automation flow with a real Notion page"""
    print(f"\n🔄 Testing automation with Notion page: {page_id}\n")

    try:
        # Initialize automation
        automation = NotionJiraAutomation()

        # Create test webhook payload
        test_payload = {
            "event": "page_updated",
            "page_id": page_id,
            "properties": {
                "status": {
                    "type": "status",
                    "status": {
                        "name": "Ready for Legal Review"
                    }
                }
            }
        }

        print("📨 Simulating webhook trigger...")
        print(f"Payload: {json.dumps(test_payload, indent=2)}\n")

        # Process the webhook
        result = automation.process_webhook(test_payload)

        # Display result
        if result['status'] == 'success':
            print("✅ SUCCESS!")
            print(f"Campaign: {result.get('campaign_name')}")
            print(f"Jira Ticket: {result.get('jira_ticket_key')}")
            print(f"Jira URL: https://{automation.jira_domain}/browse/{result.get('jira_ticket_key')}")
        elif result['status'] == 'ignored':
            print("⚠️  Webhook ignored (not actionable)")
            print(f"Reason: {result.get('message')}")
        else:
            print("❌ ERROR occurred:")
            print(f"Error: {result.get('error')}")

        return result

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return {"status": "error", "error": str(e)}

def test_fetch_only(page_id):
    """Test fetching Notion data without creating Jira ticket"""
    print(f"\n🔍 Fetching campaign details from Notion page: {page_id}\n")

    try:
        automation = NotionJiraAutomation()
        campaign_details = automation.fetch_campaign_details(page_id)

        print("✅ Successfully fetched campaign details:")
        print(f"  • Campaign Name: {campaign_details['campaign_name']}")
        print(f"  • Copy URL: {campaign_details['copy_url']}")
        print(f"  • Design URL: {campaign_details['design_url']}")

        return campaign_details

    except Exception as e:
        print(f"❌ Failed to fetch: {str(e)}")
        return None

def validate_configuration():
    """Check if all required configuration is present"""
    print("\n🔧 Validating configuration...\n")

    try:
        automation = NotionJiraAutomation()

        configs = [
            ("Notion API Key", automation.notion_api_key, "✅ Set" if automation.notion_api_key else "❌ Missing"),
            ("Jira API Token", automation.jira_api_token, "✅ Set" if automation.jira_api_token else "❌ Missing"),
            ("Jira Username", automation.jira_username, f"✅ {automation.jira_username}" if automation.jira_username else "❌ Missing"),
            ("Jira Domain", automation.jira_domain, f"✅ {automation.jira_domain}" if automation.jira_domain else "❌ Missing"),
            ("Jira Project", automation.jira_project_key, f"✅ {automation.jira_project_key}")
        ]

        all_valid = True
        for name, value, status in configs:
            print(f"  {name}: {status}")
            if "Missing" in status:
                all_valid = False

        print("\n" + "="*50)
        if all_valid:
            print("✅ All configurations are valid!")
        else:
            print("❌ Some configurations are missing. Check your .env file")

        return all_valid

    except Exception as e:
        print(f"❌ Configuration error: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*50)
    print("Campaign Automation Test Script")
    print("="*50)

    # First validate configuration
    if not validate_configuration():
        print("\n⚠️  Please configure your .env file first!")
        sys.exit(1)

    # Check if page_id provided as argument
    if len(sys.argv) > 1:
        page_id = sys.argv[1]
        print(f"\n📄 Using page ID from command line: {page_id}")

        # Ask what to do
        print("\nWhat would you like to test?")
        print("1. Fetch campaign details only (no Jira ticket)")
        print("2. Full automation (create Jira ticket)")
        choice = input("\nEnter choice (1 or 2): ").strip()

        if choice == "1":
            test_fetch_only(page_id)
        elif choice == "2":
            test_with_notion_page(page_id)
        else:
            print("Invalid choice")
    else:
        print("\n📝 Usage:")
        print("  python test_automation.py <notion_page_id>")
        print("\n💡 Example:")
        print("  python test_automation.py a1b2c3d4-e5f6-7890-1234-abcdef123456")
        print("\n🧪 Test with sample data:")
        print("  Using mock page ID for demonstration...")

        # Test with mock data
        mock_page_id = "test-page-12345"
        test_with_notion_page(mock_page_id)