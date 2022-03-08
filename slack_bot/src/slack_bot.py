import pandas as pd
from sqlalchemy import create_engine
import requests
import os
#import pyjokes

# webhook_url = os.getenv('my_slack_channel')
webhook_url = os.getenv('my_personal_slack')

engine = create_engine(os.getenv('POSTGRESDB_URI'))

tweets = pd.read_sql_table('tweets', engine, index_col=0)

tweets = tweets.iloc[5]

print(tweets)

data = {'text': f"---New Tweet message ---\n{tweets['name']}: {tweets['message']}\n ---Sentiment score ---\n{tweets['sentiment']}"}

#data = {'text': f"{tweets}"}
requests.post(url=webhook_url, json = data)