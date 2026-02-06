from django.urls import path
from .views import (
    EpicStoriesView, PreviewTasksView, CreateConfirmedTasksView, 
    IndexView, StoryDetailView, HomeView,
    TestCaseGeneratorView, GenerateTestCasesView, RefineTestCasesView, 
    ExportTestCasesView, RegenerateCategoryTestCasesView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('epics/', IndexView.as_view(), name='index'),
    path('epic/<str:epic_key>/stories/', EpicStoriesView.as_view(), name='epic_stories'),
    path('story/<str:story_key>/', StoryDetailView.as_view(), name='story_detail'),
    path('preview-tasks/', PreviewTasksView.as_view(), name='preview_tasks'),
    path('create-tasks/', CreateConfirmedTasksView.as_view(), name='create_tasks'),
    # Test Case Generator
    path('test-cases/', TestCaseGeneratorView.as_view(), name='test_case_generator'),
    path('generate-test-cases/', GenerateTestCasesView.as_view(), name='generate_test_cases'),
    path('refine-test-cases/', RefineTestCasesView.as_view(), name='refine_test_cases'),
    path('regenerate-category/', RegenerateCategoryTestCasesView.as_view(), name='regenerate_category'),
    path('export-test-cases/', ExportTestCasesView.as_view(), name='export_test_cases'),
]

