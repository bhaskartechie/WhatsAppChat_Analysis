from django.shortcuts import render
from django.http import HttpResponse
from .WhatsApp_chat_analysis import chat_analysis_main, dayofweek
import re
import numpy as np
from django.conf import settings
import os
from collections import OrderedDict
from django.http import JsonResponse
from collections import Counter
import datetime
from wordcloud import WordCloud
# import matplotlib.pyplot as plt
from shutil import copyfile, rmtree

# from django.views.generic import TemplateView
# from chartjs.views.lines import BaselLineChartView
#  this is the global variable for calculate the average word speed of the group memeber
avg_words = 10

def create_local_chat_file(fd):
    chat_filename = os.path.join(settings.MEDIA_ROOT, 'temp_chat_file.txt')
    with open(chat_filename, 'wb+') as destination:
        for chunk in fd.chunks():
            destination.write(chunk)
    return chat_filename


# function to count the number of times group dp changed
def group_dp_changes(df, date, created_by):
    # this i the key term to check in the dataframe
    key_term_icon = 'this group\'s icon'
    icon_changes = df[df["Message"].str.contains(key_term_icon)]
    # total number of changes
    num_changes = icon_changes.shape[0]
    if num_changes > 0:
        # last dp changed date by getting last column of the searched data frame
        last_change = icon_changes['Date'].dt.date.iloc[-1]
        # last dp changed author by getting last column of the searched data frame
        last_change_by = icon_changes['Message'].iloc[[-1]
                                                      ].str.rsplit(' changed').to_list()[0][0]
        return num_changes, last_change, last_change_by
    else:
        return num_changes, date, created_by

def get_month(month_number):
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    return months[month_number -1] 

# function to count the number of times group name changed
def group_name_changes(df):
    # this key term used to find the changes in the group name
    key_terms = 'changed the subject from '
    data_frame = df[df["Message"].str.contains(key_terms)]
    if data_frame.empty:
        def filter_groupname_nochange(s):
            return [s[0:s.find(' created')], s[s.find(
                'created group "') + len('created group "'):s.rfind('"')]]
        return [df["Message"].apply(filter_groupname_nochange)[0]]
    # filt_2 = lambda s: s[s.find(second_str_pre) + len(second_str_pre):s.rfind(second_str_post)]

    def filter_groupname_change(s):
        # find the string between from and to strings
        first_str_pre = 'from "'
        first_str_post = '" to'
        second_str_pre = 'to "'
        second_str_post = '"'
        return [s[0:s.find(' changed the subject')], s[s.find(first_str_pre) +
                                                       len(first_str_pre):s.rfind(first_str_post)], s[s.find(second_str_pre) +
                                                                                                      len(second_str_pre):s.rfind(second_str_post)]]
    temp_df = data_frame["Message"].apply(filter_groupname_change)
    # remove empty list from the none data frame
    return temp_df[temp_df.astype(bool)].to_list()


