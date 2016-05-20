from __future__ import unicode_literals, division, absolute_import
import urlparse
import logging
import urllib
import zlib
import re

from flexget import plugin
from flexget.event import event
from flexget.entry import Entry
from flexget.utils.soup import get_soup
from flexget.utils.cached_input import cached

log = logging.getLogger('html_resurrectthenet')


class InputHtml(object):
    """
        Parses urls from html page. Usefull on sites which have direct download
        links of any type (mp3, jpg, torrent, ...).

        Many anime-fansubbers do not provide RSS-feed, this works well in many cases.

        Configuration expects url parameter.

        Note: This returns ALL links on url so you need to configure filters
        to match only to desired content.
    """

    def validator(self):
        from flexget import validator
        root = validator.factory()
        root.accept('text')
        advanced = root.accept('dict')
        advanced.accept('url', key='url', required=True)
        advanced.accept('text', key='username')
        advanced.accept('text', key='password')
        advanced.accept('text', key='dump')
        advanced.accept('text', key='title_from')
        regexps = advanced.accept('list', key='links_re')
        regexps.accept('regexp')
        return root

    def build_config(self, config):

        def get_auth_from_url():
            """Moves basic authentication from url to username and password fields"""
            parts = list(urlparse.urlsplit(config['url']))
            split = parts[1].split('@')
            if len(split) > 1:
                auth = split[0].split(':')
                if len(auth) == 2:
                    config['username'], config['password'] = auth[0], auth[1]
                else:
                    log.warning('Invalid basic authentication in url: %s' % config['url'])
                parts[1] = split[1]
                config['url'] = urlparse.urlunsplit(parts)

        if isinstance(config, basestring):
            config = {'url': config}
        get_auth_from_url()
        return config

    @cached('html_resurrectthenet')
    @plugin.internet(log)
    def on_task_input(self, task, config):
        config = self.build_config(config)

        log.debug('InputPlugin html requesting url %s' % config['url'])

        auth = None
        if config.get('username') and config.get('password'):
            log.debug('Basic auth enabled. User: %s Password: %s' % (config['username'], config['password']))
            auth = (config['username'], config['password'])

        import urllib2
        opener = urllib2.build_opener()
        opener.addheaders.append(('Cookie', 'uid=3112;pass=ca930f5b3e747eb582e71209b380d297;xbtitFM=b8hjitrkjjl985e7i9u3jsv6k1'))
        f = opener.open(config['url'])
        page = f.read()
        soup = get_soup(page)

        #page = task.requests.get(config['url'], auth=auth)
        #soup = get_soup(page.text)

        # dump received content into a file
        if 'dump' in config:
            name = config['dump']
            log.info('Dumping %s into %s' % (config['url'], name))
            data = page
            f = open(name, 'w')
            f.write(data)
            f.close()

        return self.create_entries(config['url'], soup, config)

    def create_entries(self, page_url, soup, config):

        queue = []
        duplicates = {}
        duplicate_limit = 4

        def title_exists(title):
            """Helper method. Return True if title is already added to entries"""
            for entry in queue:
                if entry['title'] == title:
                    return True

        stable_all = soup.find_all('table',{'class':'lista','width':'100%'})
        stable = stable_all[0]

        title = ''
        for row in stable.find_all('td'):
            try:
                if row['class'][0]=='lista':
                    try:
                        if row['valign'] == 'middle':
                            al = row.find('a')
                            title = al.string.encode('utf-8')
                    except:
                        pass
                    try:
                        if row['width'] == '20':
                            al = row.find('a')
                            url = al['href']
                            entry = Entry()
                            entry['url'] = 'http://resurrectthe.net/' + url
                            entry['title'] = title
                            queue.append(entry)
                    except:
                        pass
            except:
                pass


        # add from queue to task
        return queue


@event('plugin.register')
def register_plugin():
    plugin.register(InputHtml, 'html_resurrectthenet', api_ver=2)

