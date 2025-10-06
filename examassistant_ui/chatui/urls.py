from django.urls import path
from . import views

urlpatterns = [

    path('compare', views.compare, name='compare'),
    path('detailed', views.detailed, name='detailed'),
    path('api/message', views.api_message, name='api_message'),
    path('api/generate-solution', views.api_generate_solution, name='api_generate_solution'),
    path('api/compare-solutions', views.api_compare_solutions, name='api_compare_solutions'),
]
