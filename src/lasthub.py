from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
from datetime import datetime
from django.utils import simplejson
import os, time
from google.appengine.ext.webapp import template

class Index(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
        self.response.out.write(template.render(path, {}))
        
    def post(self):
        
        
        lastfm_username = self.request.get('lastfm')
        github_username = self.request.get('github')
        
        if lastfm_username and github_username:
            github = self._fetch_github(github_username)
            
            
            # date, time, offset = github[0]['created_at'].rsplit(' ')
            # datetime.strptime(date + ' ' + time, '%Y/%m/%d %H:%M:%S')
            

            # lastfm is using UTC we need to add an on the delta from github
            # lastfm['recenttracks']['track'][1]['date']
            # datetime.fromtimestamp(float(lastfm['recenttracks']['track'][1]['date']['uts']))
            
            # lastfm['recenttracks']['track'][1]['album']['#text'] => album name
            
            # find a track with 3 mins (before) a commit extend out until we find the last track that hour
            

            template_values = {'commits' : []}
            
            date, time, offset = github[-1]['created_at'].rsplit(' ')
            start_time = datetime.strptime(date + ' ' + time, '%Y/%m/%d %H:%M:%S')
            
            date, time, offset = github[1]['created_at'].rsplit(' ')
            end_time = datetime.strptime(date + ' ' + time, '%Y/%m/%d %H:%M:%S')
            

            lastfm = self._fetch_lastfm(lastfm_username, start_time, end_time)
            
            for git in github:
                date, time, offset = git['created_at'].rsplit(' ')
                a = datetime.strptime(date + ' ' + time, '%Y/%m/%d %H:%M:%S')
                git['created_at'] = a
                for track in lastfm['recenttracks']['track'][1:]:
                    b = datetime.fromtimestamp(float(track['date']['uts']))
                    c = a - b
                    if c.seconds < 240 and c.days == 0:
                        git['track'] = track
                        git['album'] = track['album']['#text']
                        git['artist'] = track['artist']['#text']
                        try:
                            #git['comment'] = git['payload']['shas'][0][2]
                            git['comment'] = self._set_title_body(git)
                        except:
                            pass
                        template_values['commits'].append(git)
                        break
            
        else:
            template_values = {'missing_username' : True}
        path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
        self.response.out.write(template.render(path, template_values))

    def _set_title_body(self, github):
        """create a meaning string from the github action
        """

        if github['type'] == 'CreateEvent':
            if github['payload'].has_key('object_name'):
                title = "Created branch %s from %s" % (github['payload']['object_name'], github['payload']['name'])
            else:
                title = "Created new branch called %s for %s" % (github['payload']['ref'], github['repository']['name'],)
        elif github['type'] == 'GistEvent':
            title = "Created gist %s" % (github['payload']['desc'])
        elif github['type'] == 'IssuesEvent':
            title = "Issue #%s was %s" % (str(github['payload']['number']), github['payload']['action'])
        elif github['type'] == 'ForkEvent':
            title = "Repo %s forked." % (github['payload']['repo'])
        elif github['type'] == 'PushEvent':
            title = "Pushed to repo %s with comment %s." % (github['payload']['repo'], github['payload']['shas'][0][2])
        elif github['type'] == 'CreateEvent':
            title = "Branch %s for %s" % (github['payload']['object_name'], github['payload']['name'])
        elif github['type'] == 'WatchEvent':
            title = "Started watching %s." % (github['payload']['repo'])
        elif github['type'] == 'FollowEvent':
            title = "Started following %s." % (github['payload']['target']['login'])
        elif github['type'] == 'GistEvent':
            title = "Snippet: %s" % (github['payload']['snippet'])
        elif github['type'] == 'DeleteEvent':
            title = "Deleted: %s called %s" % (github['payload']['ref_type'], github['payload']['ref'])
        elif github['type'] == 'GollumEvent':
            pass
        elif github['type'] == 'IssueCommentEvent':
            title = "Commented on issue with id of %s" % (github['payload']['issue_id'])

        return title
        
    def _fetch_github(self, username):
        """Fetch all the detials for a user in github."""

        url = "https://github.com/%s.json" % (username,)
        
        user_json = urlfetch.fetch(url, validate_certificate=False)
        
        if user_json.status_code == 200:
            return simplejson.loads(user_json.content)
            
    def _fetch_lastfm(self, username, start_time, end_time):
        """Fetch all the detials for a user in github."""

        start = str(int(time.mktime(start_time.timetuple())))
        end = str(int(time.mktime(end_time.timetuple())))
        
        url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%s&api_key=09f1c061fc65a7bc08fb3ad95222d16e&format=json&limit=200&from=%s&to=%s" % (username, start, end)
        
        user_json = urlfetch.fetch(url, validate_certificate=False)
        
        if user_json.status_code == 200:
            json = simplejson.loads(user_json.content)
            try:
                if json['recenttracks']['@attr']['totalPages'] > str(1):
                    for i in range(2,4):
                        url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%s&api_key=ADD_KEY!&format=json&limit=200&from=%s&to=%s&page=%s" % (username, start, end, i)
                        user_json = urlfetch.fetch(url, validate_certificate=False)
                        tmp_json = simplejson.loads(user_json.content)
                        json['recenttracks']['track'] = json['recenttracks']['track'] + tmp_json['recenttracks']['track']
            except:
                pass
        return json
application = webapp.WSGIApplication(
                                     [('/', Index)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
