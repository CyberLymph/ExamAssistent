from django.urls import path
from . import views

urlpatterns = [
    path("", views.chat_page, name="chat"),             # <— root: "", nicht "/"
    path("api/message", views.api_message, name="api_message"),
    path("api/attachment", views.api_attachment, name="api_attachment"),
]
