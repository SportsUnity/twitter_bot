import config
from scheduler import SportsUnityScheduler

from tasks import twitter_task

from flask import Flask, render_template, jsonify
from flask import request as rq

from time import time
from datetime import datetime, timedelta
import json

app = Flask(__name__)

import requests
# import io
# from flask import send_file

def get_the_dates():
	l = []
	for i in xrange(3):
		x = datetime.now()+timedelta(days=i)
		l.append(x.strftime("%d-%m-%Y"))
	return l


@app.route('/')
def index():
	dates = get_the_dates()
	return render_template('home.html', dates=dates)


def update_database():
	obj = SportsUnityScheduler()
	obj.update_database()


def get_schedule_from_db(date_val, sport_type):
	try:
		coll = config.db_connection[config.database_name][config.collection_name]

		# setting the fields that need to be extracted
		projections = {'_id':False, 'series_name':True, 'home_team':True, 'away_team':True, 'hashtags':True}
		projections.update({'time':True, 'series_id':True, 'match_id':True, 'status':True})
		games = list(coll.find({'date':date_val, 'sport':sport_type}, projections))
		if not games:
			# convert the date string into epoch value
			date_epoch = int(datetime.strptime(date_val, '%d-%m-%Y').strftime("%s"))

			# check the latest match epoch for the sport type
			coll_dates = config.db_connection[config.database_name][config.collection_dates]
			latest_epoch = coll_dates.find_one({'sport':sport_type})

			# if latest_epoch is avaliable and the data till the latest epoch 
			# time is already parsed, then return the empty list since there 
			# are not matches for the sport_type on this date
			if latest_epoch:
				if date_epoch <= latest_epoch['epoch']:
					return {'success':True, 'error':False, 'data': []}

			# if latest_epoch is not avaliable (i.e. no DB is constructed), or if the present date epoch 
			# is greater than the latest match epoch present in the databse for the given sport, we update
			# the database since we dont have matches data for the present day matches 
			update_database()
			games = list(coll.find({'date':date_val, 'sport':sport_type}, projections))

		return {'success':True, 'error':False, 'data': games}
	except Exception as e:
		print str(e)
		return {'success':False, 'error':True, 'message':'Internal Server Error'}


@app.route('/get-schedule', methods=['POST'])
def get_schedule():
	# get the date from the webpage
	date_val = rq.form.get('date')
	sport_type = rq.form.get('sport')
	return jsonify(get_schedule_from_db(date_val, sport_type))


@app.route('/scheduler-handler', methods=['GET'])
def scheduler_handler():
	try:
		# getting the 'schedule' collection from database
		coll_schedule = config.db_connection[config.database_name][config.collection_name]

		# getting the fields from the web-form to filter the document from collection
		fields = {'sport':rq.args.get('sport'), 'series_id':rq.args.get('series_id'), 'match_id':rq.args.get('match_id')}

		# getting the document with sport, series_id and match_id
		# from schedule collection 
		schedule_doc = coll_schedule.find_one(fields)

		# getting the hashtags string from the web page
		hashtags = rq.args.get('hashtags')

		# if this match is not assigned before in the celery queue	
		if not schedule_doc['in_celery_queue']:
			# setting in_celery_queue flag to True to indicate
			# that it is now placed in the celery queue
			coll_schedule.update_one(fields, {"$set":{"in_celery_queue": True}})
			# getting the epoch time from scheule doc
			epoch = schedule_doc['epoch']

			# placing the task into queue with schedule time equals to : epoch_time - current_time 
			# (i.e. start this process after seconds difference in the current_time and the match time)
			game_args = (fields['sport'], fields['series_id'], fields['match_id'])
			game_countdown = int(epoch - round(int(time())))
			
			# twitter_task.delay(fields['sport'], fields['series_id'], fields['match_id'])
			twitter_task.apply_async(args=game_args, countdown=game_countdown)

		# toggle status and ready Flag and save the hashtags it into database
		status = 'SCHEDULED' if schedule_doc['status'] == 'UNSCHEDULED' else 'UNSCHEDULED'
		ready_state = not schedule_doc['ready']
		coll_schedule.update_one(fields, {"$set":{"status": status, "ready":ready_state,"hashtags":hashtags}})

		return jsonify({'success':True, 'error':False, 'message':'Saved Successfully'})
	except Exception, e:
		# print str(e)
		return jsonify({'success': False, 'error':True, 'message':'Server Error in Saving Schedule'}), 500


@app.route('/change-game-hashtags', methods=['GET'])
def change_hashtags():
	try:
		# getting the 'schedule' collection from database
		coll_schedule = config.db_connection[config.database_name][config.collection_name]
		# getting the fields from the web-form to filter the document from collection
		fields = {'sport':rq.args.get('sport'), 'series_id':rq.args.get('series_id'), 'match_id':rq.args.get('match_id')}

		# getting the hashtag string and saving it in the database
		hashtags = rq.args.get('hashtags')
		coll_schedule.update_one(fields, {"$set":{"hashtags":hashtags}})

		return jsonify({'success':True, 'error':False, 'message':'Hashtags Saved Successfully'})
	except Exception, e:
		print str(e)
		return jsonify({'success': False, 'error':True, 'message':'Server Error in Saving Hashtags'}), 500		

	
if __name__=='__main__':
	app.run(debug=True, port=8888)