from django.contrib import admin
from django.urls import path
from . import views

app_name = 'GroupChat'

urlpatterns = [
    path('', views.home, name='GroupChat'),
    path('<str:author>/', views.plot_days_plot, name='draw_graph')
    # path('population-chart/', views.find_day_of_chat, name='population-chart')
]
