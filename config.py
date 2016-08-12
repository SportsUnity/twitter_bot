import pymongo
import os

# mongodb config variables
MONGO_HOST = None
MONGO_PORT = None
database_name = "twitterflash"
collection_name = "schedule"
collection_dates = "latest_dates"
collection_fixtures = "fixtures"

# defining connection to database
db_connection = pymongo.MongoClient(MONGO_HOST, MONGO_PORT, connect=False)

# api for getting present day match schedule
match_schedule_url = 'http://scoreslb-822670678.ap-northeast-2.elb.amazonaws.com/v1/get_all_matches_list'

# urls for APIs for all Sports, use format to replace params in {}
# cricket_url = "http://52.74.75.79:8080/v1/get_match_commentary?match_id={match_id}&season_key={series_id}"
cricket_url = "http://scoreslb-822670678.ap-northeast-2.elb.amazonaws.com/v1/get_match_commentary?match_id={match_id}&season_key={series_id}"
football_url = "http://scoreslb-822670678.ap-northeast-2.elb.amazonaws.com/get_football_commentary?match_id={match_id}"
basketball_url = ''
f1_url = ''
tennis_url = ''

# twitter app credentials
twitter_cons_key = '0448wNvDBQpBuUSUtYMspkxld'
twitter_cons_secret = 'QA0sKvyi3Qfg5J07GkYoWE7BbYW23LW8aRXbtKJZi2rggDnLxB'
twitter_access_token = '707458521462382594-nHgEfXOiSlgZmj6iuzTTIVAT6Pon7FJ'
twitter_access_token_secret = 'YuCQSoS6btI0YdCk9aTtK28YHox7WbNOFyxBQf9ta0Nnj'

# twitter test app credentials
# twitter_cons_key = 'DCgP6jqWaqnpXXDNHsusTz68t'
# twitter_cons_secret = 'WsN6DOc9rNsO3Fu4rc1DH511mxq5KOzh8kzJ4cEtZvHrUGTCwm'
# twitter_access_token = '208713780-3czsVI3ZJV0BkxtJfk2eOjK6AUMDeVnfbZSmlOyG'
# twitter_access_token_secret = 'cikeVIINYC8z1CZAohQiykXsin4VtTkhuyduEiC63yuMj'


# log files
logs_dir = os.getcwd()+'/logs'
std_err_log_file = logs_dir+'/'+'twitterflash_std_logs.log'


# time interval to run tasks (in seconds)
time_interval = 10

# exit count variable; i.e. till when
# the program waits for new update
# here it is set to 40 minutes; 
terminate_task_at = (40*60)/time_interval


