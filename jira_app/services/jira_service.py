import os
import requests
import json
from django.conf import settings

class JiraService:
    def __init__(self):
        self.base_url = os.environ.get('JIRA_URL')
        self.email = os.environ.get('JIRA_EMAIL')
        self.api_token = os.environ.get('JIRA_API_TOKEN')
        self.auth = (self.email, self.api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_stories_for_epic(self, epic_key):
        """
        Fetch all stories linked to an Epic (using JQL).
        """
        if not self.base_url or not self.email or not self.api_token:
            # Mock data for demonstration when no credentials are present
            return [
                {'key': 'MOCK-101', 'summary': 'User should see error on login fail', 'description': 'As a user...'},
                {'key': 'MOCK-102', 'summary': 'Add logging for system failures', 'description': 'We need logs...'},
                {'key': 'MOCK-103', 'summary': 'Update user profile UI', 'description': 'Profile page needs refresh...'},
            ]

        url = f"{self.base_url}/rest/api/3/search/jql"
        jql = f"parent = {epic_key} AND issuetype = Story"
        
        payload = {
            'jql': jql,
            'fields': ['summary', 'description']
        }

        try:
            response = requests.post(
                url, headers=self.headers, json=payload, auth=self.auth
            )
            response.raise_for_status()
            issues = response.json().get('issues', [])
            
            stories = []
            for issue in issues:
                desc_raw = issue['fields'].get('description')
                desc_html = self._adf_to_html(desc_raw)
                stories.append({
                    'key': issue['key'],
                    'summary': issue['fields']['summary'],
                    'description': desc_html
                })
            return stories
        except Exception as e:
            print(f"Error fetching stories: {e}")
            return []

    def create_task(self, parent_epic_key, task_data):
        if not self.base_url:
             return {"key": "MOCK-TASK-NEW", "self": "http://mock/task/new"}

        project_key = parent_epic_key.split('-')[0]

        adf_content = self._create_adf_content(task_data)

        payload = {
            "fields": {
                "project": { "key": project_key },
                "summary": task_data.get('summary'),
                "description": adf_content,
                "issuetype": { "name": "Task" },
                "parent": { "key": parent_epic_key } 
            }
        }
        
        url = f"{self.base_url}/rest/api/3/issue"
        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(payload), auth=self.auth)
            # 400 errors often mean ADF format issues, print them
            if response.status_code >= 400:
                print(f"Jira Error {response.status_code}: {response.text}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating task: {e}")
            return None

    def _create_adf_content(self, data):
        """Constructs Jira ADF content with tables and formatting."""
        content = []

        # Description
        if data.get('description'):
            content.append(self._adf_paragraph(data['description']))

        # Acceptance Criteria
        if data.get('acceptance_criteria'):
            content.append(self._adf_heading("Acceptance Criteria"))
            content.append(self._adf_bullet_list(data['acceptance_criteria']))

        # Tech Stack
        if data.get('tech_stack'):
            content.append(self._adf_heading("Tech Stack"))
            content.append(self._adf_bullet_list(data['tech_stack']))

        # API Endpoints (Table)
        if data.get('api_endpoints'):
            content.append(self._adf_heading("API Endpoints"))
            content.append(self._adf_api_table(data['api_endpoints']))

        # cURL
        if data.get('api_curl'):
            content.append(self._adf_heading("Example Request"))
            content.append({
                "type": "codeBlock",
                "attrs": { "language": "bash" },
                "content": [{ "type": "text", "text": data['api_curl'] }]
            })

        # DB Schema (Table)
        if data.get('database_schema'):
            content.append(self._adf_heading("Database Schema"))
            content.append(self._adf_db_table(data['database_schema']))
            
        # Infrastructure
        if data.get('infrastructure'):
            content.append(self._adf_heading("Infrastructure"))
            content.append(self._adf_bullet_list(data['infrastructure']))

        return {
            "type": "doc",
            "version": 1,
            "content": content
        }

    def _adf_paragraph(self, text):
        return {
            "type": "paragraph",
            "content": [{ "type": "text", "text": text }]
        }

    def _adf_heading(self, text, level=3):
        return {
            "type": "heading",
            "attrs": { "level": level },
            "content": [{ "type": "text", "text": text }]
        }

    def _adf_bullet_list(self, items):
        if not items: return self._adf_paragraph("None")
        return {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [ self._adf_paragraph(item) ]
                } for item in items
            ]
        }

    def _adf_api_table(self, apis):
        if not isinstance(apis, list): return self._adf_paragraph(str(apis))
        
        rows = []
        # Header
        rows.append({
            "type": "tableRow",
            "content": [
                { "type": "tableHeader", "content": [ self._adf_paragraph("Method") ] },
                { "type": "tableHeader", "content": [ self._adf_paragraph("Endpoint") ] },
                { "type": "tableHeader", "content": [ self._adf_paragraph("Description") ] }
            ]
        })
        # Data
        for api in apis:
            if isinstance(api, dict):
                rows.append({
                    "type": "tableRow",
                    "content": [
                        { "type": "tableCell", "content": [ self._adf_paragraph(api.get("method", "")) ] },
                        { "type": "tableCell", "content": [ self._adf_paragraph(api.get("endpoint", "")) ] },
                        { "type": "tableCell", "content": [ self._adf_paragraph(api.get("description", "")) ] }
                    ]
                })
        return { "type": "table", "content": rows }

    def _adf_db_table(self, schema):
        if not isinstance(schema, list): return self._adf_paragraph(str(schema))
        
        rows = []
        rows.append({
            "type": "tableRow",
            "content": [
                { "type": "tableHeader", "content": [ self._adf_paragraph("Table") ] },
                { "type": "tableHeader", "content": [ self._adf_paragraph("Columns") ] }
            ]
        })
        for item in schema:
            if isinstance(item, dict):
                cols = item.get("columns", [])
                if isinstance(cols, list): cols = ", ".join(cols)
                rows.append({
                    "type": "tableRow",
                    "content": [
                        { "type": "tableCell", "content": [ self._adf_paragraph(item.get("table", "")) ] },
                        { "type": "tableCell", "content": [ self._adf_paragraph(str(cols)) ] }
                    ]
                })
        return { "type": "table", "content": rows }

    def _adf_to_html(self, content_node):
        """Converts Atlassian Document Format (ADF) to HTML."""
        if not content_node:
            return ""
            
        if isinstance(content_node, str):
            return content_node
            
        node_type = content_node.get('type')
        content = content_node.get('content', [])
        
        html_parts = []
        
        # Process children
        for child in content:
            html_parts.append(self._adf_to_html(child))
            
        inner_html = "".join(html_parts)
        
        if node_type == 'doc':
            return inner_html
        elif node_type == 'paragraph':
            return f"<p>{inner_html}</p>"
        elif node_type == 'text':
            return content_node.get('text', '')
        elif node_type == 'bulletList':
            return f"<ul>{inner_html}</ul>"
        elif node_type == 'orderedList':
            return f"<ol>{inner_html}</ol>"
        elif node_type == 'listItem':
            return f"<li>{inner_html}</li>"
        elif node_type == 'heading':
            level = content_node.get('attrs', {}).get('level', 3)
            return f"<h{level}>{inner_html}</h{level}>"
        elif node_type == 'codeBlock':
             return f"<pre><code>{inner_html}</code></pre>"
        else:
            return inner_html
