from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json
import os

from jira_app.services.ai_service import AIService

class JiraAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.epic_key = "TEST-100"

    @patch('jira_app.services.jira_service.requests.get')
    def test_epic_stories_view(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'issues': [
                {'key': 'TEST-101', 'fields': {'summary': 'Story 1', 'description': 'Desc 1'}}
            ]
        }
        mock_get.return_value = mock_response

        url = reverse('epic_stories', args=[self.epic_key])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @patch('jira_app.services.ai_service.OpenAI')
    @patch('jira_app.services.jira_service.requests.get')
    @patch('jira_app.services.jira_service.requests.post')
    def test_generate_tasks_openai(self, mock_post, mock_get, mock_openai):
        # Force OPENAI
        with patch.dict(os.environ, {'AI_PROVIDER': 'OPENAI', 'OPENAI_API_KEY': 'chk-123'}):
            mock_get.return_value.json.return_value = {'issues': [{'key': 'T-1', 'fields': {'summary': 'S', 'description': 'D'}}]}
            
            mock_ai = MagicMock()
            mock_ai.chat.completions.create.return_value.choices[0].message.content = json.dumps({"summary": "AI", "description": "D", "acceptance_criteria": []})
            mock_openai.return_value = mock_ai
            
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {'key': 'NEW-1'}

            url = reverse('generate_tasks')
            response = self.client.post(url, json.dumps({'story_keys': ['T-1'], 'epic_key': 'E'}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
            res = response.json()
            self.assertEqual(res['results'][0]['status'], 'CREATED')

    @patch('jira_app.services.ai_service.genai.GenerativeModel')
    @patch('jira_app.services.jira_service.requests.get')
    @patch('jira_app.services.jira_service.requests.post')
    def test_generate_tasks_gemini(self, mock_post, mock_get, mock_model_class):
        # Force GEMINI
        with patch.dict(os.environ, {'AI_PROVIDER': 'GEMINI', 'GEMINI_API_KEY': 'gem-123'}):
            mock_get.return_value.json.return_value = {'issues': [{'key': 'T-1', 'fields': {'summary': 'S', 'description': 'D'}}]}
            
            mock_model_instance = MagicMock()
            mock_model_instance.generate_content.return_value.text = json.dumps({"summary": "GEMINI AI", "description": "D", "acceptance_criteria": []})
            mock_model_class.return_value = mock_model_instance
            
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {'key': 'NEW-2'}

            url = reverse('generate_tasks')
            response = self.client.post(url, json.dumps({'story_keys': ['T-1'], 'epic_key': 'E'}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
            res = response.json()
            self.assertEqual(res['results'][0]['status'], 'CREATED')
