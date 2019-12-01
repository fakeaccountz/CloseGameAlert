import requests
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
import os.path
from email.mime.text import MIMEText
import base64
import smtplib, ssl


def get_teams_info(teams):
    ret = [0,0]
    team_0_name_s = teams[0]['name'].split(' ')
    team_0_name = team_0_name_s[len(team_0_name_s)-1]
    team_1_name_s = teams[1]['name'].split(' ')
    team_1_name = team_1_name_s[len(team_1_name_s)-1]
    if teams[0]['is_home']:
        ret[0] = team_0_name
        ret[1] = team_1_name
    else:
        ret[0] = team_1_name
        ret[1] = team_0_name
    return ret

def create_message(game):
  r = get_teams_info(game['teams'])
  message_text = 'Score: \n' + str(game['score']['score_home']) + ' ' + r[0] + '\n' + str(game['score']['score_away']) + ' ' + r[1] + '\n4th Quarter time left: ' + game['score']['display_clock']
  message = MIMEText(message_text)
  message['to'] = os.environ['receiver_email'].replace('\xc2\xa0', ' ')
  message['from'] = os.environ['sender_email']
  message['subject'] = "Omid's Close Game Alert"
  return message.as_string()


def send_alerts(msg):
    sender_email = os.environ['sender_email']
    receiver_email = os.environ['receiver_email'].replace('\xc2\xa0', ' ').split(', ')
    
    port = 465
    smtp_server = "smtp.gmail.com"
    password = os.environ['gmail_key']

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg)

def eval_single_game(game, already_ran=False):
    game_eventid = game['event_id']
    updated_game = get_today_games(game_eventid)
    updated_game_score_obj = updated_game['score']
    print(updated_game_score_obj)
    print('\n')
    is_fourth_q = (True if updated_game_score_obj['game_period'] == 4 else False)
    desired_mins_left = 6
    clock_time = updated_game_score_obj['display_clock']
    if '.' in clock_time:
        actual_mins_left = int(clock_time.split('.')[0])
    else:
        actual_mins_left = int(clock_time.split(':')[0])
    print('actual mins left: ' + str(actual_mins_left))
    is_in_desired_mins_left = (True if actual_mins_left <= desired_mins_left else False)
    if is_fourth_q and is_in_desired_mins_left:
        point_differential = abs(updated_game_score_obj['score_home'] - updated_game_score_obj['score_away'])
        print('point diff: ' + str(point_differential))
        desired_point_diff = 8
        if point_differential <= desired_point_diff:
            msg = create_message(updated_game)
            send_alerts(msg)
            print("Alert sent.")
    else:
        if already_ran:
            return
        if is_fourth_q:
            mins_to_schedule_from_now = (actual_mins_left - desired_mins_left) * 2
        else:
            mins_to_schedule_from_now = (((actual_mins_left+12) - desired_mins_left) * 2) + 5
        mins_to_schedule_from_now_datetime = datetime.now() + timedelta(minutes=mins_to_schedule_from_now)
        print('scheduled a re-check')
        scheduler.add_job(eval_single_game, 'date',run_date=mins_to_schedule_from_now_datetime, args=[updated_game, True])


def get_today_games(single_game_id = None):
    
    querystring = {"include":["scores"],"offset":"480"}
    headers = {
        'x-rapidapi-host': "therundown-therundown-v1.p.rapidapi.com",
        'x-rapidapi-key': os.environ['rapidapi_key']
        }
 
    if single_game_id:
        url = "https://therundown-therundown-v1.p.rapidapi.com/events/" + single_game_id
        return requests.request("GET", url, headers=headers, params=querystring).json()
    else:
        d = datetime.today().strftime('%Y-%m-%d')
        url = "https://therundown-therundown-v1.p.rapidapi.com/sports/4/events/" + d
        response_json = requests.request("GET", url, headers=headers, params=querystring).json()
        return response_json['events']


def close_game():
    all_games = get_today_games() 
    for game in all_games:
        game_time = game['event_date'] # for example 2019-11-23T22:05:00Z
        print('game time: ' + game_time)
        game_time_datetime = datetime.strptime(game_time, "%Y-%m-%dT%H:%M:%S%z")
        almost_end_of_game_time = (game_time_datetime + timedelta(hours=2, minutes=10)).astimezone(tz=None)
        print(almost_end_of_game_time)
        scheduler.add_job(eval_single_game, 'date',run_date=almost_end_of_game_time, args=[game])
    
    scheduler.start()



scheduler = BlockingScheduler()
if __name__ == '__main__':
    close_game()


