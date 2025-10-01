# Notion to Jira Campaign Automation

Automate the handoff of marketing campaigns from Creative to Legal teams by automatically creating Jira tickets when Notion campaigns are marked as "Ready for Legal Review".

## Overview

This serverless automation integrates Notion and Jira to streamline the campaign review process:
- Monitors Notion database for status changes
- Triggers when a campaign is marked "Ready for Legal Review"
- Creates a formatted Jira ticket with campaign details and review materials
- Runs on Google Cloud Functions for reliability and scalability

## Features

- **Automatic Ticket Creation**: Creates Jira tickets instantly when campaigns need legal review
- **Rich Formatting**: Well-structured Jira descriptions with headings, links, and bullet points
- **Serverless Architecture**: No servers to maintain, scales automatically
- **Environment-Based Config**: Secure API key management using environment variables
- **Error Handling**: Comprehensive logging and error reporting

## Prerequisites

- Notion account with API access (Plus plan or higher for automations)
- Jira account with API token
- Google Cloud Platform account with billing enabled
- Python 3.11+
- gcloud CLI installed

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd block
```

### 2. Configure Notion

1. **Create a Notion Integration**
   - Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
   - Click "New integration"
   - Give it a name (e.g., "Campaign Automation")
   - Copy the API key (starts with `secret_`)

2. **Set Up Your Campaign Database**

   Required fields in your Notion database:
   - **Name** (Title): Campaign name
   - **Status** (Status): Must include "Ready for Legal Review" option
   - **Final Copy URL** (URL): Link to final copy documents
   - **Final Design URL** (URL): Link to final design assets

3. **Connect Integration to Database**
   - Open your campaign database in Notion
   - Click the "..." menu → "Connections"
   - Add your integration

### 3. Configure Jira

1. **Generate API Token**
   - Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Click "Create API token"
   - Give it a name and copy the token

2. **Note Your Jira Details**
   - Domain: `yourcompany.atlassian.net`
   - Username: Your email address
   - Project Key: The key for your project (e.g., "MKTG", "MCP")

### 4. Set Up Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```bash
   NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxx
   JIRA_API_TOKEN=ATATT3xFfGF0xxxxxxxxxxxxx
   JIRA_USERNAME=your.email@company.com
   JIRA_DOMAIN=yourcompany.atlassian.net
   JIRA_PROJECT_KEY=MKTG
   ```

### 5. Deploy to Google Cloud Functions

1. **Install Google Cloud CLI**
   ```bash
   brew install google-cloud-sdk  # macOS
   # Or visit: https://cloud.google.com/sdk/docs/install
   ```

2. **Initialize and Configure GCP**
   ```bash
   gcloud auth login
   gcloud projects create notion-jira-auto --name="Notion Jira Automation"
   gcloud config set project notion-jira-auto
   ```

3. **Enable Required Services**
   ```bash
   gcloud services enable cloudfunctions.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

4. **Deploy the Function**
   ```bash
   gcloud functions deploy notion-jira-webhook \
     --runtime python311 \
     --trigger-http \
     --allow-unauthenticated \
     --entry-point notion_jira_webhook \
     --source . \
     --project notion-jira-auto \
     --region us-central1
   ```

5. **Set Environment Variables in GCP Console**
   - Go to [Cloud Functions Console](https://console.cloud.google.com/functions)
   - Click on your function
   - Click "EDIT"
   - Under "Runtime environment variables", add your keys
   - Click "NEXT" and "DEPLOY"

### 6. Configure Notion Automation

1. **Open Your Notion Database**
   - Click the lightning bolt icon (⚡) for Automations
   - Click "New automation"

2. **Set Up the Trigger**
   - Trigger: "Page property edited"
   - Property: "Status"
   - Filter: Status is "Ready for Legal Review"

3. **Add Webhook Action**
   - Add action: "Send webhook"
   - URL: `https://us-central1-notion-jira-auto.cloudfunctions.net/notion-jira-webhook`
   - Method: POST
   - Body: Include page content
   - Headers: Add a custom header (e.g., `X-Source: Notion`)

4. **Enable the Automation**
   - Toggle the automation ON
   - Test by changing a campaign status

## Testing

### Local Testing (Optional)

1. **Install Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install flask  # For local testing only
   ```

2. **Run Local Server**
   ```bash
   python local_server.py
   ```

3. **Test Endpoints**
   - Health check: `http://localhost:5000/health`
   - Test creation: `http://localhost:5000/test`

### Production Testing

1. **Test with cURL**
   ```bash
   curl -X POST https://us-central1-notion-jira-auto.cloudfunctions.net/notion-jira-webhook \
     -H "Content-Type: application/json" \
     -d '{
       "data": {
         "id": "test-page-id",
         "properties": {
           "Name": {"title": [{"plain_text": "Test Campaign"}]},
           "Status": {"status": {"name": "Ready for Legal Review"}},
           "Final Copy URL": {"url": "https://docs.google.com/test-copy"},
           "Final Design URL": {"url": "https://figma.com/test-design"}
         }
       }
     }'
   ```

2. **Test End-to-End**
   - Create or edit a campaign in Notion
   - Change status to "Ready for Legal Review"
   - Check Jira for the new ticket
   - Verify formatting and links

## Troubleshooting

### Common Issues

1. **Notion Automation Not Triggering**
   - Ensure you're on Notion Plus plan or higher
   - Check automation is enabled (toggle ON)
   - Avoid hyphens in custom header names
   - Try email action first to verify automation works

2. **401 Unauthorized (Notion)**
   - Verify API key starts with `secret_`
   - Check integration is connected to database
   - Ensure API key has no line breaks

3. **401/403 Errors (Jira)**
   - Verify API token is correct
   - Check username is your email address
   - Ensure user has permission to create issues in project

4. **400 Bad Request (Jira)**
   - Check project key exists
   - Verify issue type "Task" is available
   - Ensure required fields are provided

### Viewing Logs

```bash
gcloud functions logs read notion-jira-webhook --limit 50
```

## Project Structure

```
block/
├── main.py              # Cloud Function entry point
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (git ignored)
├── .env.example         # Environment template
├── .gitignore          # Git ignore rules
├── README.md           # This file
└── local_server.py     # Local testing server (optional)
```

## Security Notes

- Never commit `.env` files to version control
- Use GCP environment variables for production
- Rotate API keys periodically
- Consider restricting Cloud Function access in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT

## Support

For issues or questions, please open a GitHub issue or contact your DevOps team.