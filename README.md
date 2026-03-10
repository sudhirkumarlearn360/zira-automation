# Zira Automation (Jira + AI Task Generator)

A Django-based web application designed to automate and streamline the agile workflow by generating detailed technical Jira Sub-tasks directly from User Stories using AI (OpenAI or Google Gemini).

## 🚀 Features

* **Epic & Story Dashboard**: View all current Epics and drill down into their associated stories right from the UI.
* **AI-Powered Task Generation**: Automatically generate comprehensive Backend, Frontend, and QA testing plans based on a Story's description.
* **Two-Step Preview Workflow**: Review and manually edit the AI-generated JSON technical plan in a user-friendly HTML form before committing it to Jira.
* **Highly Flexible Context Parsing**: Provide raw data like cURL commands, SQL schemas, or SEO requirements in the 'Additional Context' box. The AI will dynamically categorize them, and the backend will automatically map them perfectly into Atlassian Document Format (ADF) as Jira Code Blocks, Tables, or Lists.
* **Dual AI Support**: Configure the application to use either OpenAI (GPT-4) or Google Gemini (Flash/Pro) based on your preference and rate limits.

## 🛠️ Tech Stack

* **Backend**: Python, Django
* **Frontend**: Vanilla HTML/CSS/JS (Django Templates)
* **Integrations**: Jira Cloud REST API, OpenAI API, Google Gemini API

## ⚙️ Setup Instructions

### 1. Prerequisites
Ensure you have Python 3.9+ installed and pip available.

### 2. Environment Variables
Create a `.env` file in the root directory (alongside `manage.py`) using `.env.example` as a template. You must configure the following:

```env
# Jira Configuration
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=PROJ

# AI Configuration (OpenAI OR Gemini)
AI_PROVIDER=OPENAI # or GEMINI
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
AI_MODEL=gpt-4o # or gemini-2.5-flash
```

### 3. Installation
Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Running the Application
Apply migrations and start the Django development server:
```bash
python manage.py migrate
python manage.py runserver
```

## 📖 Usage

1. Open your browser and navigate to `http://127.0.0.1:8000/jira/`.
2. Browse your Epics and Stories on the dashboard.
3. To generate tasks for a specific story, navigate to `http://127.0.0.1:8000/jira/stories/`.
4. Enter the Story Key (e.g., `CAR-123`).
5. Select a Task Scope (Backend, Frontend, Bug, QA).
6. *(Optional)* Provide specific technical instructions, cURLs, or table schema data in the **Additional Context** box.
7. Click **Generate Preview**.
8. Review the parsed Technical Plan in the rendered form inputs. Make any manual adjustments if necessary.
9. Click **Confirm & Create Task in Jira** to instantly publish the structured sub-task to your Jira board.
