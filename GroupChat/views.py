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


def find_group_name(df):
    # this key term used to find the changes in the group name
    key_terms = 'changed the subject from '
    data_frame = df[df["Message"].str.contains(key_terms)]
    if data_frame.empty:
        filt = lambda s: [s[0:s.find(' created')], s[s.find('created group "') + len('created group "'):s.rfind('"')]]
        return [df["Message"].apply(filt)[0]]
    # find the string between from and to strings
    first_str_pre = 'from "'
    first_str_post = '" to'
    second_str_pre = 'to "'
    second_str_post = '"'
    filt = lambda s: [s[0:s.find(' changed the subject')], s[s.find(first_str_pre) +
                       len(first_str_pre):s.rfind(first_str_post)], s[s.find(second_str_pre) +
                       len(second_str_pre):s.rfind(second_str_post)]]

    # filt_2 = lambda s: s[s.find(second_str_pre) + len(second_str_pre):s.rfind(second_str_post)]
    temp_df = data_frame["Message"].apply(filt)
    # remove empty list from the none data frame
    return temp_df[temp_df.astype(bool)].to_list()


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
        # get None author data, it is special author for group operations
        none_data = messages_df[messages_df["Author"].isnull()]
        authors = messages_df.Author.unique()
        authors = authors[authors != None]

        total_messages = data_frame.shape[0]
        emojis = sum(data_frame['emoji'].str.len())
        links = np.sum(data_frame.urlcount)
        media_messages = data_frame[data_frame['Message'] == '<Media omitted>'].shape[0]
        group_names = find_group_name(none_data)
        first_group_name = group_names[0][1]
        if len(group_names) == 1:
            present_group_name = first_group_name
        else:
            present_group_name = group_names[-1][2]

        msg_statistics = {'Total messages': total_messages,
                          'Media messages': media_messages,
                          'Total Emojis': emojis,
                          'Total links': links, }
        return render(request, 'groupchat/chat_analysis.html', {'first_msg': first_msg,
                                                                'first_date': first_date,
                                                                'first_time': first_time,
                                                                'first_group_name': first_group_name,
                                                                'present_group_name': present_group_name,
                                                                'creator': creator,
                                                                'authors': authors,
                                                                'msg_statistics': msg_statistics,
                                                                'group_names': group_names,
                                                                'member_stats': member_stats, })

    # else:
    #     form = UploadChatFileForm()
    return render(request, 'base.html')
