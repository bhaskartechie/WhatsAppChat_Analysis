import re
import pandas as pd
import emoji
import numpy as np


# from collections import Counter
# # from wordcloud import WordCloud
# import matplotlib.pyplot as plt
# import plotly.express as px


def starts_with_date_and_time(s):
    # regex pattern for date.(Works only for android. IOS Whatsapp export format is different. Will update the code soon
    pattern = '^([0-9]+)(\/)([0-9]+)(\/)([0-9][0-9]), ([0-9]+):([0-9][0-9]) (am|pm) -'
    result = re.match(pattern, s)
    if result:
        return True
    return False


# Finds username of any given format.
def find_author(s):
    patterns = ['([\w]+):',  # First Name
                '([\w]+[\s]+[\w]+):',  # First Name + Last Name
                '([\w]+[\s]+[\w]+[\s]+[\w]+):',  # First Name + Middle Name + Last Name
                '([+]\d{2} \d{5} \d{5}):',  # Mobile Number (India)
                '([+]\d{2} \d{3} \d{3} \d{4}):',  # Mobile Number (US)
                '([\w]+)[\u263a-\U0001f999]+:', ]  # Name and Emoji

    pattern = '^' + '|'.join(patterns)
    result = re.match(pattern, s)
    if result:
        return True
    return False


def get_data_point(current_line):
    split_line = current_line.split(' - ')
    date_time = split_line[0]
    date_from_line, time_from_line = date_time.split(', ')
    message_from_line = ' '.join(split_line[1:])
    if find_author(message_from_line):
        split_message = message_from_line.split(': ')
        author_from_line = split_message[0]
        message_from_line = ' '.join(split_message[1:])
    else:
        author_from_line = None
    return date_from_line, time_from_line, author_from_line, message_from_line


def split_count(text):
    emoji_list = []
    # data = re.findall(r'\X', text)
    for word in text:
        if any(char in emoji.UNICODE_EMOJI for char in word):
            emoji_list.append(word)

    return emoji_list


def dayofweek(day):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
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
                    parsed_data.append([date, time, author, ' '.join(message_buffer)])
                message_buffer.clear()
                date, time, author, message = get_data_point(line)
                message_buffer.append(message)
            else:
                message_buffer.append(line)
        parsed_data.append([date, time, author, ' '.join(message_buffer)])
    # Initialising a pandas Dataframe.
    data_frame = pd.DataFrame(parsed_data, columns=['Date', 'Time', 'Author', 'Message'])
    data_frame["Date"] = pd.to_datetime(data_frame["Date"])
    data_frame['Date'] = data_frame['Date'].dt.strftime('%d/%m/%Y')
    data_frame["Date"] = pd.to_datetime(data_frame["Date"])
    data_frame["emoji"] = data_frame["Message"].apply(split_count)
    url_pattern = r'(https?://\S+)'
    data_frame['urlcount'] = data_frame.Message.apply(lambda x: re.findall(url_pattern, x)).str.len()
    media_messages_df = data_frame[data_frame['Message'] == '<Media omitted>']
    messages_df = data_frame.drop(media_messages_df.index)
    messages_df['Letter_Count'] = messages_df['Message'].apply(lambda s: len(s))
    messages_df['Word_Count'] = messages_df['Message'].apply(lambda s: len(s.split(' ')))

    return data_frame, messages_df

#     for writer in range(len(authors)):
#         # Filtering out messages of particular user
#         req_df = messages_df[messages_df["Author"] == authors[writer]]
#         # req_df will contain messages of only one particular user
#         print(f'Stats of {authors[writer]} -')
#         # shape will print number of rows which indirectly means the number of messages
#         print('Messages Sent', req_df.shape[0])
#         # Word_Count contains of total words in one message. Sum of all words/ Total Messages will yield words per message
#         words_per_message = (np.sum(req_df['Word_Count'])) / req_df.shape[0]
#         print('Words per message', words_per_message)
#         # media consist of media messages
#         media = media_messages_df[media_messages_df['Author'] == authors[writer]].shape[0]
#         print('Media Messages Sent', media)
#         # emojis consist of total emojis
#         emojis = sum(req_df['emoji'].str.len())
#         print('Emojis Sent', emojis)
#         # links consist of total links
#         links = sum(req_df["urlcount"])
#         print('Links Sent', links)
#         print()
# #
# total_emojis_list = list(set([a for b in messages_df.emoji for a in b]))
# total_emojis = len(total_emojis_list)
# print(total_emojis)
# total_emojis_list = list([a for b in messages_df.emoji for a in b])
# emoji_dict = dict(Counter(total_emojis_list))
# emoji_dict = sorted(emoji_dict.items(), key=lambda x: x[1], reverse=True)
#
# emoji_df = pd.DataFrame(emoji_dict, columns=['emoji', 'count'])
# emoji_df
#
#
# fig = px.pie(emoji_df, values='count', names='emoji', title='Emoji Distribution')
# fig.update_traces(textposition='inside', textinfo='percent+label')
# fig.show()
# l = messages_df.Author.unique()
# for i in range(len(l)):
#   dummy_df = messages_df[messages_df['Author'] == l[i]]
#   total_emojis_list = list([a for b in dummy_df.emoji for a in b])
#   emoji_dict = dict(Counter(total_emojis_list))
#   emoji_dict = sorted(emoji_dict.items(), key=lambda x: x[1], reverse=True)
#   print('Emoji Distribution for', l[i])
#   author_emoji_df = pd.DataFrame(emoji_dict, columns=['emoji', 'count'])
#   fig = px.pie(author_emoji_df, values='count', names='emoji')
#   fig.update_traces(textposition='inside', textinfo='percent+label')
#   fig.show()
#
# text = " ".join(review for review in messages_df.Message)
# print('Group stats'.center(30, '-'))
# print(f'Messages          : {total_messages}')
# print(f'Media             : {media_messages}')
# print(f'Emojies           : {emojis}')
# print(f'Links             : {links}')
# print('-'*30)
# print("There are {} words in all the messages.".format(len(text)))
# # stopwords = set(STOPWORDS)
# # stopwords.update(["ra", "ga", "na", "ani", "em", "ki", "ah", "ha", "la", "eh", "ne", "le"])
# # Generate a word cloud image
#
# # wordcloud = WordCloud(background_color="white").generate(text)
# # # Display the generated image:
# # # the matplotlib way:
# #
# # plt.figure(figsize=(10, 5))
# # plt.imshow(wordcloud, interpolation='bilinear')
# # plt.axis("off")
# # plt.show()
#
# date_df = messages_df.groupby("Date").sum()
# date_df.reset_index(inplace=True)
# plt.plot(date_df)
# fig = px.line(date_df, x="Date", y="MessageCount", title='Number of Messages as time moves on.')
# fig.update_xaxes(nticks=20)
# fig.show()
# # plt.show()
#
# messages_df['Date'].value_counts().head(10).plot.barh()
# plt.xlabel('Number of Messages')
# plt.ylabel('Date')
# plt.show()
#
# messages_df['Time'].value_counts().head(10).plot.barh()
# plt.xlabel('Number of messages')
# plt.ylabel('Time')
# plt.show()

