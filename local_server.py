"""
Local Flask Server for Campaign Automation Demo
===============================================
Run this locally to test the Notion-Jira integration
"""

from flask import Flask, request, jsonify
from campaign_automation import NotionJiraAutomation
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    """Home page with instructions"""
    return """
    <h1>Campaign Automation Demo Server</h1>
    <p>This server is running locally for demo purposes.</p>

    <h2>Available Endpoints:</h2>
    <ul>
        <li><b>POST /webhook</b> - Receives Notion webhook events</li>
        <li><b>GET /health</b> - Check if server is running</li>
        <li><b>POST /test</b> - Trigger with test data</li>
    </ul>

    <h2>How to use:</h2>
    <ol>
        <li>Configure your .env file with API keys</li>
        <li>For Notion webhooks, use ngrok to expose this local server</li>
        <li>Or use the /test endpoint to simulate a webhook</li>
    </ol>
    """

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        automation = NotionJiraAutomation()
        is_valid, missing = validate_config(automation)

        if is_valid:
            return jsonify({
                "status": "healthy",
                "message": "All configurations are set",
                "notion_configured": bool(automation.notion_api_key),
                "jira_configured": bool(automation.jira_api_token)
            }), 200
        else:
            return jsonify({
                "status": "unhealthy",
                "message": "Missing configuration",
                "missing_fields": missing
            }), 503
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Main webhook endpoint for Notion events"""
    try:
        payload = request.get_json()

        if not payload:
            return jsonify({
                "status": "error",
                "error": "No JSON payload received"
            }), 400

        logger.info(f"Received webhook payload: {json.dumps(payload, indent=2)}")

        # Process the webhook
        automation = NotionJiraAutomation()
        result = automation.process_webhook(payload)

        logger.info(f"Processing result: {json.dumps(result, indent=2)}")

        # Return result
        status_code = 200 if result['status'] in ['success', 'ignored'] else 500
        return jsonify(result), status_code

    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Webhook handler error: {str(e)}"
        }
        logger.error(f"Webhook error: {str(e)}")
        return jsonify(error_response), 500

@app.route('/test', methods=['POST', 'GET'])
def test_trigger():
    """Test endpoint to manually trigger the automation"""
    if request.method == 'GET':
        return """
        <h2>Test the Automation</h2>
        <form method="POST">
            <label>Page ID: <input name="page_id" placeholder="Notion page ID" required></label><br><br>
            <button type="submit">Trigger Test</button>
        </form>
        """

    try:
        # Get page_id from form or JSON
        if request.content_type == 'application/json':
            data = request.get_json()
            page_id = data.get('page_id')
        else:
            page_id = request.form.get('page_id')

        if not page_id:
            return jsonify({
                "status": "error",
                "error": "page_id is required"
            }), 400

        # Create test payload
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

        logger.info(f"Testing with page_id: {page_id}")

        # Process the test webhook
        automation = NotionJiraAutomation()
        result = automation.process_webhook(test_payload)

        return jsonify(result), 200 if result['status'] == 'success' else 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

def validate_config(automation):
    """Validate that all required config is present"""
    missing = []
    if not automation.notion_api_key:
        missing.append("NOTION_API_KEY")
    if not automation.jira_api_token:
        missing.append("JIRA_API_TOKEN")
    if not automation.jira_username:
        missing.append("JIRA_USERNAME")
    if not automation.jira_domain:
        missing.append("JIRA_DOMAIN")

    return len(missing) == 0, missing

if __name__ == "__main__":
    print("\n🚀 Starting Campaign Automation Demo Server...")
    print("📍 Server running at: http://localhost:5000")
    print("📋 Health check: http://localhost:5000/health")
    print("🧪 Test trigger: http://localhost:5000/test")
    print("\nPress CTRL+C to stop the server\n")

    app.run(debug=True, port=5000)