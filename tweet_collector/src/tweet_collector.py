# print('import all nescessary libraries')
import tweepy
import os
import logging
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

#filters/levels: priority of the log messages

# DEBUG: detailed diagnostic output
# INFO: status monitoring, everything is working as expected
# WARNING: no immediate action required, something happened (eg disk space low)
# ERROR(CRITICAL also high): some exception to solve, software unable to perform some function

logging.basicConfig(
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='/log/etl.log', filemode='w'
)


# Twitter API Authentification
auth = tweepy.OAuthHandler(os.getenv('API_Key'), os.getenv('API_Secret'))
auth.set_access_token(os.getenv('access_token'), os.getenv('access_token_secret'))
api = tweepy.API(auth)
logging.debug('Twitter API Authentification completed.')


# Getting full tweet text for a specific user by Creating a Cursor object
cursor = tweepy.Cursor(
                        api.search,
                        q='modi',             # filter:retweets ( filter out retweets, make an OR query or exact match)
                        tweet_mode='extended',
                        lang = 'en')
logging.debug('Cursor created.')


twts = 100
created = []
screen_names = []
messages = []
sentiments = []

for status in cursor.items(twts):
     created.append(status.created_at)
     screen_names.append(status.user.screen_name)
     messages.append(status.full_text)
     sentiment_analysis = SentimentIntensityAnalyzer().polarity_scores(status.full_text)
     sentiments.append(sentiment_analysis['compound'])
logging.debug('Data collected from Twitter API.')


# logging.info(f"start loading data into {os.getenv('POSTGRESDB_URI')}")

# Creating Dataframe
df = pd.DataFrame({
    'date': created,
    'name': screen_names,
    'message': messages,
    'sentiment': sentiments
})
# logging.debug('Dataframe created')


# Connecting with Postgresql and creating table
create_query = """
    CREATE TABLE tweets(
        id SERIAL PRIMARY KEY,
        date TIMESTAMP,
        name VARCHAR,
        message TEXT,
        sentiment FLOAT
    )    
"""
    
drop_query = "DROP TABLE IF EXISTS tweets"


engine = create_engine(os.getenv('POSTGRESDB_URI'))

with engine.connect() as conn:
    conn.execute(drop_query)    
    conn.execute(create_query)


df.to_sql('tweets', engine, if_exists='append', index=False)

logging.debug('Tweeter info stored in database.')