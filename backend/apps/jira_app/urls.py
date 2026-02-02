from django.urls import path
from .views import EpicStoriesView, PreviewTasksView, CreateConfirmedTasksView, IndexView, StoryDetailView, HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('epics/', IndexView.as_view(), name='index'),
    path('epic/<str:epic_key>/stories/', EpicStoriesView.as_view(), name='epic_stories'),
    path('story/<str:story_key>/', StoryDetailView.as_view(), name='story_detail'),
    path('preview-tasks/', PreviewTasksView.as_view(), name='preview_tasks'),
    path('create-tasks/', CreateConfirmedTasksView.as_view(), name='create_tasks'),
]
