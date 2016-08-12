import tweepy
import requests
import pymongo

import config

from datetime import datetime
from time import sleep, time, ctime
from random import randint

from celery import current_task
from celery.task.control import revoke

# import requests.packages.urllib3
# requests.packages.urllib3.disable_warnings()

import os

# from random import randint

def terminate_the_task(sport_type, series_id, match_id):
	# change status of this match to FINISHED
	coll_schedule = config.db_connection[config.database_name][config.collection_name]
	doc = coll_schedule.find_one({'sport':sport_type, 'series_id':series_id, 'match_id':match_id})
	coll_schedule.update_one({'sport':sport_type, 'series_id':series_id, 'match_id':match_id}, {"$set":{"status": "FINISHED"}})

	# TERMINATE THE TASK FROM CELERY QUEUE
	task_id = current_task.request.id
	revoke(task_id, terminate=True)
	

class TwitterFlash:
	'''
		Creates tweets of commentry for sports.
	'''
	def __init__(self):
		self.set_log_files()
		self.set_twitter_creds()
		self.count_to_exit = 0


	def set_log_files(self):
		'''
			This method sets log files for the process.
		'''
		if not os.path.exists(config.logs_dir):
			os.makedirs(config.logs_dir)

		self.error_log = open(config.std_err_log_file, 'a')
		self.error_log.write('\n-------------------------------------------------\nTimestamp : '+str(ctime())+'\n\n')
		self.tweet_log_file = config.logs_dir+'/failed_tweets_logs_'+str(datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S'))+'.log'

		
	def set_twitter_creds(self):
		'''
		  This method sets the tweepy auth api, with the credentials passed.
		'''
		# credentials for twitter application
		self.cons_key = config.twitter_cons_key
		self.cons_secret = config.twitter_cons_secret
		self.access_token = config.twitter_access_token
		self.access_token_secret = config.twitter_access_token_secret
		self.auth = tweepy.OAuthHandler(self.cons_key, self.cons_secret)
		self.auth.set_access_token(self.access_token, self.access_token_secret)
		self.api = tweepy.API(self.auth)


	def set_game_params(self, sport_type, series_id, match_id, hashtags=''):
		self.sport_type = sport_type
		self.series_id = series_id
		self.match_id = match_id
		# setting the api url based on sport type
		self.api_url = self.get_api_url()
		# setting the hashtags
		self.hashtags = hashtags
		# set the commentary for sport type
		self.last_check_tag = 'time' if (sport_type == 'football') else 'commentary_id'
		self.last_check_val = 0


	def run(self):
		'''
			Start the TwitterFlash process with this function.
		'''

		# if count_to_exit becomes config.terminate_task_at, exit the program this is because of not 
		# recieving any update from the api for specific time (40 mins approx), 
		# assuming match has completed and there are no comments furthur.
		if self.count_to_exit == config.terminate_task_at:
			self.error_log.write('['+str(ctime())+'] INFO :'+' EXIT count completed.\n')
			self.error_log.close()
			terminate_the_task(self.sport_type, self.series_id, self.match_id)

		comments_list = self.get_latest_comments()

		# update count_to_exit if no commentry is found
		if not comments_list:
			self.count_to_exit += 1 
			return

		# reset count_to_exit to 0, since data is received from api
		self.count_to_exit = 0

		for comment in comments_list:
			# getting list of tweet from the comment with each tweet not
			# exceeding the character limit
			list_of_tweets = self.filter_commentry_by_char_limit(comment)

			for i, tweet in enumerate(list_of_tweets):
				try:
					tweet_num = ''
					if len(list_of_tweets) > 1:
						tweet_num = '('+str(i+1)+'/'+str(len(list_of_tweets))+') '

					# creating tweet with comment plus hashtags
					tweet_to_post = tweet_num+tweet+' '+self.hashtags

					# print tweet_to_post
					# posting the tweet and getting back the status
					# and storing the state into logfile
					status = self.post_tweet(tweet_to_post)

					# if tweet is unsuccessfull then open the failed tweets logs
					# and write the unsuccessfull tweet into the log file
					if not status:
					    f = open(self.tweet_log_file, 'a')
					    f.write('['+str(ctime())+'] '+tweet_to_post+'\n')       
					    f.close()
				except Exception, e:
					self.error_log.write('['+str(ctime())+'] EXCEPTION in {} : in TwitterFlash.run; {}\n '.format(tweet_to_post, str(e)))


	def get_api_url(self):
		'''
		  This method returns back the URL based on the category (sport type) passed.
		'''

		if self.sport_type == 'cricket':
		 	return config.cricket_url.format(match_id=self.match_id, series_id=self.series_id)

		if self.sport_type == 'football':
		 	return config.football_url.format(match_id=self.match_id)

	
	def get_latest_comments(self):
	    '''
	      Get the latest comments from the API.
	    '''
	    try:
	        # construct the api url including the timestamp param with the value
	        # of last recorded timestamp tag value
	        api_url = self.api_url+'&time_stamp='+str(self.last_check_val)+'&direction=up'
	        # print api_url
	        comments_list = []
	        r = requests.get(api_url)
	        if r.ok:
	        	# getting the response and fetching tweets from the 
	        	# response returned
	            response = r.json()
	            if response['data']:
	                for commentry in reversed(response['data']):
	                    comments_list.append(commentry['comment'])

	                # saving the value of the last tag from the topmost commentry
	                self.last_check_val = response['data'][0][self.last_check_tag]
	        return comments_list
	    except Exception, e:
	        self.error_log.write('['+str(ctime())+'] EXCEPTION : in TwitterFlash.get_latest_comments; '+str(e)+'.\n')
	        return []
	        # print 'EXCEPTION : in TwitterFlash.get_latest_commentry; '+str(e)+'.\n'


	def filter_commentry_by_char_limit(self, content, limit=100):
		'''
			This method returns list of tweets seperated by the limit specified (default:100).
		'''

		limit -= 1 # decrementing it by 1 since index starts from 0
		comments_list = []
		try:
			while True:
				# get the word nearest to the character limit
				offset = content[limit:].find(' ')
				if offset == -1:
					comments_list.append(content) # entire tweet is within limit
					break
				else:
					tweet = content[:limit+offset]
					offset += limit+1
					# get position of '(' and ')' from end of tweet
					a = tweet.rfind('(')
					b = tweet.rfind(')')

					# if '(' is present 
					if a != -1: 
						# if ')' is not present or if it appears before '(', then limit tweet before '('
						if b == '-1' or b < a: 
							tweet = content[:a]
							offset = a
					# save tweet in the list
					comments_list.append(tweet)
					# update the content with remaining words
					content = content[offset:]
			return comments_list
		except Exception, e:
			self.error_log.write('['+str(ctime())+'] EXCEPTION : in TwitterFlash.filter_commentry_by_word_limit; '+str(e)+'.\n')
			return False


	def post_tweet(self, tweet):
		'''
		  This method will post the tweet on the feed of the account associated with the credentials provided for twitter app.
		'''
		try:
			self.api.update_status(tweet)
			return True
		except Exception, e:
			self.error_log.write('['+str(ctime())+'] EXCEPTION : in TwitterFlash.post_tweet; '+str(e)+'.\n')
			# print 'Tweet Failed'
			# print 'Error :', str(e)
			return False

