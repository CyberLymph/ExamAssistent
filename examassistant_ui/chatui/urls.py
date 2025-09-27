from django.urls import path
from . import views

urlpatterns = [
    path("", views.chat_page, name="chat"),
    path("generator", views.generator_page, name="generator"),              #  neu
    path("api/message", views.api_message, name="api_message"),
    path("api/attachment", views.api_attachment, name="api_attachment"),
    path("api/task/generate", views.api_task_generate, name="api_task_generate"),  #  neu
    path("api/task/accept", views.api_task_accept, name="api_task_accept"),        #  neu
    path("api/task/export", views.api_task_export, name="api_task_export"),        #  neu
]
