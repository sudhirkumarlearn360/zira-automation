from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from .services.jira_service import JiraService
from .services.ai_service import AIService

class EpicStoriesView(View):
    def get(self, request, epic_key):
        jira_service = JiraService()
        stories = jira_service.get_stories_for_epic(epic_key)
        
        # Base URL for links
        import os
        jira_base_url = os.environ.get('JIRA_URL', '')
        
        context = {
            'epic_key': epic_key,
            'stories': stories,
            'jira_base_url': jira_base_url
        }
        return render(request, 'jira/epic_stories.html', context)

class IndexView(View):
    def get(self, request):
        return render(request, 'jira/index.html')

@method_decorator(csrf_exempt, name='dispatch')
class PreviewTasksView(View):
    """
    Step 1: Receive story keys & task type -> Return AI generated JSON for review.
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            story_keys = data.get('story_keys', [])
            epic_key = data.get('epic_key', 'UNKNOWN')
            task_type = data.get('task_type', 'General')
            
            # Re-fetch stories to get text (in real app, use cache/db)
            jira_service = JiraService()
            ai_service = AIService()
            all_stories = jira_service.get_stories_for_epic(epic_key)
            story_map = {s['key']: s for s in all_stories}
            
            previews = []
            
            for key in story_keys:
                story_data = story_map.get(key)
                if not story_data:
                    continue
                
                full_text = f"Summary: {story_data['summary']}\nDescription: {story_data['description']}"
                
                # Generate AI Content
                ai_json = ai_service.generate_task_from_story(full_text, task_type)
                
                if ai_json:
                    previews.append({
                        'original_key': key,
                        'generated_content': ai_json
                    })
            
            return JsonResponse({'previews': previews})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CreateConfirmedTasksView(View):
    """
    Step 2: Receive CONFIRMED JSON content -> Create in Jira.
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            approved_tasks = data.get('tasks', []) # List of {original_key, generated_content}
            epic_key = data.get('epic_key')
            
            jira_service = JiraService()
            results = []
            
            for task_item in approved_tasks:
                original_key = task_item.get('original_key')
                content = task_item.get('generated_content')
                
                # Create Task
                new_task = jira_service.create_task(epic_key, content)
                
                if new_task:
                    results.append({'key': original_key, 'status': 'CREATED', 'new_task_key': new_task.get('key')})
                else:
                    results.append({'key': original_key, 'status': 'FAILED', 'reason': 'Jira Create Error'})

            return JsonResponse({'results': results})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
