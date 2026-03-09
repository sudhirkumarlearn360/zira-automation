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

    def generate_task_from_story(self, story_text, task_type="General", additional_context=""):
        """
        Routing method to choose provider.
        """
        role_description = self._get_role_description(task_type)
        
        if self.provider == 'GEMINI':
            return self._generate_gemini(story_text, role_description, task_type, additional_context)
        else:
            return self._generate_openai(story_text, role_description, task_type, additional_context)

    def _get_role_description(self, task_type):
        base = "You are a senior Jira delivery manager"
        if task_type == 'Frontend':
            return f"{base} specializing in Frontend Engineering (React, CSS, UX)."
        elif task_type == 'Backend':
            return f"{base} specializing in Backend Architecture (Django, APIs, DB)."
        elif task_type == 'QA':
            return f"{base} specializing in Quality Assurance and Test Automation."
        return f"{base}."

    def _generate_openai(self, story_text, role_description, task_type, additional_context):
        # Extract summary for fallback
        original_summary = story_text.split('\n')[0].replace('Summary: ', '')

        if not self.openai_client:
             raise ValueError("OpenAI API Key is missing. Rate limit or missing env var.")

        prompt = self._get_prompt(story_text, task_type, additional_context)

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
            raise e

    def _generate_gemini(self, story_text, role_description, task_type, additional_context):
        original_summary = story_text.split('\n')[0].replace('Summary: ', '')

        if not self.gemini_key:
            raise ValueError("Gemini API Key is missing. Rate limit or missing env var.")

        prompt = f"System: {role_description}\n\n{self._get_prompt(story_text, task_type, additional_context)}"
        
        try:
            model_name = os.environ.get('AI_MODEL', 'gemini-1.5-flash')
            model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
            response = model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"The AI service was unavailable. Gemini Error: {e}")
            raise e

    def _get_prompt(self, story_text, task_type, additional_context):
        title_instruction = "Generate a concise, technical title (e.g. 'Implement ...')"
        
        if task_type == 'Backend':
            title_instruction = "CRITICAL: The title MUST start with the exact string 'BE Task - ' and mention 'API'. Example: 'BE Task - Create User API'."
        elif task_type == 'Frontend':
            title_instruction = "CRITICAL: The title MUST start with the exact string 'FE Task - '. Example: 'FE Task - Login Page UI'."
        
        context_block = f"""
CRITICAL ADDITIONAL INSTRUCTIONS FROM USER: 
{additional_context}
""" if additional_context else ""

        return f"""
Convert the following story into a detailed Technical Implementation Plan.
{context_block}
Strict Naming Rules:
- If Backend: Title MUST start with "BE Task - "
- If Frontend: Title MUST start with "FE Task - "
- NEVER use the word "Story" in the title.

Rules:
- Return ONLY valid JSON
- You MUST create ANY custom JSON keys needed to perfectly represent the information from the user's Context (e.g., "url_aliases", "seo_metadata", etc.).
- CRITICAL: If the user provides API endpoints, cURL commands, or database tables in their Context, you MUST map them to the keys `api_endpoints`, `api_curl`, and `database_schema` respectively.
- If the user provides other raw data snippets, DO NOT squash them into the description. Create a new descriptive top-level JSON key for them and put the data inside.
- Keys must automatically include "summary" (using the title instruction: {title_instruction}) and "description".

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

    # ==================== TEST CASE GENERATION ====================
    
    def generate_test_cases(self, content, scope_type="story", additional_context=""):
        """
        Generate test cases from story/epic/task content.
        scope_type: 'epic', 'story', or 'task'
        additional_context: User-provided prompt for customization
        """
        prompt = self._get_test_case_prompt(content, scope_type, additional_context)
        role_desc = "You are a senior QA Engineer specializing in creating comprehensive test cases. You return ONLY valid JSON."
        
        if self.provider == 'GEMINI':
            return self._generate_test_cases_gemini(prompt, role_desc)
        else:
            return self._generate_test_cases_openai(prompt, role_desc)

    def refine_test_cases(self, current_test_cases, refinement_prompt, original_content=""):
        """
        Refine existing test cases based on user feedback.
        """
        prompt = f"""
You are refining existing test cases based on user feedback.

CURRENT TEST CASES:
{json.dumps(current_test_cases, indent=2)}

ORIGINAL STORY/CONTEXT:
{original_content}

USER REFINEMENT REQUEST:
{refinement_prompt}

INSTRUCTIONS:
- Modify the test cases based on the user's feedback
- Keep test case IDs consistent where possible
- Add new test cases if requested
- Remove test cases if requested  
- Improve descriptions, steps, or expected results as needed

