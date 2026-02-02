import os
import json
from openai import OpenAI
import google.generativeai as genai
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

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
            return self._generate_gemini(story_text, role_description, task_type)
        else:
            return self._generate_openai(story_text, role_description, task_type)

    def _get_role_description(self, task_type):
        base = "You are a senior Jira delivery manager"
        if task_type == 'Frontend':
            return f"{base} specializing in Frontend Engineering (React, CSS, UX)."
        elif task_type == 'Backend':
            return f"{base} specializing in Backend Architecture (Django, APIs, DB)."
        elif task_type == 'QA':
            return f"{base} specializing in Quality Assurance and Test Automation."
        return f"{base}."

    def _generate_openai(self, story_text, role_description, task_type):
        # Extract summary for fallback
        original_summary = story_text.split('\n')[0].replace('Summary: ', '')

        if not self.openai_client:
             return self._mock_response(original_summary)

        prompt = self._get_prompt(story_text, task_type)

        try:
            response = self.openai_client.chat.completions.create(
                model=os.environ.get('AI_MODEL', 'gpt-4o'),
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
            logger.error(f"The AI service was unavailable. OpenAI Error: {e}")
            return self._mock_response(original_summary)

    def _generate_gemini(self, story_text, role_description, task_type):
        original_summary = story_text.split('\n')[0].replace('Summary: ', '')

        if not self.gemini_key:
            return self._mock_response(original_summary)

        prompt = f"System: {role_description}\n\n{self._get_prompt(story_text, task_type)}"
        
        try:
            model_name = os.environ.get('AI_MODEL', 'gemini-1.5-flash')
            model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
            response = model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"The AI service was unavailable. Gemini Error: {e}")
            return self._mock_response(original_summary)

    def _get_prompt(self, story_text, task_type):
        title_instruction = "Generate a concise, technical title (e.g. 'Implement ...')"
        
        if task_type == 'Backend':
            title_instruction = "CRITICAL: The title MUST start with the exact string 'BE Task - ' and mention 'API'. Example: 'BE Task - Create User API'."
        elif task_type == 'Frontend':
            title_instruction = "CRITICAL: The title MUST start with the exact string 'FE Task - '. Example: 'FE Task - Login Page UI'."
        
        return f"""
Convert the following story into a detailed Technical Implementation Plan.

Strict Naming Rules:
- If Backend: Title MUST start with "BE Task - "
- If Frontend: Title MUST start with "FE Task - "
- NEVER use the word "Story" in the title.

Rules:
- Return ONLY valid JSON
- Keys must automatically include:
  "summary": "{title_instruction}",
  "description": "Generate a detailed technical description of the work required, including context ({task_type} focus) and goals.",
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

    def _mock_response(self, original_summary="Feature"):
        return {
            "summary": f"implementation: {original_summary} (Fallback)",
            "description": f"This is a fallback technical plan for '{original_summary}'. The AI service was unavailable, so this mock plan is provided to demonstrate the system capabilities.",
            "acceptance_criteria": [
                "User can view the dashboard",
                "Data loads within 200ms",
                "Error states are handled gracefully"
            ],
            "tech_stack": ["Python", "Django", "React", "PostgreSQL"],
            "api_endpoints": [
                {"method": "GET", "endpoint": "/api/v1/resource", "description": "Fetches the main resource list"},
                {"method": "POST", "endpoint": "/api/v1/resource", "description": "Creates a new resource"}
            ],
            "api_curl": "curl -X GET https://api.example.com/v1/resource",
            "database_schema": [
                {"table": "users", "columns": ["id SERIAL PK", "username VARCHAR", "email VARCHAR"]},
                {"table": "orders", "columns": ["id SERIAL PK", "user_id FK", "amount DECIMAL"]}
            ],
            "infrastructure": ["AWS EC2", "RDS Postgres", "Redis Cache"],
            "implementation_steps": ["Step 1: Setup DB", "Step 2: Create API", "Step 3: Build UI"]
        }
