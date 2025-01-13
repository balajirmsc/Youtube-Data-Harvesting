import googleapiclient.discovery
import pandas as pd
import psycopg2
import streamlit as st

#API key Connection
def api_connect():
    api_key=#Enter your API Key"
    api_service_name = "youtube"
    api_version = "v3"
    youtube=googleapiclient.discovery.build(api_service_name,api_version,developerKey=api_key)
    return youtube
youtube=api_connect()

#Database Connection
mydb=psycopg2.connect(host="Localhost",
                    user="postgres",
                    password="24682468",
                    database="youtube_data",
                    port="5432")
cursor=mydb.cursor()

#Get Channel Details
def get_channel_info(channel_id):
    ch_list=[]
    request = youtube.channels().list(
        part = 'snippet,contentDetails,statistics',
        id = channel_id
    )
    response = request.execute()

    for i in response['items']:
        data = dict(Channel_Name=i['snippet']['title'],
                    Channel_Id=i['id'],
                    Subscription_Count=i['statistics']['subscriberCount'],
                    Channel_Views=i['statistics']['viewCount'],
                    Total_Videos=i['statistics']['videoCount'],
                    Channel_Description=i['snippet']['description'],
                    Playlist_Id=i['contentDetails']['relatedPlaylists']['uploads'])
        ch_list.append(data)
    return ch_list

#Get Video Ids
def get_video_ids(channel_id):
    video_ids=[]
    response=youtube.channels().list(
        id =channel_id,
        part = 'contentDetails').execute()

    Playlist_Id= response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    next_page_token=None

    while True:
        response1=youtube.playlistItems().list(
                                                part='snippet',
                                                playlistId=Playlist_Id,
                                                maxResults=50,
                                                pageToken=next_page_token).execute()
        
        for i in range(len(response1['items'])):
            video_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token=response1.get('nextPageToken')
        
        if next_page_token is None:
            break
    return video_ids

#Get Video Details
def get_video_info(Video_ids):
    video_data=[]
    for video_id in Video_ids:
        request = youtube.videos().list(
            part='snippet, contentDetails, statistics',
            id=video_id
        )
        response=request.execute()

        for item in response["items"]:
            data =dict(Channel_Name=item['snippet']['channelTitle'],
                    Channel_Id=item['snippet']['channelId'],
                    Video_Id=item['id'],
                    Title=item['snippet']['title'],
                    Tags=item['snippet'].get('tags'),
                    Thumbnail=item['snippet']['thumbnails']['default']['url'],
                    Description=item['snippet'].get('description'),
                    Publish_Date=item['snippet']['publishedAt'],
                    Duration=item['contentDetails']['duration'],
                    Views=item['statistics'].get('viewCount'),
                    Like_Count=item['statistics'].get('likeCount',0),
                    Dislike_Count=item['statistics'].get('dislikeCount',0),
                    Comments_Count=item['statistics'].get('commentCount'),
                    Favorite_Count=item['statistics']['favoriteCount'],
                    Definition=item['contentDetails']['definition'],
                    Caption_Status=item['contentDetails']['caption']
                    )
            video_data.append(data)
    return video_data

#Get Comments Details
def get_comment_info(Video_ids):
    Comment_data=[]
    try:
        for video_id in Video_ids:
            request=youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=50
            )
            response=request.execute()

            for item in response['items']:
                data = dict(Comment_Id=item['snippet']['topLevelComment']['id'],
                            Video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                            Comments_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                            Comment_Author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                            Comment_Publish_Date=item['snippet']['topLevelComment']['snippet']['publishedAt'])
                
                Comment_data.append(data)
    except:
        pass

    return Comment_data

                                           
#Streamlit Details
st.title(":red[YouTube Data Harvesting]")
st.sidebar.header("Menu")

Options = st.sidebar.radio("Options", ("DATA COLLECTION","MIGRATE TO SQL","Channels","Queries"))

if Options=="DATA COLLECTION":
    C=st.text_input("Enter Channel ID")
    if C:
        Channel_Details=get_channel_info(channel_id=C)
        Video_Details=get_video_info(Video_ids=get_video_ids(channel_id=C))
        Comment_Details=get_comment_info(Video_ids=get_video_ids(channel_id=C))
    if st.button("submit"):
        st.success("ID Submitted Successfully")

        st.write("CHANNEL")
        st.dataframe(Channel_Details)
        st.write("VIDEOS")
        st.dataframe(Video_Details)
        st.write("COMMENTS")
        st.dataframe(Comment_Details)

