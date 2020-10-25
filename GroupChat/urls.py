from django.contrib import admin
from django.urls import path
from . import views

app_name = 'GroupChat'

urlpatterns = [
    path('', views.home, name='GroupChat'),
    path('<int:key>/', views.authors_days_plot, name='draw_graph'),
    path('group_sent_days/', views.group_days_plot, name='draw_graph_group'),
    # path('population-chart/', views.find_day_of_chat, name='population-chart')
]