Return the refined test cases in this exact JSON format:
{{
  "test_cases": [
    {{
      "id": "TC001",
      "title": "Test case title",
      "description": "What this test verifies",
      "preconditions": ["Precondition 1", "Precondition 2"],
      "steps": ["Step 1", "Step 2", "Step 3"],
      "expected_result": "Expected outcome",
      "priority": "High/Medium/Low",
      "type": "Functional/UI/Integration/API/Performance"
    }}
  ],
  "changes_made": ["List of changes applied"]
}}
"""
        role_desc = "You are a senior QA Engineer. You return ONLY valid JSON."
        
        if self.provider == 'GEMINI':
            return self._generate_test_cases_gemini(prompt, role_desc)
        else:
            return self._generate_test_cases_openai(prompt, role_desc)

    def generate_categorized_epic_test_cases(self, stories, additional_context=""):
        """
        Generate categorized test cases for an entire Epic.
        Analyzes stories and categorizes them by BE/FE/QA/Other, then generates test cases per category.
        """
        prompt = f"""
You are a senior QA Engineer analyzing an EPIC with multiple stories.

STORIES TO ANALYZE:
{json.dumps(stories, indent=2)}

{f"ADDITIONAL CONTEXT FROM USER: {additional_context}" if additional_context else ""}

TASK:
1. First, analyze each story and categorize it:
   - BE (Backend): API development, database changes, server-side logic, integrations
   - FE (Frontend): UI components, user interactions, styling, client-side logic
   - QA (Testing): Test automation, quality gates, validation scripts
   - OTHER: Documentation, DevOps, infrastructure, design, etc.

2. For each category, generate comprehensive test cases specific to that area.

Return the categorized test cases in this exact JSON format:
{{
  "categories": {{
    "BE": {{
      "stories": ["STORY-KEY-1", "STORY-KEY-2"],
      "description": "Backend components requiring testing",
      "test_cases": [
        {{
          "id": "BE-TC001",
          "story_key": "STORY-KEY-1",
          "title": "Test case title",
          "description": "What this test verifies",
          "preconditions": ["API server running", "Database seeded"],
          "steps": ["Send POST request", "Verify response"],
          "expected_result": "Expected outcome",
          "priority": "High/Medium/Low",
          "type": "API/Integration/Unit"
        }}
      ]
    }},
    "FE": {{
      "stories": ["STORY-KEY-3"],
      "description": "Frontend components requiring testing",
      "test_cases": [...]
    }},
    "QA": {{
      "stories": [],
      "description": "QA and automation tasks",
      "test_cases": [...]
    }},
    "OTHER": {{
      "stories": [],
      "description": "Other non-code tasks",
      "test_cases": [...]
    }}
  }},
  "summary": {{
    "total_stories": 5,
    "total_test_cases": 25,
    "by_category": {{
      "BE": 10,
      "FE": 12,
      "QA": 2,
      "OTHER": 1
    }}
  }}
}}

RULES:
- Assign EVERY story to exactly ONE category based on its primary focus
- Generate 3-8 test cases per story
- Use prefixes for test case IDs: BE-TC001, FE-TC001, QA-TC001, OTHER-TC001
- Include the story_key in each test case to track origin
- BE tests focus on: API contracts, data validation, error handling, performance
- FE tests focus on: UI rendering, user interactions, responsiveness, accessibility
- QA tests focus on: Automation coverage, regression, smoke tests
- OTHER tests focus on: Documentation accuracy, deployment verification
"""
        role_desc = "You are a senior QA Engineer specializing in comprehensive test planning. You return ONLY valid JSON."
        
        if self.provider == 'GEMINI':
            return self._generate_test_cases_gemini(prompt, role_desc)
        else:
            return self._generate_test_cases_openai(prompt, role_desc)

    def regenerate_category_test_cases(self, category, stories, current_test_cases, user_prompt, original_context=""):
        """
        Regenerate test cases for a specific category with user guidance.
        """
        prompt = f"""
You are regenerating test cases for the {category} category based on user feedback.

CATEGORY: {category}
{"- Backend: Focus on API, database, server-side logic" if category == "BE" else ""}
{"- Frontend: Focus on UI, user interactions, client-side" if category == "FE" else ""}
{"- QA: Focus on automation, regression, quality gates" if category == "QA" else ""}
{"- Other: Focus on documentation, infrastructure, deployment" if category == "OTHER" else ""}

STORIES IN THIS CATEGORY:
{json.dumps(stories, indent=2)}

CURRENT TEST CASES:
{json.dumps(current_test_cases, indent=2)}

