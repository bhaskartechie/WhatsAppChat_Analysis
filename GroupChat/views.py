from django.shortcuts import render
from django.http import HttpResponse
import numpy as np
from django.conf import settings
from .chat_stats_calculations import create_local_chat_file, \
    chat_analysis_main, group_name_changes, group_dp_changes, \
    find_active_members, find_day_of_chat, emoji_stats, \
    sent_messages_over_time, chatting_time, display_wordcloud, \
    calculate_each_member_stats, busiest_day_of_chat, personal_data_arrangement

def plot_members_stats(request, key):
    # member week days plot
    try:
        sent_days = request.session['authors_days']
        author = list(sent_days)[key]
        author_sent = sent_days[author]
        author_sent = [list(author_sent.keys()), list(author_sent.values())]
        # member sent emojies
        emojies_sent = request.session['emoji_sent_author']
        emojies = emojies_sent[author]
        emojies_sent_mem = [list(emojies.keys()), list(emojies.values())]
        # member sent data each month
        each_month_data_member = request.session['each_month_data_member']
        each_month_data_member = each_month_data_member[author]
        # bar plot of the active time for each member 
        time_wise_messages = request.session['member_chat_time']
        member_times = time_wise_messages[author]
        member_timings = [list(member_times.keys()), list(member_times.values())]
        image_path = f'word_cloud_images/{key}.jpg'
        return render(request, 'groupchat/members/base_members.html', 
                                {'author': author,
                                'author_sent': author_sent,
                                'emojies_sent_mem': emojies_sent_mem,
                                'each_month_data_member': each_month_data_member,
                                'member_timings': member_timings,
                                'image_path': image_path, })
    except Exception as e:
        return HttpResponse(e)    
        # return HttpResponse('<p>Something wrong at plat members statistics plot<\p>')



# this function to send the data to client
def plot_group_stats(request):
    try: 
        sent_days = request.session['group_days']
        group_days = [list(sent_days.keys()), list(sent_days.values())]
        group_name = request.session['present_group_name']   
        each_month_data_group = request.session['each_month_data_group'] 
        group_chat_time = request.session['group_chat_time']
        members_stats = request.session['members_stats']

        emoji_sent_group = request.session['emoji_sent_group']
        emoji_sent_group = [list(emoji_sent_group.keys()), list(emoji_sent_group.values())]
        word_cloud_image = 'word_cloud_images/group_word_cloud.jpg'
        return render(request, 'groupchat/group/base_groups.html', 
                                {'emojies_sent_group': emoji_sent_group,
                                'group_name': group_name,
                                'group_days': group_days,
                                'each_month_data_group': each_month_data_group,
                                'group_chat_time': group_chat_time,
                                'members_stats': members_stats,
                                'word_cloud_image': word_cloud_image, })
    except Exception as e:
        return HttpResponse(e)    
        # return HttpResponse('<p>Something wrong at plat members statistics plot<\p>')


def call_footer(request):
    return render(request, 'groupchat/footer_messages.html')