#SQL Part
if Options == "MIGRATE TO SQL":
    C = st.text_input("Enter Channel ID")
    if st.button("Migrate to SQL"):
            try:
                #Create Channels
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS channels (
                        Channel_Name VARCHAR(100),
                        Channel_Id VARCHAR(80) PRIMARY KEY,
                        Subscription_Count BIGINT,
                        Channel_Views BIGINT,
                        Total_Videos INT,
                        Channel_Description TEXT,
                        Playlist_Id VARCHAR(80)
                    )
                ''')

                #Create Videos
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS videos (
                        Channel_Name VARCHAR(100),
                        Channel_Id VARCHAR(100),
                        Video_Id VARCHAR(30) PRIMARY KEY,
                        Title VARCHAR(150),
                        Tags TEXT,
                        Thumbnail VARCHAR(200),
                        Description TEXT,
                        Publish_Date TIMESTAMP,
                        Duration INTERVAL,
                        Views BIGINT,
                        Like_Count BIGINT,
                        Dislike_Count BIGINT,
                        Comments_Count INT,
                        Favorite_Count INT,
                        Definition VARCHAR(10),
                        Caption_Status VARCHAR(50)
                    )
                ''')

                #Create Comments
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS comments (
                        Comment_Id VARCHAR(100) PRIMARY KEY,
                        Video_Id VARCHAR(50),
                        Comments_Text TEXT,
                        Comment_Author VARCHAR(150),
                        Comment_Publish_Date TIMESTAMP
                    )
                ''')
                mydb.commit()
                cursor.close()
                print("Tables created successfully")

                df_channel=pd.DataFrame(get_channel_info(channel_id=C))
                df_video=pd.DataFrame(get_video_info(Video_ids=get_video_ids(channel_id=C)))
                df_comments=pd.DataFrame(get_comment_info(Video_ids=get_video_ids(channel_id=C)))

                #Insert Channels
                cursor = mydb.cursor()
                for index, row in df_channel.iterrows():
                    table_insert_query = '''insert into channels(Channel_Name,
                                                        Channel_Id,
                                                        Subscription_Count,
                                                        Channel_Views,
                                                        Total_Videos,
                                                        Channel_Description,
                                                        Playlist_Id)
                                                        values(%s, %s, %s, %s, %s, %s, %s)'''
                    values = (row['Channel_Name'],
                        row['Channel_Id'],
                        row['Subscription_Count'],
                        row['Channel_Views'],
                        row['Total_Videos'],
                        row['Channel_Description'],
                        row['Playlist_Id'])
                    cursor.execute(table_insert_query, values)
                mydb.commit()
                cursor.close()
                
                #Insert Videos
                cursor = mydb.cursor()
                for index, row in df_video.iterrows():
                    table_insert_queryy = '''insert into videos(Channel_Name,
                                                    Channel_Id,
                                                    Video_Id,
                                                    Title,
                                                    Tags,
                                                    Thumbnail,
                                                    Description,
                                                    Publish_Date,
                                                    Duration,
                                                    Views,
                                                    Like_Count,
                                                    Dislike_Count,
                                                    Comments_Count,
                                                    Favorite_Count,
                                                    Definition,
                                                    Caption_Status)
                                                        
                                                        values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
                    values = (row['Channel_Name'],
                        row['Channel_Id'],
                        row['Video_Id'],
                        row['Title'],
                        row['Tags'],
                        row['Thumbnail'],
                        row['Description'],
                        row['Publish_Date'],
                        row['Duration'],
                        row['Views'],
                        row['Like_Count'],
                        row['Dislike_Count'],
                        row['Comments_Count'],
                        row['Favorite_Count'],
                        row['Definition'],
                        row['Caption_Status'])
                    cursor.execute(table_insert_queryy, values)
                mydb.commit()
                cursor.close()

                #Insert Comments
                cursor = mydb.cursor()
                for index, row in df_comments.iterrows():
                    table_insert_query2 = '''insert into comments(Comment_Id,
                                                        Video_Id,
                                                        Comments_Text,
                                                        Comment_Author,
                                                        Comment_Publish_Date
                                                        )
                                                        values(%s, %s, %s, %s, %s)'''
                    values = (row['Comment_Id'],
                            row['Video_Id'],
                            row['Comments_Text'],
                            row['Comment_Author'],
                            row['Comment_Publish_Date'])
                    cursor.execute(table_insert_query2, values)

                mydb.commit()
                cursor.close()
                st.success("MIGRATED SUCCESSFULL")
            except:
                 st.success("Channel ID Already Exists")

#Display Channels
if Options=="Channels":
    try:
        select_query = '''SELECT Channel_Name FROM CHANNELS'''
        cursor.execute(select_query)
        st.header("THESE ARE CHANNELS ADDED IN DATABASE")

        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        df = pd.DataFrame(results, columns=column_names)
        st.dataframe(df)
    except:
         st.write("No Channels added in Database")


