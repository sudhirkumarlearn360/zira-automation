import os
import requests
import json
from dotenv import load_dotenv

# Load env vars
load_dotenv()

JIRA_URL = os.environ.get('JIRA_URL')
JIRA_EMAIL = os.environ.get('JIRA_EMAIL')
JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')

print(f"URL: {JIRA_URL}")
print(f"Email: {JIRA_EMAIL}")
print(f"Token: {'*' * 5} (len={len(JIRA_API_TOKEN) if JIRA_API_TOKEN else 0})")

auth = (JIRA_EMAIL, JIRA_API_TOKEN)
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

epic_key = "CAR-13494"

# 1. Fetch the Epic itself
print(f"\n--- Fetching Issue {epic_key} ---")
url_issue = f"{JIRA_URL}/rest/api/3/issue/{epic_key}"
try:
    resp = requests.get(url_issue, headers=headers, auth=auth)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Summary: {data['fields']['summary']}")
        print(f"Type: {data['fields']['issuetype']['name']}")
    else:
        print(f"Error: {resp.text}")
except Exception as e:
    print(f"Exception: {e}")

# 2. Fetch Children (JQL)
print(f"\n--- Fetching Children (parent = {epic_key}) ---")
url_search = f"{JIRA_URL}/rest/api/3/search/jql"
jql = f"parent = {epic_key} AND issuetype = Story"
query = {
    'jql': jql,
    'fields': 'summary,description,issuetype'
}

try:
    payload = {
        "jql": jql,
        "fields": ["summary", "description", "issuetype"]
    }
    resp = requests.post(url_search, headers=headers, json=payload, auth=auth)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total Found: {data.get('total', 0)}")
        if 'issues' in data:
            for issue in data['issues']:
                print(f"- {issue['key']}: {issue['fields']['summary']}")
    else:
        print(f"Error: {resp.text}")
except Exception as e:
    print(f"Exception: {e}")