# this function finds the active and left members from the group
def find_active_members(df, authors):
    # ---------this snippet for the string "added" search
    keyword_added = 'added'
    added_memebers = df[df['Message'].str.findall(
        keyword_added).astype(bool)]['Message']
    # get added string messages then get second list from list
    added_persons = added_memebers.str.rsplit(
        keyword_added).apply(lambda x: x.pop(1))
    # replace 'and' with ',' so that it will easier to get list
    added_persons = added_persons.str.replace('and', ',')
    # split list elements by ',' and convert to the list, its list of list elemets
    authors_list_of_lists = added_persons.str.split(',').to_list()
    # flatten list by striping strings
    authors_list = [item.strip()
                    for sublist in authors_list_of_lists for item in sublist]
    # remove any nulls
    authors_list = list(filter(None, authors_list))
    # get only unique others out of added mutliple times
    authors_list = list(set(authors_list))

    # ---------this snippet for the string "joined using this" search
    keyword_link = 'joined using this'
    link_joining = df[df['Message'].str.findall(
        keyword_link).astype(bool)]['Message']
    link_joining = link_joining.str.rsplit(
        keyword_link).apply(lambda x: x.pop(0)).to_list()
    joined_by_link = [s.strip() for s in link_joining]
    # get only unique others out of added mutliple times by link
    joined_by_link = list(set(joined_by_link))

    # TODO: need to get admin if you were added
    # checking for the condition "was added"
    keyword_was = 'was added'
    if any(added_persons == ''):
        empty_ind = added_persons[added_persons == ''].index
        was_added = added_memebers[empty_ind]
        was_added = was_added.str.rsplit(
            keyword_was).apply(lambda x: x.pop(0)).to_list()
        # it is to check the "You were added"  adding number
        if not any('You' in s for s in was_added):
            authors_list.extend(was_added)

    # combine all extracted contacts to single list
    authors_list.extend(joined_by_link)
    authors_list.extend(authors)

    # get the values which contains "left" keyword for left members
    keyword_left = 'left'
    left_mem = df[df['Message'].str.findall(
        keyword_left).astype(bool)]['Message']
    # get first value in the list
    l_m = left_mem.str.rsplit(
        keyword_left).apply(lambda x: x.pop(0)).to_list()
    left_mem = [s.strip() for s in l_m]  # trimming list elements
    # get only unique others out of left multiple times
    left_mem = list(set(left_mem))

    # get the values which contains "removed" keyword for removed members
    keyword_removed = 'removed'
    rem_members = df[df['Message'].str.findall(
        keyword_removed).astype(bool)]['Message']
    # get first value in the list
    r_m = rem_members.str.rsplit(
        keyword_removed).apply(lambda x: x.pop(1)).to_list()
    rem_members = [s.strip() for s in r_m]  # trimming list elements
    # get only unique others out of removed multiple times
    rem_members = list(set(rem_members))

    left_members = []
    removed_members = []
    active_members = []
    for author in left_mem + rem_members:
        # + is a special character and you have to escape it with \
        if author[0] == '+':
            activity = df['Message'].str.split(f'\{author}')
        else:
            activity = df['Message'].str.split(author)
        if any(activity.apply(lambda s: len(s) > 1)):
            acts = activity[activity.apply(lambda s: len(s) > 1)]
            # check last activity
            # author_act = acts.iloc[[-1]].str.find('added')
            # if not author_act.isna():
            cond_1 = any('left' in s for s in acts.iloc[-1])
            cond_2 = any(f'removed ' in s for s in acts.iloc[-1])
            if cond_1:
                left_members.append(author)
            elif cond_2:
                removed_members.append(author)
            else:
                active_members.append(author)
        else:
            active_members.append(author)
    active_members.extend(authors_list)
    # active_members = np.setdiff1d(active_members, inacctive_members)
    # get all authors by applying unique
    all_memebers = np.unique(active_members + joined_by_link +
                             rem_members + left_mem)
    # remove "you" author
    all_memebers = np.delete(all_memebers, np.where(
        [all_memebers == 'you', all_memebers == 'You']))
    active_members = np.setdiff1d(all_memebers, left_members + removed_members)
    group_members = (active_members.tolist(),
                     left_members,
                     removed_members, )
    return group_members


def find_day_of_chat(df, senders):
    """[summary]

    Args:
        df ([pandas dataframe]): [This dataframe contains all message statistics of the authors]
        senders ([list]): [authors who send messages in the group]

    Returns:
        sender_days ([dictionary]): [This dictionary contains the total messages sent on perticular day of the week]
    """
    # individual senders dictionary
    sender_days = OrderedDict()
    # whole dictionary
    group_sent_days = OrderedDict()
    # sent days by group
    sent_by_days = df['Date'].apply(lambda d: d.weekday()).to_list()
    # calculate number of sent messages day wise
    for day in range(7):
        group_sent_days[dayofweek(day)] = sum(
            [int(d == day) for d in sent_by_days])

    for sender in range(len(senders)):
        # find the weekdays of the week columns and convert to the list
        weekdays = df[df['Author'] == senders[sender]]['Date'].apply(
            lambda d: d.weekday()).to_list()
        # count the number of weekdays
        values = OrderedDict()
        for day in range(7):
            values[dayofweek(day)] = sum([int(d == day) for d in weekdays])
        sender_days[senders[sender]] = values

    return sender_days, group_sent_days


