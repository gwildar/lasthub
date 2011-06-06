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
            
            for commit in github:
                track = self._fetch_lastfm(lastfm_username, commit['commit_time'])
                if track:
                    commit['track'] = track
                    commit['album'] = track['album']['#text']
                    commit['artist'] = track['artist']['#text']

                    template_values['commits'].append(commit)
            
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
        
        if not user_json.status_code == 200:
            return
        
        user_events = simplejson.loads(user_json.content)            
        
        commits = []
        
        for event in user_events:
            if event['type'] == 'PushEvent':
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