# @timeit
def home(request):
    # import cProfile, pstats
    # profiler = cProfile.Profile()
    # profiler.enable()
    # calculate number of visits of the site
    is_personal_chat = 0
    num_visits = request.session.get('num_visits', 0)
    request.session['num_visits'] = num_visits + 1
    if request.method == 'POST' and request.FILES['chat_file']:    
        chat_filename = create_local_chat_file(request.FILES['chat_file'])
        data_frame, member_stats = chat_analysis_main(
            chat_filename)
        # cheching for the group creation date time with group name by whom 
        if len(data_frame['Message'][0].split(' created group')) != 1:
            first_msg = data_frame['Message'][0]
            first_date = data_frame['Date'][0].date()
            # get the time from data frame
            first_time = data_frame['Date'][0].time()
            # creator of the group member
            creator = first_msg.split(' created group')[0]
        else:
            first_msg = first_date = first_time = creator = 'Not Available !'
        # get None author data, it is special author for group operations
        none_data = data_frame[data_frame["Author"].isnull()]
        authors = data_frame.Author.unique()
        authors = authors[authors != None]
        total_messages = data_frame.shape[0]
        emojis = sum(data_frame['Emoji'].str.len())
        links = np.sum(data_frame.isURL)
        deleted_messages = np.sum(data_frame.isDeleted)
        media_messages = data_frame[data_frame['Message']
                                    == '<Media omitted>'].shape[0]
        data_frame.sort_values(by='Date')
        # this case is for personal chat
        # set flag to 1 if number of authors only 2
        if len(member_stats) == 2:
            is_personal_chat = 1

        # * From here functions manipulation functions are starting
        # function to find the number changes in the group dps
        if is_personal_chat == 0:
            num_dp_changes, dp_last_change, dp_last_change_by = group_dp_changes(
                none_data, first_date, creator)
            group_members = find_active_members(none_data, authors)
            # function to find the number changes in the group names
            group_names, ids = group_name_changes(none_data)
            if ids == 1:
                # this case is group name available but no change in group names
                first_group_name = present_group_name = group_names[1]
            elif ids == 2:
                # this case has multiple group name changes
                first_group_name = group_names[0][1]
                present_group_name = group_names[-1][2]
            elif ids == 3:
                # no groupnames available case
                first_group_name = 'Not Available !'
                present_group_name = 'GroupNameNotAvailable'
            else:
                first_group_name = 'SomethingWentBad !'
                present_group_name = 'SomethingWentBad !'

        # sent messages on which day of the week for each each member and whole group
        authors_days, group_days = find_day_of_chat(data_frame, authors)
        # numbers of emojies in each member sent messages
        emoji_sent_author, emoji_sent_group = emoji_stats(data_frame, authors)
        # count of the sent messages of each month from joining 
        each_month_data_member, each_month_data_group = sent_messages_over_time(data_frame, authors)
        # find active timing of the member
        member_chat_time, group_chat_time = chatting_time(data_frame, authors)
        # word cloud plot
        display_wordcloud(data_frame, authors)
        # for group graph display calculate all statistics of the group members
        members_stats = calculate_each_member_stats(data_frame, authors)
        # calculate busiest day of the group chat
        busy_day_stats = busiest_day_of_chat(data_frame)
        arranged_personal_data = personal_data_arrangement(authors, members_stats, authors_days, emoji_sent_author, \
                                                            each_month_data_member, member_chat_time, busy_day_stats)
        if is_personal_chat == 1:
            return render(request, 'groupchat/personal_chat/personal_chat.html', {'authors': authors,
                                                                                  'busy_day_stats':busy_day_stats,
                                                                                  'arranged_personal_data': arranged_personal_data, })
        # ! save data to session to send this data graphs of which day most day
        # members statistics
        request.session['authors_days'] = authors_days
        request.session['emoji_sent_author'] = emoji_sent_author
        request.session['each_month_data_member'] = each_month_data_member
        request.session['member_chat_time'] = member_chat_time
        
        # group statistics
        request.session['group_days'] = group_days
        request.session['present_group_name'] = present_group_name
        request.session['each_month_data_group'] = each_month_data_group
        request.session['group_chat_time'] = group_chat_time
        request.session['members_stats'] = members_stats
        request.session['emoji_sent_group'] = emoji_sent_group


        msg_statistics = {'Total messages': total_messages,
                          'Media messages': media_messages,
                          'Total Emojis': emojis,
                          'Total links': links,
                          'Total deleted messages': deleted_messages, }
        # put all outs of the the dp activities
        dp_changes = (num_dp_changes, dp_last_change, dp_last_change_by)
        # profiler.disable()
        # stats = pstats.Stats(profiler).sort_stats('cumtime')
        # stats.dump_stats(r"C:\Users\Administrator\Work\Whats_App_Chat_Analysis\profile.prof")
        return render(request, 'groupchat/chat_analysis.html', {'first_msg': first_msg,
                                                                'first_date': first_date,
                                                                'first_time': first_time,
                                                                'first_group_name': first_group_name,
                                                                'present_group_name': present_group_name,
                                                                'ids': ids,
                                                                'creator': creator,
                                                                'group_members': group_members,
                                                                'dp_changes': dp_changes,
                                                                'msg_statistics': msg_statistics,
                                                                'group_names': group_names,
                                                                'member_stats': member_stats,
                                                                'busy_day_stats': busy_day_stats,
                                                                'num_visits': num_visits, })
        # 'data': data, })

    # else:
    #     form = UploadChatFileForm()
    return render(request, 'base.html', {'num_visits': num_visits, })

