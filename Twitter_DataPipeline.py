import os
from dotenv import load_dotenv
load_dotenv()
import argparse
import tweepy
import json
from pymongo import MongoClient
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
from sqlalchemy import create_engine
import psycopg2


class TwitterDataPipeline:
    def __init__(self, arg):
        self.username = arg.username
        # print(self.username) # elonmusk

    def run(self):
        # collects tweets
        self.collect_tweets()
        # Store tweets in JSON file
        tweets_cursor = self.collect_tweets()
        self.store_tweets_in_json(tweets_cursor)
        # Connects to MongoDB
        self.connect_to_mongodb()
        # Stores JSON file contents in MongoDB
        self.store_json_in_mongodb()
        # Updates accuracy field of the collection and stores in MongoDB
        self.accuracy_store_mongodb()
        # Extract data from MongoDB to JSON file
        self.extract_final_json()
        # Converting JSON to Pandas DataFrame
        dataframe = self.json_to_pandas()
        # Converting dataframe to CSV
        self.dataframe_to_csv(dataframe)

    def collect_tweets(self):
        # Provides Authentication to collect tweets
        self.authentication()
        # Collect user_info
        self.user_information = self.collect_user_info()
        # Collect tweets of the user provided
        tweets_cursor = self.collect_user_tweets(self.user_information)

        return tweets_cursor

    def authentication(self):
        """Authentication to collect tweets from Twitter API"""
        BEARER_TOKEN = os.getenv('BEARER_TOKEN')
        self.client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

    def collect_user_info(self):
        """Collects information about the user"""
        response = self.client.get_user(
            username=self.username,
            user_fields=['created_at', 'description', 'location',
                         'profile_image_url', 'public_metrics']
        )

        self.user_info = dict(response.data)
        # print(self.user_info)
        # print(self.user_info['name']) # Elon Musk
        return self.user_info

    def collect_user_tweets(self, user_information):
        cursor = tweepy.Paginator(
            method=self.client.get_users_tweets,
            id=user_information['id'],
            exclude=['retweets', 'replies']
        ).flatten(limit=200)

        # for tweet in cursor:
        #     print(f"\n{tweet}")

        return cursor

    def store_tweets_in_json(self, tweets_cursor):
        tweets_list = []
        count = 1
        with open('tweets.json', 'w') as json_file:
            for tweet in tweets_cursor:
                # tweets = {self.user_information['name']: dict(tweet)} # {'Elon Musk': {'id': 1520017094007476224, 'text': 'The far left hates everyone, themselves included!'}}
                tweets = {count: dict(tweet)}
                count += 1
                # print(tweets)
                tweets_list.append(tweets)

            json.dump(tweets_list, json_file, indent=4)

            # print(tweets_list)

    def connect_to_mongodb(self):
        self.cluster = MongoClient(os.getenv('MongoDB_Conn'))
        db = self.cluster["MyProjects"]
        self.collection = db["tweets"]

        # post = {"_id": 108, "name": "jazz", "score": 7}
        # self.collection.insert_one(post)

    def store_json_in_mongodb(self):
        with open('tweets.json', 'r') as tweets_json:
            tweets_file = json.load(tweets_json)
            for data in tweets_file:
                for key, value in data.items():
                    json_in_dict = {
                        '_id': value['id'],
                        'username': self.user_information['username'],
                        'tweet': value['text']
                    }
                    # print(json_in_dict)
                    try:
                        self.collection.insert_one(json_in_dict)
                    except:
                        continue

    def tweets_sentiment_analysis(self, text):
        s = SentimentIntensityAnalyzer()
        sentiment = s.polarity_scores(text)

        return sentiment

    def accuracy_store_mongodb(self):
        tweets = self.collection.find({})
        for tweet in tweets:
            tweets_sentiment = self.tweets_sentiment_analysis(tweet['tweet'])

            # print(tweets_sentiment)
            self.collection.update_one({'_id': tweet['_id']},
                                   {"$set":
                                        {'sentiment': tweets_sentiment}
                                    }
                                   )

    def extract_final_json(self):
        """Extract data in JSON format which will be used for Tableau visualization"""
        final_tweets_list = []
        count = 1
        all_tweets = self.collection.find({})
        with open('all_tweets.json', 'w') as final_data:
            for tweet in all_tweets:
                tweets = {count: dict(tweet)}
                count += 1
                # print(tweets)
                final_tweets_list.append(tweets)

            json.dump(final_tweets_list, final_data, indent=4)

    def json_to_pandas(self):
        """Make unstructured to structured data using Pandas Dataframe."""
        with open('all_tweets.json', 'r') as f:
            data = json.load(f)
            records = []
            for count, value in enumerate(data):
                # print(value)
                for key, val in value.items():
                    # print(val)
                    records.append(val)
            # print(records)

            result = pd.json_normalize(records)
            # print(result)
            return result

    def dataframe_to_csv(self, dataframe):
        """Stores dataframe in CSV file"""
        dataframe.to_csv('tweets.csv', encoding='utf-8')


def parsing_arguments():
    """Provide arguments from Command Line."""

    # Initialize the parser
    parser = argparse.ArgumentParser()

    # Adding arguments
    parser.add_argument("username", help="Collects tweets of the user provided.")

    # Read the arguments from command line
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    arg = parsing_arguments()
    obj = TwitterDataPipeline(arg)
    obj.run()