def plot_members_stats(request, key):
    # member week days plot
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

# this function to send the data to client
def plot_group_stats(request):
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


def emoji_stats(data_frame, authors):
    emojies_sent_member = OrderedDict()
    for sender in authors:
        # get author dataframe
        author_df = data_frame[data_frame['Author'] == sender]
        # filter only emojies to list
        total_emojis_list = list([a for b in author_df.Emoji for a in b])
        # count the each emojies count
        emoji_dict = dict(Counter(total_emojis_list))
        # create another dict for the each author
        emojies_sent_member[sender] = emoji_dict
    # calculate the all emojies
    all_emojies = data_frame['Emoji'].to_list()
    all_emojies = dict(Counter([item for sublist in all_emojies for item in sublist]))
    return emojies_sent_member, all_emojies

def sent_messages_over_time(df, members):
    # initialize ordereddict for maintaining order of values
    month_wise_data = OrderedDict()
    for sender in members:
        # get each sender dataframe from actual dataframe
        sender_df = df[df['Author'] == sender]
        # group the data by month and year with number of sent messages for each month and convert to dictionary 
        months_data = sender_df.groupby([sender_df['Date'].dt.year, sender_df['Date'].dt.month]).agg({'Author':len}).to_dict()
        # get dictionary data
        data = months_data['Author']
        # months list
        months_list = list(data.keys())
        # swap month to year by converting month number to string
        months_list = [(get_month(t[1]), t[0]) for t in months_list]
        # sent messages
        values_list = list(data.values())
        # insert all data 
        month_wise_data[sender] = [months_list, values_list]
    # remove none author
    all_messages = df[df['Author'].notnull()]
    # group sent messages by months
    months_data = all_messages.groupby([all_messages['Date'].dt.year, all_messages['Date'].dt.month]).agg({'Message':len}).to_dict()
    # get data 
    data = months_data['Message']
    # months list
    months_list = list(data.keys())
    # swap month to year by converting month number to string
    months_list = [(get_month(t[1]), t[0]) for t in months_list]
    # sent messages
    values_list = list(data.values())
    # its group activity
    group_activity = [months_list, values_list]
    return month_wise_data, group_activity
   
def chatting_time(df, members):
    # %%
    # individual statistics
    time_wise_data = OrderedDict()
    for sender in members:
        # get each sender dataframe from actual dataframe
        sender_df = df[df['Author'] == sender]
        # get the number od sent messages between two timings
        early_morning = len(sender_df[sender_df.Date.dt.strftime('%H:%M:%S').between('04:00:00','08:00:00')])
        morning = len(sender_df[sender_df.Date.dt.strftime('%H:%M:%S').between('08:00:00','13:00:00')])
        afternoon = len(sender_df[sender_df.Date.dt.strftime('%H:%M:%S').between('13:00:00','17:00:00')])
        evening = len(sender_df[sender_df.Date.dt.strftime('%H:%M:%S').between('17:00:00','22:00:00')])
        night = len(sender_df[sender_df.Date.dt.strftime('%H:%M:%S').between('22:00:00','23:59:00')]) + \
                len(sender_df[sender_df.Date.dt.strftime('%H:%M:%S').between('00:00:00','04:00:00')])
        time_wise_data[sender] = {'Early Morning(4am-8am)':early_morning,
                                  'Morning(8am-1pm)': morning,
                                  'Afternoon(1pm-5pm)':afternoon,
                                  'Evening(5pm-10pm)': evening,
                                  'Night(10pm-4am)': night, }
    # %%
    # overall statistics
    # all messages except none type
    all_messages = df[df['Author'].notnull()]
    early_morning = len(all_messages[all_messages.Date.dt.strftime('%H:%M:%S').between('04:00:00','08:00:00')])
    morning = len(all_messages[all_messages.Date.dt.strftime('%H:%M:%S').between('08:00:00','13:00:00')])
    afternoon = len(all_messages[all_messages.Date.dt.strftime('%H:%M:%S').between('13:00:00','17:00:00')])
    evening = len(all_messages[all_messages.Date.dt.strftime('%H:%M:%S').between('17:00:00','22:00:00')])
    night = len(all_messages[all_messages.Date.dt.strftime('%H:%M:%S').between('22:00:00','23:59:00')]) + \
            len(all_messages[all_messages.Date.dt.strftime('%H:%M:%S').between('00:00:00','04:00:00')])
    group_chating_time = [['Early Morning(4am-8am)', 'Morning(8am-1pm)', 'Afternoon(1pm-5pm)',
                           'Evening(5pm-10pm)', 'Night(10pm-4am)'], [early_morning, morning, afternoon, evening, night]]
    return time_wise_data, group_chating_time


