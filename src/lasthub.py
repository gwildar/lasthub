from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
from datetime import datetime, timedelta
from django.utils import simplejson
from django.utils.datastructures import SortedDict
import os, time
from google.appengine.ext.webapp import template

class Index(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
        self.response.out.write(template.render(path, {}))
        
    def post(self):
        """Handle data posted from main form"""
        
        lastfm_username = self.request.get('lastfm')
        github_username = self.request.get('github')
        
        if lastfm_username and github_username:
            github = self._fetch_github(github_username)
            
            template_values = {'commits' : []}
            
            for commit in github:
                track = self._fetch_lastfm(lastfm_username, commit['commit_time'])
                if track:
                    commit['track'] = track
                    commit['album'] = track['album']['#text']
                    commit['artist'] = track['artist']['#text']

                    template_values['commits'].append(commit)
            
            if not template_values['commits']:
                template_values['noresults'] = True

        else:
            template_values = {'missing_username' : True}
        path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
        self.response.out.write(template.render(path, template_values))
      
    def _fetch_github(self, username):
        """Fetch all the detials for a user in github."""

        url = "https://github.com/%s.json" % (username,)
        
        user_json = urlfetch.fetch(url, validate_certificate=False)
        
        if not user_json.status_code == 200:
            return
        
        user_events = simplejson.loads(user_json.content)            
        
        commits = []
        
        for event in user_events:
            if event['type'] == 'PushEvent' and event.has_key('repository'):
                url = "https://github.com/api/v2/json/commits/show/%s/%s/%s" % (event['repository']['owner'], event['repository']['name'], event['payload']['shas'][0][0])
            
                commit_json = urlfetch.fetch(url, validate_certificate=False)
        
                if commit_json.status_code == 200:
                    commit = simplejson.loads(commit_json.content)
                
                    # build dict for use later
                    date_time, offset = commit['commit']['committed_date'].rsplit('-', 1)
                    start_time = datetime.strptime(date_time, '%Y-%m-%dT%H:%M:%S')
                    commit['commit_time'] = start_time + timedelta(hours=int(offset.split(':')[0]))
                    commit['repo'] = event['repository']['name']
                    commits.append(commit)
        
        return commits

    
    def _fetch_lastfm(self, username, commit_time):
        """Fetch all the detials for a user in github."""

        offset = timedelta(minutes=10)
        start = str(int(time.mktime(commit_time.timetuple())))
        end_time = commit_time + offset
        end = str(int(time.mktime(end_time.timetuple())))
        
        url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%s&api_key=ADD_KEY!&format=json&limit=200&from=%s&to=%s" % (username, start, end)
        
        user_json = urlfetch.fetch(url, validate_certificate=False)
        
        if user_json.status_code == 200:
            json = simplejson.loads(user_json.content)
            try:
                return json['recenttracks']['track'][0]
            except:
                return
    
application = webapp.WSGIApplication(
                                     [('/', Index)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
