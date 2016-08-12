import config

import requests
from time import time
from datetime import datetime, timedelta

# from traceback import print_exc

class SportsUnityScheduler:
	def __init__(self):
		# getting the time of the call to Scheduler
		self.present_time = int(round(time()))
		# getting the API url and databse collection from config file
		self.api_url = config.match_schedule_url
		self.coll = config.db_connection[config.database_name][config.collection_name]
		self.dates_coll = config.db_connection[config.database_name][config.collection_dates]


	def __get_api_response(self):
		'''
		  This method checks the status of the request returned and returns the response in json on success.
		'''
		try:
			# sending get request to the API and getting the response in json
			r = requests.get(self.api_url)
			# if request is successfull that is no HTTPError Occured
			if r.ok:
				response = r.json()
				# rechecking by the status of 'success' param
				if response['success']:
					return response
				else:
					# self.error_log.write('['+str(ctime())+'] ERROR : in main.get_api_response; Failed to get successful Results.\n')
					# print 'ERROR : main.__get_api_response; Failed to get successful Results.\n'
					return False
			else:
				# self.error_log.write('['+str(ctime())+'] ERROR : in TwitterFlash.get_api_response; Failed API request, status > "'+str(r.status_code)+'".\n')
				# print 'ERROR : main.__get_api_response; Failed API request, status > "'+str(r.status_code)+'".\n'
				return False
		except Exception, e:
			# self.error_log.write('['+str(ctime())+'] EXCEPTION : in TwitterFlash.get_api_response; '+str(e)+'.\n')
			# print 'EXCEPTION : main.__get_api_response; '+str(e)+'.\n'
			return False
		

	def __check_date_and_record_entry(self, epoch_time):
		# if the record is of match that has finished
		# i.e. epoch should be less than the present time
		if epoch_time < self.present_time:
			return False

		# if the record(s) with the epoch is already present 
		if epoch_time in self.all_epochs:
			return False

		return True

	def __get_formatted_date_and_time(self, epoch):
		return datetime.fromtimestamp(epoch).strftime('%d-%m-%Y'), datetime.fromtimestamp(epoch).strftime('%H:%M')


	def __get_football_schedule(self, match_list):
		try:
			games = []
			for match in match_list:
				if self.__check_date_and_record_entry(match['match_date_epoch']):
					params = {}
					# saving the parameters got from the api response
					params['epoch'] = match['match_date_epoch']
					params['sport'] = 'football'
					params['match_id'] = str(match['match_id'])
					params['series_id'] = str(match['league_id'])
					params['date'], params['time'] = self.__get_formatted_date_and_time(match['match_date_epoch'])
					params['series_name'] = match['league_name']
					params['home_team'] = match['home_team']
					params['away_team'] = match['away_team']

					# the parmas needed for scheduling the task 
					# state of the match 
					params['status'] = 'UNSCHEDULED'
					# flag to indicate whether match is assigned
					params['in_celery_queue'] = False
					# flag to check if match is set for twitter
					params['ready'] = False
					# hashtags for the match
					params['hashtags'] = ""
					games.append(params)
			return games
		except Exception, e:
			print str(e)
			return []


	def __get_cricket_schedule(self, match_list):
		try:
			games = []
			for match in match_list:
				# if match['match_time'] >= self.present_time:
				if self.__check_date_and_record_entry(match['match_time']):
					params = {}
					# saving the parameters got from the api response
					params['epoch'] = match['match_time']
					params['sport'] = 'cricket'
					params['match_id'] = match['match_id']
					params['series_id'] = match['series_id']
					params['date'], params['time'] = self.__get_formatted_date_and_time(match['match_time'])
					params['series_name'] = match['series_name']
					params['home_team'] = match['home_team']
					params['away_team'] = match['away_team']
					# the parmas needed for scheduling the task 
					# state of the match 
					params['status'] = 'UNSCHEDULED'
					# flag to indicate whether match is assigned
					params['in_celery_queue'] = False
					# flag to check if match is set for twitter
					params['ready'] = False
					# hashtags for the match
					params['hashtags'] = ""
					games.append(params)			
			return games
		except Exception, e:
			print str(e)
			return []


	def __remove_outdated_data(self):
		try:
			# remove the documents from databse which are
			# older than 12 hours from the present time
			ts  = int((datetime.now()-timedelta(hours=12)).strftime('%s'))
			self.coll.remove({'epoch': { '$lt' : ts }})
		except Exception as e:
			print str(e)


	def __construct_database(self, data):
		try:
			# get all the epoch timestamps of the documnets in the database
			self.all_epochs = set([x['epoch'] for x in list(self.coll.find({}, {'epoch':True, '_id':False}))])
			# ------- print self.all_epochs
			games = self.__get_football_schedule(data['football']) +  self.__get_cricket_schedule(data['cricket'])
			# ------- print len(games)
			# for game in games:
			# 	if game['sport']=='football':
			# 		print '>', game['date'], game['home_team'], 'vs', game['away_team'], ':', game['time']
			if games:
				self.coll.insert(games)
			# else:
			# 	print 'No New Update'
		except Exception as e:
			print str(e)
		

	def __update_latest_dates(self):
		# updating/creating the collection containing
		# latest epoch time for sport type parsed
		sport_types = ['cricket', 'football']
		for sp in sport_types:
			data = {}
			data.update({'sport':sp})
			# getting the latest match epoch for the sport
			data.update({'epoch':self.coll.find_one({'sport':sp}, sort=[("epoch", -1)])['epoch']})

			# updating the collection with sport type and latest match epoch
			# this collection serves as cache for the dates which has no matches
			# avaliable and are less than the latest epoch
			self.dates_coll.update({'sport':sp}, data, upsert=True)	


	def update_database(self):
		try:
			self.__remove_outdated_data()
			response = self.__get_api_response()
			self.__construct_database(response['data'])
			self.__update_latest_dates()
		except Exception, e:
			print str(e)

	
if __name__ == '__main__':
	obj = SportsUnityScheduler()
	obj.update_database()
