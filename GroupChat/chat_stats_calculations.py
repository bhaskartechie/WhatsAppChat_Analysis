import os
import numpy as np
from collections import OrderedDict, Counter
from .WhatsApp_chat_analysis import chat_analysis_main, dayofweek
import time
from shutil import copyfile, rmtree
from wordcloud import WordCloud
from django.conf import settings

# from chartjs.views.lines import BaselLineChartView
#  this is the global variable for calculate the average word speed of the group member
avg_words = 10

# ! this decoratore function is used  for to measure time of execution of the function only
# def timeit(method):
#     def timed(*args, **kw):
#         ts = time.time()
#         result = method(*args, **kw)
#         te = time.time()
#         if 'log_time' in kw:
#             name = kw.get('log_name', method.__name__.upper())
#             kw['log_time'][name] = int((te - ts) * 1000)
#         else:
#             print('%r  %2.2f ms' % \
#                   (method.__name__, (te - ts) * 1000))
#         return result
#     return timed

# @timeit
def create_local_chat_file(fd):
    try:
        chat_filename = os.path.join(settings.MEDIA_ROOT, 'temp_chat_file.txt')
        with open(chat_filename, 'wb+') as destination:
            for chunk in fd.chunks():
                destination.write(chunk)
        return chat_filename
    except Exception as e:
        raise e

# function to count the number of times group dp changed
# @timeit
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
# @timeit
def group_name_changes(df):
    # this key term used to find the changes in the group name
    key_terms = 'changed the subject from '
    data_frame = df[df["Message"].str.contains(key_terms)]
    # returns first argument is group name changes data and second arguments are flags 
    # 1- group name is available and no group name changes
    # 2- group name is available and has group name changes
    # 3- no group names is available
    if data_frame.empty:
        first_message = df.iloc[0]['Message']
        if  first_message.find(' created group ') != -1:
        # this is to filter first message for the group name changes
            return [first_message[0:first_message.find(' created')], first_message[first_message.find(
                    'created group "') + len('created group "'):first_message.rfind('"')]], 1
        else:
            return ['Group Name Not Available'], 3
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
    
    return temp_df[temp_df.astype(bool)].to_list(), 2


# this function finds the active and left members from the group
# @timeit
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
    # split list elements by ',' and convert to the list, its list of list elements
    authors_list_of_lists = added_persons.str.split(',').to_list()
    # flatten list by striping strings
    authors_list = [item.strip()
                    for sublist in authors_list_of_lists for item in sublist]
    # remove any nulls
    authors_list = list(filter(None, authors_list))
    # get only unique others out of added multiple times
    authors_list = list(set(authors_list))

    # ---------this snippet for the string "joined using this" search
    keyword_link = 'joined using this'
    link_joining = df[df['Message'].str.findall(
        keyword_link).astype(bool)]['Message']
    link_joining = link_joining.str.rsplit(
        keyword_link).apply(lambda x: x.pop(0)).to_list()
    joined_by_link = [s.strip() for s in link_joining]
    # get only unique others out of added multiple times by link
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
        # + is a special character and you have to escape it with beckslash
        if author[0] == '+':
            activity = df['Message'].str.split(f'\{author}')
        else:
            activity = df['Message'].str.split(author)
        if any(activity.apply(lambda s: len(s) > 1)):
            acts = activity[activity.apply(lambda s: len(s) > 1)]
            # check last activity
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

# @timeit
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
# @timeit
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

# @timeit
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

# @timeit
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

# @timeit
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

def busiest_day_of_chat(df):
    high_msgs_counts = df['Date'].dt.date.value_counts()
    busiest_day = high_msgs_counts.index[0]
    busy_day_messages = high_msgs_counts[busiest_day]
    total_messages = len(df[df['Author'].notnull()])
    grp_started_on = df['Date'].min()
    grp_last_msg_on = df['Date'].max() 
    total_days = (grp_last_msg_on - grp_started_on).days
    average_messages_per_day = round(total_messages / total_days)
    return (busiest_day, busy_day_messages, average_messages_per_day, grp_started_on, grp_last_msg_on, total_days)

# %%
def personal_data_arrangement(authors, author_stats, mem_days, emoji_sent_member, \
                                  each_month_data_author, author_chat_time, busy_day):
                                  
    arranged_data = []
    for key, val in author_stats.items():
        if key == 'No_msgs':
            arranged_data.append([val[1][0], 'Sent messages', val[1][1]])
        elif key == 'No_links':
            arranged_data.append([val[1][0], 'Links shared', val[1][1]])
        elif key == 'No_media':
            arranged_data.append([val[1][0], 'Media(Pics/Video/Audio/Doc)', val[1][1]])
        elif key == 'No_deleted':
            arranged_data.append([val[1][0], 'Deleted', val[1][1]])
        elif key == 'No_forward':
            arranged_data.append([val[1][0], 'Forworded messages', val[1][1]])
        elif key == 'No_typed':
            arranged_data.append([val[1][0], 'Typed messages', val[1][1]])
        elif key == 'No_emoji':
            arranged_data.append([val[1][0], 'Sent Emojies', val[1][1]])
            # get both authors sent emojies dictionaries
            author_1 = emoji_sent_member[list(emoji_sent_member)[0]]
            author_2 = emoji_sent_member[list(emoji_sent_member)[1]]
            arranged_data.append([max(author_1, key=author_1.get), 'Most used Emoji', max(author_2, key=author_2.get)])
        elif key == 'No_words':
            arranged_data.append([val[1][0], 'Average Words per messages', val[1][1]])
    
    # most sent days of the week
    author_1 = mem_days[list(mem_days)[0]]
    author_2 = mem_days[list(mem_days)[1]]
    arranged_data.append([max(author_1, key=author_1.get), 'Most sent messages on the week day', ''])
    # time of the chat time in a day
    author_1 = author_chat_time[list(author_chat_time)[0]]
    author_2 = author_chat_time[list(author_chat_time)[1]]
    arranged_data.append([max(author_1, key=author_1.get), 'Your preferred timing for messaging', ''])
    # most messages sent month 
    author_1 = each_month_data_author[list(each_month_data_author)[0]]
    author_2 = each_month_data_author[list(each_month_data_author)[1]]
    month, year = author_1[0][author_1[1].index(max(author_1[1]))]
    arranged_data.append([f'{month}, {year}', 'Most sent messages in the month with messages:', max(author_1[1]) + max(author_2[1])])

    # busiest day of both
    arranged_data.append([busy_day[0], 'Most sent messages on the day with messages', busy_day[1]])

    return arranged_data
