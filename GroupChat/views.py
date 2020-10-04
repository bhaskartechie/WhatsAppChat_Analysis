from django.shortcuts import render
from django.http import HttpResponse
from .WhatsApp_chat_analysis import chat_analysis_main
import re


# Create your views here.
def home(request):
    filename = r"C:\Users\Administrator\Work\Whats_App_Chat_Analysis\WhatAppChat.txt"
    data_frame, messages_df = chat_analysis_main(filename)
    first_msg = data_frame['Message'][0]
    first_date = data_frame['Date'][0]
    first_date = first_date.date()
    first_time = data_frame['Time'][0]
    group_name = re.findall(r'\"(.*?)\"', first_msg)[0]
    creator = re.findall(r'\w+', first_msg)[0]
    # print(f'Group created by "{creator}" with group name "{group_name}" on {first_date.date()} {first_time}')
    return render(request, 'base.html', {'first_msg': first_msg,
                                         'first_date': first_date,
                                         'first_time': first_time,
                                         'group_name': group_name,
                                         'creator': creator})

