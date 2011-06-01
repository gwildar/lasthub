from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
from datetime import datetime
from django.utils import simplejson
import os
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
            lastfm = self._fetch_lastfm(lastfm_username)
            
            # date, time, offset = github[0]['created_at'].rsplit(' ')
            # datetime.strptime(date + ' ' + time, '%Y/%m/%d %H:%M:%S')
            

            # lastfm is using UTC we need to add an on the delta from github
            # lastfm['recenttracks']['track'][1]['date']
            # datetime.fromtimestamp(float(lastfm['recenttracks']['track'][1]['date']['uts']))
            
            # lastfm['recenttracks']['track'][1]['album']['#text'] => album name
            
            # find a track with 3 mins (before) a commit extend out until we find the last track that hour
            

            template_values = {'commits' : []}
            
            for git in github:
                date, time, offset = git['created_at'].rsplit(' ')
                a = datetime.strptime(date + ' ' + time, '%Y/%m/%d %H:%M:%S')
                for track in lastfm['recenttracks']['track'][1:]:
                    b = datetime.fromtimestamp(float(track['date']['uts']))
                    c = a - b
                    if c.seconds < 180 and c.days == 0:
                        git['track'] = track
                        git['album'] = track['album']['#text']
                        git['artist'] = track['artist']['#text']
                        if git['type'] == "PushEvent":
                            try:
                                git['comment'] = git['payload']['shas'][0][2]
                            except:
                                pass
                        template_values['commits'].append(git)
                        break
            pass
            
        else:
            template_values = {'missing_username' : True}
        path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
        self.response.out.write(template.render(path, template_values))

    def _fetch_github(self, username):
        """Fetch all the detials for a user in github."""

        url = "https://github.com/%s.json" % (username,)
        
        user_json = urlfetch.fetch(url, validate_certificate=False)
        
        if user_json.status_code == 200:
            return simplejson.loads(user_json.content)
            
    def _fetch_lastfm(self, username):
        """Fetch all the detials for a user in github."""

        url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%s&api_key=ADD_KEY!&format=json&limit=200" % (username,)
        
        user_json = urlfetch.fetch(url, validate_certificate=False)
        
        if user_json.status_code == 200:
            return simplejson.loads(user_json.content)
        
application = webapp.WSGIApplication(
                                     [('/', Index)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