def display_wordcloud(data_frame, authors):
    # delete previous generated images
    media_path = os.path.join(settings.MEDIA_ROOT, 'word_cloud_images')
    for filename in os.listdir(media_path):
        if filename.endswith('.jpg'):
            filepath = os.path.join(media_path, filename)
            try:
                rmtree(filepath)
            except OSError:
                os.remove(filepath)

    for i, sender in enumerate(authors):
        # get sender message dataframe
        sender_df = data_frame[data_frame['Author'] == sender]

        # join all text together as data
        data = ' '.join(sender_df['Typed'].to_list())
        
        # ! pending with emoji inclusion
        # emoji_path = os.path.join(settings.MEDIA_ROOT, 'NotoColorEmoji.ttf')
        try:
            # word cloud calling
            wordcloud = WordCloud(background_color='white',
                                  width=200, height=100,  
                                  max_words=200,
                                  max_font_size=40, 
                                  scale=3,
                                  random_state=1 # chosen at random by flipping a coin; it was heads
                                  ).generate(str(data))
            # plot data
            wordcloud.to_file(os.path.join(settings.MEDIA_ROOT, 'word_cloud_images', f'{i}.jpg'))
        except:
            src = os.path.join(settings.STATIC_ROOT, 'no_message.jpg')
            dst = os.path.join(settings.MEDIA_ROOT, 'word_cloud_images', f'{i}.jpg')
            copyfile(src, dst)
    
    data = ' '.join(data_frame['Typed'].to_list())
    try:
        wordcloud = WordCloud(background_color='white',
                                width=200, height=100,  
                                max_words=200,
                                max_font_size=40, 
                                scale=3,
                                random_state=1 # chosen at random by flipping a coin; it was heads
                                ).generate(str(data))
        # plot data
        wordcloud.to_file(os.path.join(settings.MEDIA_ROOT, 'word_cloud_images', 'group_word_cloud.jpg'))
    except:
        src = os.path.join(settings.STATIC_ROOT, 'no_message.jpg')
        dst = os.path.join(settings.MEDIA_ROOT, 'word_cloud_images', 'group_word_cloud.jpg')
        copyfile(src, dst)
    
