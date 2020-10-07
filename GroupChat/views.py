from django.shortcuts import render
from django.http import HttpResponse
from .WhatsApp_chat_analysis import chat_analysis_main
import re
import numpy as np
from .forms import UploadChatFileForm
from django.conf import settings
import os


def create_local_chat_file(fd):
    chat_filename = os.path.join(settings.MEDIA_ROOT, 'temp_chat_file.txt')
    with open(chat_filename, 'wb+') as destination:
        for chunk in fd.chunks():
            destination.write(chunk)
    return chat_filename


# Create your views here.
def home(request):
    if request.method == 'POST' and request.FILES['chat_file']:
        # form = UploadChatFileForm(request.POST, request.FILES)
        # if form.is_valid():
        # filename = r"C:\Users\Administrator\Work\Whats_App_Chat_Analysis\WhatAppChat.txt"
        chat_filename = create_local_chat_file(request.FILES['chat_file'])
        data_frame, messages_df, member_stats = chat_analysis_main(chat_filename)
        first_msg = data_frame['Message'][0]
        first_date = data_frame['Date'][0].date()
        first_time = data_frame['Time'][0]
        group_name = re.findall(r'\"(.*?)\"', first_msg)[0]
        creator = re.findall(r'\w+', first_msg)[0]
        authors = messages_df.Author.unique()
        authors = authors[authors != None]

        total_messages = data_frame.shape[0]
        emojis = sum(data_frame['emoji'].str.len())
        links = np.sum(data_frame.urlcount)
        media_messages = data_frame[data_frame['Message'] == '<Media omitted>'].shape[0]

        msg_statistics = {'Total messages': total_messages,
                          'Media messages': media_messages,
                          'Total Emojis': emojis,
                          'Total links': links,
                          }
        return render(request, 'groupchat/chat_analysis.html', {'first_msg': first_msg,
                                                                'first_date': first_date,
                                                                'first_time': first_time,
                                                                'group_name': group_name,
                                                                'creator': creator,
                                                                'authors': authors,
                                                                'msg_statistics': msg_statistics,
                                                                'member_stats': member_stats, })

    # else:
    #     form = UploadChatFileForm()
    return render(request, 'base.html')