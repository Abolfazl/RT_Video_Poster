import requests
from bs4 import BeautifulSoup
import sqlite3
import sys
import traceback
import praw
import time
from pushbullet import Pushbullet
import warnings
warnings.simplefilter("ignore")

'''User Config'''
APP_ID = ''
APP_SECRET = ''
APP_URI = ''
APP_REFRESH = ''
USERAGENT = ''
URL = "http://roosterteeth.com/episode/recently-added"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36', 'Connection': 'close'} 

'''DB Config'''
sql = sqlite3.connect('RT.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
cur = sql.cursor()

'''PushBullet'''
def pushMsg(title, body):
    apiKey = ""
    p = Pushbullet(apiKey)
    sony = p.devices[0]
    try:
        sony.push_note(title, body)
    except Exception as e:
        traceback.print_exc()
        pass

'''Reddit Post'''
def RedditPost(TITLE, URL, TIME):
    try:
        r = praw.Reddit(USERAGENT)
        r.set_oauth_app_info(APP_ID, APP_SECRET, APP_URI)
        r.refresh_access_information(APP_REFRESH)
        pos = TITLE.lower().find("let's play: ")
        if pos != -1:
            TITLE = TITLE[pos+len("let's play: "):]
        TITLE_FORMATTED = "[FIRST] %s - [%s]" % (TITLE, TIME)
        newpost = r.submit(subreddit='roosterteeth', title=TITLE_FORMATTED, url=URL, captcha=None, resubmit=False, send_replies=True)
        print("%s: '%s', ID '%s'" % (time.strftime("%Y-%m-%d %H:%M"), TITLE, newpost.id))
        pushMsg("RT: %s" % TITLE, newpost.permalink)
        return newpost.id, TITLE
    except praw.errors.AlreadySubmitted as e:
        print("AlreadySubmitted", TITLE, URL)
        return "AlreadySubmitted", TITLE
    except Exception as e:
        print("RedditPost", e)
        traceback.print_exc()

response = requests.get(URL, headers=headers)
html_source = response.text
html_source = html_source.encode('utf-8', 'ignore')
soup = BeautifulSoup(html_source, 'html.parser')
episodes = soup.findAll('li')
for episode in episodes:
    try:
        # Skip the recently-added url
        if str(episode).find('recently-added') != -1:
            continue

        # Skip non-First URLs (no mention of 'ion-star')
        if str(episode).find('ion-star') == -1:
            continue

        # Skip an episode if it does not contain class="name"
        if str(episode).find('class="name"') == -1:
            continue

        # Find URL
        video_page_url = episode.a['href']
        if "/episode/" not in video_page_url:
            continue
        
        # Get Title
        info = episode.find_all('p')
        if (not info) and ('"name"' not in str(info[1])):
            continue
        title = (info[1].text.encode('ascii', 'ignore')).decode()
        time_length = info[0].text.strip()
        
        cur.execute("SELECT COUNT(*) FROM RT WHERE URL = ?", (video_page_url,))
        count = int(cur.fetchone()[0])
        if count == 0:
            pid, newtitle = RedditPost(title, video_page_url, time_length)
            cur.execute("INSERT INTO RT VALUES (?, ?, ?)", (newtitle, video_page_url, pid))
            sql.commit()
            #print("DB: '%s' with ID %s" % (title, pid)) 
    except Exception as e:
        print("Main:", e)
        traceback.print_exc()
        pass
sql.close()
#response.connection.close()