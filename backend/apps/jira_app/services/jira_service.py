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

    def get_story_details(self, story_key):
        """
        Fetch single story details including subtasks.
        """
        if not self.base_url:
            return {
                'key': story_key, 
                'summary': 'Mock Story Details', 
                'description': '<p>Mock description for offline mode.</p>',
                'subtasks': []
            }

        url = f"{self.base_url}/rest/api/3/issue/{story_key}"
        try:
            response = requests.get(url, headers=self.headers, auth=self.auth)
            response.raise_for_status()
            data = response.json()
            
            fields = data['fields']
            desc_raw = fields.get('description')
            desc_html = self._adf_to_html(desc_raw)
            
            # Extract subtasks
            subtasks = []
            for sub in fields.get('subtasks', []):
                subtasks.append({
                    'key': sub['key'],
                    'summary': sub['fields']['summary'],
                    'status': sub['fields']['status']['name']
                })

            return {
                'key': data['key'],
                'summary': fields['summary'],
                'description': desc_html,
                'status': fields['status']['name'],
                'subtasks': subtasks,
                'project_key': fields['project']['key']
            }
        except Exception as e:
            print(f"Error fetching story details: {e}")
            return None

    def create_task(self, task_data, parent_key=None, project_key=None):
        if not self.base_url:
             return {"key": "MOCK-TASK-NEW", "self": "http://mock/task/new"}
             
        # Defensive handling if AI returns a list of tasks instead of a single dict
        if isinstance(task_data, list):
            task_data = task_data[0] if len(task_data) > 0 else {}

        # Determine project key logic: explicit > from parent > fallback
        if not project_key and parent_key:
            project_key = parent_key.split('-')[0]
        elif not project_key:
            project_key = "CAR" # Fallback or fetch from settings

        adf_content = self._create_adf_content(task_data)

        # Base fields
        fields = {
            "project": { "key": project_key },
            "summary": task_data.get('summary', 'New Task'),
            "description": adf_content
        }

        # Handle Hierarchy:
        # If we have a parent key, and it's a story (e.g., from /stories/ generate flow)
        # we likely need to create a "Sub-task" instead of "Task"
        if parent_key:
            fields["parent"] = { "key": parent_key }
            fields["issuetype"] = { "name": "Sub-task" }
        else:
            fields["issuetype"] = { "name": "Task" }

        payload = {
            "fields": fields
        }
        
        url = f"{self.base_url}/rest/api/3/issue"
        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(payload), auth=self.auth)
            
            # Retroactively handle cases where Sub-task is rejected or Task parent link is rejected
            if response.status_code == 400:
                print(f"Jira Error 400: {response.text}. Attempting fallback...")
                
                # If Sub-task failed, maybe try Task?
                if fields["issuetype"]["name"] == "Sub-task":
                    fields["issuetype"]["name"] = "Task"
                    response = requests.post(url, headers=self.headers, data=json.dumps({"fields": fields}), auth=self.auth)
                
                # If it still failed or was Task originally, try stripping parent
                if response.status_code == 400 and "parent" in fields:
                     del fields["parent"]
                     response = requests.post(url, headers=self.headers, data=json.dumps({"fields": fields}), auth=self.auth)
                 
            if response.status_code >= 400:
                print(f"Jira Error {response.status_code}: {response.text}")
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating task: {e}")
            return None

    def _create_adf_content(self, data):
        """Constructs Jira ADF content dynamically from parsed JSON."""
        if isinstance(data, list):
            data = data[0] if len(data) > 0 else {}
            
        content = []

        # Description ALWAYS comes first if present
        desc_text = data.get('description')
        if desc_text and isinstance(desc_text, str):
            content.append(self._adf_paragraph(desc_text))

        reserved_keys = ['summary', 'description']

        for key, value in data.items():
            if key in reserved_keys or not value:
                continue

            # Format the heading (e.g., 'api_endpoints' -> 'Api Endpoints')
            heading_title = key.replace('_', ' ').title()
            content.append(self._adf_heading(heading_title))

            if isinstance(value, str):
                # Heuristic for code blocks
                if key.endswith('curl') or value.strip().startswith(('curl ', 'SELECT ', '{', '[')):
                    lang = 'bash' if 'curl' in key.lower() else ('sql' if 'sql' in key.lower() else 'json')
                    content.append({
                        "type": "codeBlock",
                        "attrs": { "language": lang },
                        "content": [{ "type": "text", "text": value }]
                    })
                else:
                    paragraphs = [p for p in value.split('\n\n') if p.strip()]
                    if not paragraphs: paragraphs = [value]
                    for p in paragraphs:
                        content.append(self._adf_paragraph(p.strip()))

            elif isinstance(value, list) and len(value) > 0:
                # List of strings -> Bullet list
                if all(isinstance(item, str) for item in value):
                    content.append(self._adf_bullet_list(value))
                # List of dicts -> Table
                elif all(isinstance(item, dict) for item in value):
                    headers = []
                    for item in value:
                        for k in item.keys():
                            if k not in headers: headers.append(k)
                    
                    if headers:
                        display_headers = [h.replace('_', ' ').title() for h in headers]
                        content.append(self._create_table_adf(display_headers, value, headers))
                    else:
                        content.append(self._adf_paragraph("Empty records"))
                else:
                    # Fallback mixed list
                    content.append(self._adf_paragraph(str(value)))
                    
            elif isinstance(value, dict):
                content.append({
                    "type": "codeBlock",
                    "attrs": { "language": "json" },
                    "content": [{ "type": "text", "text": json.dumps(value, indent=2) }]
                })

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

    def _create_table_adf(self, headers, items, keys):
        if not items or not isinstance(items, list):
            return self._adf_paragraph("No items provided.")
            
        rows = []
        # Header Row
        header_cells = [
            {
                "type": "tableHeader",
                "content": [ self._adf_paragraph(h) ]
            } for h in headers
        ]
        rows.append({ "type": "tableRow", "content": header_cells })

        # Data Rows
        for item in items:
            if not isinstance(item, dict):
                continue
                
            cells = [
                {
                    "type": "tableCell",
                    "content": [ self._adf_paragraph(str(item.get(k, ""))) ]
                } for k in keys
            ]
            rows.append({ "type": "tableRow", "content": cells })

        return {
            "type": "table",
            "attrs": { "isNumberColumnEnabled": False, "layout": "default" },
            "content": rows
        }


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