USER REQUEST:
{user_prompt}

ORIGINAL CONTEXT:
{original_context}

Generate improved test cases in this exact JSON format:
{{
  "test_cases": [
    {{
      "id": "{category}-TC001",
      "story_key": "STORY-KEY",
      "title": "Test case title",
      "description": "What this test verifies",
      "preconditions": ["Precondition 1"],
      "steps": ["Step 1", "Step 2"],
      "expected_result": "Expected outcome",
      "priority": "High/Medium/Low",
      "type": "Appropriate test type"
    }}
  ],
  "changes_made": ["List of changes based on user request"]
}}

RULES:
- Follow user's instructions precisely
- Keep IDs prefixed with {category}-
- Maintain story_key references
- Generate comprehensive tests based on the category focus
"""
        role_desc = f"You are a senior QA Engineer specializing in {category} testing. You return ONLY valid JSON."
        
        if self.provider == 'GEMINI':
            return self._generate_test_cases_gemini(prompt, role_desc)
        else:
            return self._generate_test_cases_openai(prompt, role_desc)

    def _get_test_case_prompt(self, content, scope_type, additional_context):
        scope_instruction = {
            'epic': "This is an EPIC containing multiple stories. Generate comprehensive test cases covering all user journeys.",
            'story': "This is a single USER STORY. Generate detailed test cases for this specific feature.",
            'task': "This is a TASK. Generate focused test cases for this specific implementation."
        }.get(scope_type, "Generate test cases for this content.")
        
        return f"""
{scope_instruction}

CONTENT TO ANALYZE:
{content}

{f"ADDITIONAL CONTEXT FROM USER: {additional_context}" if additional_context else ""}

Generate comprehensive test cases in this exact JSON format:
{{
  "test_cases": [
    {{
      "id": "TC001",
      "title": "Descriptive test case title",
      "description": "What this test verifies and why it's important",
      "preconditions": ["User is logged in", "Feature X is enabled"],
      "steps": ["Navigate to page", "Click button", "Enter data", "Submit form"],
      "expected_result": "Clear description of expected outcome",
      "priority": "High/Medium/Low",
      "type": "Functional/UI/Integration/API/Performance"
    }}
  ],
  "summary": "Brief summary of test coverage"
}}

RULES:
- Generate at least 5-10 relevant test cases
- Include positive tests (happy path)
- Include negative tests (error handling, edge cases)
- Include boundary tests where applicable
- Prioritize based on business impact
- Make steps clear and actionable
"""

    def _generate_test_cases_openai(self, prompt, role_desc):
        if not self.openai_client:
            return self._mock_test_cases()
        
        try:
            response = self.openai_client.chat.completions.create(
                model=os.environ.get('AI_MODEL', 'gpt-4o'),
                messages=[
                    {"role": "system", "content": role_desc},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"OpenAI test case generation error: {e}")
            return self._mock_test_cases()

    def _generate_test_cases_gemini(self, prompt, role_desc):
        if not self.gemini_key:
            return self._mock_test_cases()
        
        full_prompt = f"System: {role_desc}\n\n{prompt}"
        
        try:
            model_name = os.environ.get('AI_MODEL', 'gemini-1.5-flash')
            model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
            response = model.generate_content(full_prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini test case generation error: {e}")
            return self._mock_test_cases()

    def _mock_test_cases(self):
        return {
            "test_cases": [
                {
                    "id": "TC001",
                    "title": "Verify successful login with valid credentials",
                    "description": "Test that users can log in with correct username and password",
                    "preconditions": ["User account exists", "User is on login page"],
                    "steps": ["Enter valid username", "Enter valid password", "Click Login button"],
                    "expected_result": "User is redirected to dashboard",
                    "priority": "High",
                    "type": "Functional"
                },
                {
                    "id": "TC002", 
                    "title": "Verify error message for invalid credentials",
                    "description": "Test error handling for incorrect login attempts",
                    "preconditions": ["User is on login page"],
                    "steps": ["Enter invalid username", "Enter any password", "Click Login button"],
                    "expected_result": "Error message 'Invalid credentials' is displayed",
                    "priority": "High",
                    "type": "Functional"
                },
                {
                    "id": "TC003",
                    "title": "Verify password field masking",
                    "description": "Test that password input is masked for security",
                    "preconditions": ["User is on login page"],
                    "steps": ["Click on password field", "Type password"],
                    "expected_result": "Characters are displayed as dots/asterisks",
                    "priority": "Medium",
                    "type": "UI"
                }
            ],
            "summary": "Basic test coverage for login functionality (mock data - AI service unavailable)"
        }

