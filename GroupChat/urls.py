from django.contrib import admin
from django.urls import path
from . import views
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static

app_name = 'GroupChat'

urlpatterns = [
    path('', views.home, name='GroupChat'),
    path('<int:key>/', views.plot_group_stats, name='draw_graph'),
    path('group_sent_days/', views.group_days_plot, name='draw_graph_group'),

    # path('population-chart/', views.find_day_of_chat, name='population-chart')
]#+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
