import re
import pandas as pd
import emoji
import numpy as np

#  this is the global variable for calculate the average word speed of the group memeber
avg_words = 10
# Average typing speed in mobile, actual reference is 38
avg_typing_speed = 25

def starts_with_date_and_time(s):
    # regex pattern for date.(Works only for android. IOS Whatsapp export format is different. Will update the code soon
    pattern = '^([0-9]+)(\/)([0-9]+)(\/)([0-9][0-9]), ([0-9]+):([0-9][0-9]) (am|pm|AM|PM) -'
    result = re.match(pattern, s)
    if result:
        return True
    return False

def get_data_point(current_line):
    split_line = current_line.split(' - ')
    date_time = split_line[0]
    date_from_line, time_from_line = date_time.split(', ')
    message_from_line = ' '.join(split_line[1:])
    split_message = message_from_line.split(': ')
    if len(split_message) > 1:
        author_from_line = split_message[0]
        message_from_line = ' '.join(split_message[1:])
    else:
        author_from_line = None

    return date_from_line, time_from_line, author_from_line, message_from_line


def split_count_emoji(text):
    emoji_list = []
    for word in text:
        if any(char in emoji.UNICODE_EMOJI for char in word):
            emoji_list.append(word)

    return emoji_list


def dayofweek(day):
    days = ["Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday", "Sunday"]
    return days[day]


# ---------------- starting --------------------
def chat_analysis_main(filename):
    parsed_data = []  # List to keep track of data so it can be used by a Pandas dataframe
    # Upload your file here
    conversation_path = filename  # chat file
    with open(conversation_path, encoding="utf-8") as fp:
        # Skipping first line of the file because contains information related to something about end-to-end encryption
        fp.readline()
        message_buffer = []
        date, time, author = None, None, None
        writer = 1
        while True:
            writer += 1
            line = fp.readline()
            if not line:
                break
            line = line.strip()
            if starts_with_date_and_time(line):
                if len(message_buffer) > 0:
                    parsed_data.append(
                        [f'{date} {time}', author, ' '.join(message_buffer)])
                message_buffer.clear()
                date, time, author, message = get_data_point(line)
                message_buffer.append(message)
            else:
                message_buffer.append(line)
        parsed_data.append([f'{date} {time}', author, ' '.join(message_buffer)])
    # Initializing a pandas Dataframe.
    data_frame = pd.DataFrame(parsed_data, columns=[
                              'Date', 'Author', 'Message'])
    data_frame["Date"] = pd.to_datetime(data_frame["Date"])
    # by default month showing as day and vice versa to eliminate apply this
    data_frame['Date'] = data_frame['Date'].dt.strftime('%d/%m/%Y %H:%M:%S')
    data_frame["Date"] = pd.to_datetime(data_frame["Date"])
    url_pattern = r'(https?://\S+)'
    data_frame['isURL'] = data_frame.Message.apply(
        lambda x: re.findall(url_pattern, x)).str.len()
    data_frame['isMedia'] = (data_frame['Message'] == '<Media omitted>').apply(int)
    media_messages_df = data_frame[data_frame['Message'] == '<Media omitted>']
    
    # This is the filter for deleted messages of author
    def deleted_filter(s):
        r = re.split('This message was deleted|You deleted this message', s)
        if sum([len(s) for s in r]) == 0:
            return 1
        else:
            return 0
    # deleted messages count
    data_frame['isDeleted'] = data_frame['Message'].apply(deleted_filter)
    # 
    data_frame['Letter_Count'] = data_frame['Message'].apply(
        lambda s: len(s))
    data_frame['Word_Count'] = data_frame['Message'].apply(
        lambda s: len(s.split(' ')))
    # Ignoring 1) deleted 
    #          2) media
    #          3) message word count more less tha 10 words for typed
    #          4) url 
    #          5) none author 
    filter_typed =  data_frame[(data_frame['isDeleted'] == 0) & (data_frame['isMedia'] == 0) & \
                    (data_frame['Word_Count'] < avg_words) & (data_frame['isURL'] == 0) & (data_frame['Author'].notnull())]
    filter_forwarded =  data_frame[(data_frame['isDeleted'] == 0) & (data_frame['isMedia'] == 0) & \
                    (data_frame['Word_Count'] > avg_words) & (data_frame['isURL'] == 0) & (data_frame['Author'].notnull())] 
    
    # make separate column for typed messages
    data_frame['Typed'] = filter_typed['Message']
    # replace nan values with empty string
    data_frame.Typed = data_frame.Typed.fillna('')
    # make separate column for forwarded messages
    data_frame['Forwarded'] = filter_forwarded['Message']
    # replace nan values with empty string
    data_frame.Forwarded = data_frame.Forwarded.fillna('')
    # find the emojies of the typed messages
    data_frame["Emoji"] = data_frame["Typed"].apply(split_count_emoji)
    # get group members
    authors = data_frame.Author.unique()
    authors = authors[authors != None]  # remove None author

    author_range = range(len(authors))
    
    # individual each member data
    author_msgs = [data_frame[data_frame["Author"] == authors[writer]]
                   for writer in author_range]
    # individual messages count of the each member in list
    num_msgs = [author_msgs[i].shape[0] for i in author_range]
    # individual average word count of the each member in list
    avg_words_msg = [round((np.sum(author_msgs[i]['Word_Count'])) /
                           author_msgs[i].shape[0], 2) for i in author_range]
    # individual time spent in min of the each member in list
    total_time_spent_min = [round(
        (np.sum(author_msgs[i]['Word_Count'])) / avg_typing_speed, 2) for i in author_range]
    # individual emojies count of the each member in list
    num_emojis = [sum(author_msgs[i]['Emoji'].str.len()) for i in author_range]
    # individual urls sent of the each member in list
    num_urls = [sum(author_msgs[i]['isURL']) for i in author_range]
    # individual media messages count of the each member in list
    media_msg = [media_messages_df[media_messages_df['Author']
                                   == authors[i]].shape[0] for i in author_range]
    # individual deleted messages count of the each member in list
    deleted_msg = [sum(author_msgs[i]['isDeleted']) for i in author_range]
    # creating dictionary with authors key and derived values from above
    member_stats = {author: [msg, emoji, urls, media, del_msg, words, time] for author, msg, emoji, urls, media, del_msg, words, time in
                    zip(authors, num_msgs, num_emojis, num_urls, media_msg, deleted_msg, avg_words_msg, total_time_spent_min)}
    # member_stats['authors'] = authors
    return data_frame, member_stats