def calculate_each_member_stats(df, author):
    # initialize ordered dictionary to store results
    all_members_stats = OrderedDict()
    all_members_stats['No_msgs'] = {}
    all_members_stats['No_links'] = {}
    all_members_stats['No_media'] = {}
    all_members_stats['No_deleted'] = {}
    all_members_stats['No_forward'] = {}
    all_members_stats['No_typed'] = {}
    all_members_stats['No_emoji'] = {}
    all_members_stats['No_words'] = {}

    for member in author:
        # get the member data from the whole dataframe
        sender_df = df[df['Author'] == member]
        # calculate the member statistics 
        # 1) Number of sent messages
        no_messages = len(sender_df['Message'])
        all_members_stats['No_msgs'].update({member: no_messages})
        # 2) Number of shared links
        no_links = sum(sender_df['isURL'])
        all_members_stats['No_links'].update({member: no_links})
        # 3) Number of sent media messages(Image, Audio, Video, Document, Contacts)
        no_media = sum(sender_df['isMedia'])
        all_members_stats['No_media'].update({member: no_media})
        # 4) Number of deleted messages
        no_deleted = sum(sender_df['isDeleted'])
        all_members_stats['No_deleted'].update({member: no_deleted})
        # 5) Number of forwarded messages
        no_forwarded = len(sender_df[(sender_df['Forwarded'] != '')])
        all_members_stats['No_forward'].update({member: no_forwarded})
        # 6) Number of typed messages
        no_typed = len(sender_df[(sender_df['Typed'] != '')])
        all_members_stats['No_typed'].update({member: no_typed})
        # 7) number of emojies used
        no_emojies = sum(sender_df['Emoji'].apply(len))
        all_members_stats['No_emoji'].update({member: no_emojies})
        # 8) average number of words per messages
        no_words_per_msg = sender_df['Typed'].apply(lambda s: len(s.split(' ')))
        avg_no_words_per_msg = sum(no_words_per_msg)/len(no_words_per_msg)
        all_members_stats['No_words'].update({member: round(avg_no_words_per_msg, 2)})
        # 9) time spent on whatsapp approximately

    # converting dictionary to lists so that list can be given directly in the template
    all_members_stats['No_msgs'] = [list(all_members_stats['No_msgs'].keys()),
                                  list(all_members_stats['No_msgs'].values())]
    all_members_stats['No_links'] = [list(all_members_stats['No_links'].keys()),
                                  list(all_members_stats['No_links'].values())]
    all_members_stats['No_media'] = [list(all_members_stats['No_media'].keys()),
                                  list(all_members_stats['No_media'].values())]
    all_members_stats['No_deleted'] = [list(all_members_stats['No_deleted'].keys()),
                                  list(all_members_stats['No_deleted'].values())]
    all_members_stats['No_forward'] = [list(all_members_stats['No_forward'].keys()),
                                  list(all_members_stats['No_forward'].values())]
    all_members_stats['No_typed'] = [list(all_members_stats['No_typed'].keys()),
                                  list(all_members_stats['No_typed'].values())]
    all_members_stats['No_emoji'] = [list(all_members_stats['No_emoji'].keys()),
                                  list(all_members_stats['No_emoji'].values())]
    all_members_stats['No_words'] = [list(all_members_stats['No_words'].keys()),
                                  list(all_members_stats['No_words'].values())]
    # members_stats['No_deleted'] = [list(members_stats['No_deleted'].keys()),
    #                               list(members_stats['No_deleted'].values())]
    # members_stats['No_deleted'] = [list(members_stats['No_deleted'].keys()),
    #                               list(members_stats['No_deleted'].values())]                             
    return all_members_stats


def call_footer(request):
    return render(request, 'groupchat/footer_messages.html')
    
def home(request):
    if request.method == 'POST' and request.FILES['chat_file']:
        
        chat_filename = create_local_chat_file(request.FILES['chat_file'])
        data_frame, member_stats = chat_analysis_main(
            chat_filename)

        first_msg = data_frame['Message'][0]
        first_date = data_frame['Date'][0].date()
        # get the time from data frame
        first_time = data_frame['Date'][0].time()
        # creator of the group member
        creator = first_msg.split(' created group')[0]
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

        # * From here functions manipulation functions are starting
        # function to find the number changes in the group names
        group_names = group_name_changes(none_data)
        # function to find the number changes in the group dps
        num_dp_changes, dp_last_change, dp_last_change_by = group_dp_changes(
            none_data, first_date, creator)
        
        group_members = find_active_members(none_data, authors)
        first_group_name = group_names[0][1]
        if len(group_names[0]) == 2:
            present_group_name = first_group_name
        else:
            present_group_name = group_names[-1][2]
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
        return render(request, 'groupchat/chat_analysis.html', {'first_msg': first_msg,
                                                                'first_date': first_date,
                                                                'first_time': first_time,
                                                                'first_group_name': first_group_name,
                                                                'present_group_name': present_group_name,
                                                                'creator': creator,
                                                                'group_members': group_members,
                                                                'dp_changes': dp_changes,
                                                                'msg_statistics': msg_statistics,
                                                                'group_names': group_names,
                                                                'member_stats': member_stats, })
        # 'data': data, })

    # else:
    #     form = UploadChatFileForm()
    return render(request, 'base.html')

