from twitterflash import TwitterFlash
from config import time_interval
from config import db_connection, database_name, collection_fixtures, collection_name

import schedule
from celery import Celery
from billiard.exceptions import Terminated

# delete these two lines pls
# import os
from time import sleep

app = Celery('tasks')
app.config_from_object('celeryconfig')


def start_process(obj):
    schedule.every(time_interval).seconds.do(obj.run) # scheduling function to run with time_interval provided
    try:
        while True:
			schedule.run_pending()
    except Exception, e:
            pass
        

@app.task(throws=(Terminated,))
def twitter_task(sport_type, series_id, match_id):
	try:
		
		# setting the fields
		fields = {'sport':sport_type, 'series_id':series_id, 'match_id':match_id}

		# get the doc with match info from database
		coll_schedule = db_connection[database_name][collection_name]
		doc = coll_schedule.find_one(fields)

		# getting the hashtag string and the ready flag
		hashtags = doc['hashtags']
		ready = doc['ready']

		# if match is scheduled for twitter
		# i.e. if ready flag is 'true'
		if ready:
			# change staus of this match to RUNNING
			coll_schedule.update_one(fields, {"$set":{"status": "RUNNING"}})
			obj = TwitterFlash()
			obj.set_game_params(sport_type, series_id, match_id, hashtags)
			start_process(obj)
		else:
			# change status of this match to DECLINED
			coll_schedule.update_one(fields, {"$set":{"status": "DECLINED"}})
	except Exception, e:
		print 'Error in running task in celery', str(e)
		
