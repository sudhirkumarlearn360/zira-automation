import os
import json
from openai import OpenAI
import google.generativeai as genai
from django.conf import settings

class AIService:
    def __init__(self):
        self.provider = os.environ.get('AI_PROVIDER', 'OPENAI').upper()
        self.openai_key = os.environ.get('OPENAI_API_KEY')
        self.gemini_key = os.environ.get('GEMINI_API_KEY')
        
        self.openai_client = None
        if self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)

        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

    def generate_task_from_story(self, story_text, task_type="General"):
        """
        Routing method to choose provider.
        """
        role_description = self._get_role_description(task_type)
        
        if self.provider == 'GEMINI':
            return self._generate_gemini(story_text, role_description)
        else:
            return self._generate_openai(story_text, role_description)

    def _get_role_description(self, task_type):
        base = "You are a senior Jira delivery manager"
        if task_type == 'Frontend':
            return f"{base} specializing in Frontend Engineering (React, CSS, UX)."
        elif task_type == 'Backend':
            return f"{base} specializing in Backend Architecture (Django, APIs, DB)."
        elif task_type == 'QA':
            return f"{base} specializing in Quality Assurance and Test Automation."
        return f"{base}."

    def _generate_openai(self, story_text, role_description):
        if not self.openai_client:
             return self._mock_response()

        prompt = self._get_prompt(story_text)

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"{role_description} You return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return None

    def _generate_gemini(self, story_text, role_description):
        if not self.gemini_key:
            return self._mock_response()

        prompt = f"System: {role_description}\n\n{self._get_prompt(story_text)}"
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
            response = model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini Error: {e}")
            return None

    def _get_prompt(self, story_text):
        return f"""
Convert the following story into a detailed Technical Implementation Plan.

Rules:
- Return ONLY valid JSON
- Keys must automatically include:
  "summary": "String",
  "description": "String",
  "acceptance_criteria": ["String"],
  "tech_stack": ["String"],
  "api_endpoints": [{{"method": "GET/POST", "endpoint": "/url", "description": "text"}}],
  "api_curl": "String (code block)",
  "database_schema": [{{"table": "name", "columns": ["col type", ...]}}],
  "infrastructure": ["String"],
  "implementation_steps": ["String"]

Story:
{story_text}
"""

    def _mock_response(self):
        return {
            "summary": "Implement functionality (MOCK)",
            "description": "Mock description.",
            "acceptance_criteria": ["Mock AC 1"]
        }