#Queries Section
if Options=="Queries":
    st.header("SELECT THE QUESTIONS TO GET INSIGHTS")
    options=st.selectbox("Select options",
                         ("1.What are the names of all the videos and their corresponding channels?",
                          "2.Which channels have the most number of videos, and how many videos do they have?",
                          "3.What are the top 10 most viewed videos and their respective channels?",
                          "4.How many comments were made on each video, and what are their corresponding video names?",
                          "5.Which videos have the highest number of likes, and what are their corresponding channel names?",
                          "6.What is the total number of likes and dislikes for each video, and what are their corresponding video names?",
                          "7.What is the total number of views for each channel, and what are their corresponding channel names?",
                          "8.What are the names of all the channels that have published videos in the year 2022?",
                          "9.What is the average duration of all videos in each channel, and what are their corresponding channel names?",
                          "10.Which videos have the highest number of comments, and what are their corresponding channel names?"))
    
    # Query 1
    if options=="1.What are the names of all the videos and their corresponding channels?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Title,Channel_Name from videos
                                   order by Channel_Name''')
                out=cursor.fetchall()
                que_1=pd.DataFrame(out,columns=["Video Title","Channel Name"])
                st.success("ANSWER")
                st.write(que_1)

    # Query 2
    elif options=="2.Which channels have the most number of videos, and how many videos do they have?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Channel_Name, Total_Videos from channels
                                    order by Total_Videos  desc''')
                out=cursor.fetchall()
                que_2=pd.DataFrame(out,columns=["Channel Name","Video Counts"])
                st.success("ANSWER")
                st.write(que_2)

    # Query 3
    elif options=="3.What are the top 10 most viewed videos and their respective channels?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Channel_Name,Title,Views  from videos
                                order by Views desc limit 10''')
                out=cursor.fetchall()
                que_3=pd.DataFrame(out,columns=["Channel Name","Video Title","Video Views"])
                st.success("ANSWER")
                st.write(que_3)

    # Query 4
    elif options=="4.How many comments were made on each video, and what are their corresponding video names?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Comments_Count,Title from videos
                                    where Comments_Count is not null
                                    order by Comments_Count desc''')
                out=cursor.fetchall()
                que_4=pd.DataFrame(out,columns=["No of Comments","Video Title"])
                st.success("ANSWER")
                st.write(que_4)

    # Query 5
    elif options=="5.Which videos have the highest number of likes, and what are their corresponding channel names?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Title,Like_Count,Channel_Name  from videos
                                    order by Like_Count desc''')
                out=cursor.fetchall()
                que_5=pd.DataFrame(out,columns=["Video Title","Likes","Channel Name"])
                st.success("ANSWER")
                st.write(que_5)

    # Query 6
    elif options=="6.What is the total number of likes and dislikes for each video, and what are their corresponding video names?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Title,Like_Count,Dislike_Count  from videos
                                    order by Dislike_Count desc''')
                out=cursor.fetchall()
                que_6=pd.DataFrame(out,columns=["Video Title","Likes","Dislikes"])
                st.success("ANSWER")
                st.write(que_6)

    # Query 7
    if options=="7.What is the total number of views for each channel, and what are their corresponding channel names?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Channel_Name,Channel_Views from channels
                                    order by Channel_Views desc ''')
                out=cursor.fetchall()
                que_7=pd.DataFrame(out,columns=["Channel Name","Total Views"])
                st.success("ANSWER")
                st.write(que_7)

    # Query 8
    if options=="8.What are the names of all the channels that have published videos in the year 2022?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Title,Publish_Date, Channel_Name from videos
                                    where extract(year from Publish_Date)=2022
                                ''')
                out=cursor.fetchall()
                que_8=pd.DataFrame(out,columns=["Video Title","Published Date","Channel Name"])
                st.success("ANSWER")
                st.write(que_8)

    # Query 9
    if options=="9.What is the average duration of all videos in each channel, and what are their corresponding channel names?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Channel_Name,avg(Duration) from videos
                                    group by Channel_Name
                                ''')
                out=cursor.fetchall()
                que_9=pd.DataFrame(out,columns=["Channel Name","Average Duration"])
                st.success("ANSWER")
                st.write(que_9)

    # Query 10
    if options=="10.Which videos have the highest number of comments, and what are their corresponding channel names?":
            if st.button("SUBMIT"):
                cursor.execute(''' select Title,Channel_Name,Comments_Count from videos
                                    where Comments_Count is not null order by Comments_Count desc''')
                out=cursor.fetchall()
                que_10=pd.DataFrame(out,columns=["Video Title","Channel Name","Comments Count"])
                st.success("ANSWER")
                st.write(que_10)

#Already Added Channels:
#Hip Hop Gaming Tamil     : UCqqN6TIACv7pcDQoyqT4vvA
#Yudesh gaming tamil      : UCFTNbPMXVWXvv6qZZnxVw5Q
#vicky bhai gaming tamil  : UCDMPc1thXdVD_meLANv6OAA
#Vijay Gaming Tamil       : UCiABDuYJQfmP7x8v9JXVDXg
#Pg Gaming tamil          : UC2D74rb1z9wFiAoVPGBjRTQ
#Skull Gaming Tamil       : UCeOnlDpvtsiX3CkG1QFIMxQ
#GameMaster Balaji        : UCumrEa02mYn9nlLYdGGKqRw
#CodeX LearnN Tamil       : UCJkZuVwzwW5igYg3WjIru4g
#Smart learn tamil        : UCXGV7Zn4QQdg0BnujTwCPXQ
# Data Science with Ranga : UCLxUFOYeUMJVFfG0mb97Mmg                
