from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings
urlpatterns = [
    path("", views.chat_page, name="chat"),
    path("generator", views.generator_page, name="generator"),   
    path("wizard", views.wizard_page, name="wizard"),  #  neu           
    path("api/message", views.api_message, name="api_message"),
    path("api/attachment", views.api_attachment, name="api_attachment"),
    path("api/task/generate", views.api_task_generate, name="api_task_generate"),  
    path("api/task/accept", views.api_task_accept, name="api_task_accept"),
    path("api/task/accepted_list", views.api_task_accepted_list, name="api_task_accepted_list"),
    path("api/task/reset_exam", views.api_task_reset_exam, name="api_task_reset_exam"),      
    path("api/task/export", views.api_task_export, name="api_task_export"),
    path("api/task/export_pdf", views.api_task_export, name="api_task_export_pdf"),  
    path("api/task/export_docx", views.api_task_export_docx, name="api_task_export_docx"),

    path('compare', views.compare, name='compare'),
    path('api/generate-solution', views.api_generate_solution, name='api_generate_solution'),
    path('api/compare-solutions', views.api_compare_solutions, name='api_compare_solutions'),
    path('api/detailed-analysis', views.api_detailed_analysis, name='api_detailed_analysis'),
            
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)