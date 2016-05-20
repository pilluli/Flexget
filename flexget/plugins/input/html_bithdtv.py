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

log = logging.getLogger('html_bithdtv')


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

    @cached('html_bithdtv')
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
        opener.addheaders.append(('Cookie', 'h_su=MTA4OTQx; h_sp=1fb9b4477d6f27d54ba760303eeb667e; h_sl=YmxhYw%3D%3D; punbb_cookie=a%3A2%3A%7Bi%3A0%3Bs%3A5%3A%2257827%22%3Bi%3A1%3Bs%3A32%3A%22de67f567ed4f0abac31237469fc7336e%22%3B%7D'))
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

    def _title_from_link(self, link, log_link):
        title = link.text
        # longshot from next element (?)
        if not title:
            title = link.next.string
            if title is None:
                log.debug('longshot failed for %s' % log_link)
                return None
        return title or None

    def _title_from_url(self, url):
        parts = urllib.splitquery(url[url.rfind('/') + 1:])
        title = urllib.unquote_plus(parts[0])
        return title

    def create_entries(self, page_url, soup, config):

        queue = []
        duplicates = {}
        duplicate_limit = 4

        def title_exists(title):
            """Helper method. Return True if title is already added to entries"""
            for entry in queue:
                if entry['title'] == title:
                    return True

        stable = soup.find('table',{'width':750,'cellspacing':'0', 'cellpadding':5, 'border':0})
        i = 0
        for row in stable.find_all('tr'):
            # Skip the first one
            if i > 0:
                url = row.find('a')['href']
                title = row.find('td',{'class':'detail','align':'left'}).find('a')['title'].encode('utf-8')

                # truly duplicate, title + url crc already exists in queue
                if title_exists(title):
                    continue            

                entry = Entry()
                entry['url'] = url
                entry['title'] = title

                queue.append(entry)

            i = i+1


        # add from queue to task
        return queue


@event('plugin.register')
def register_plugin():
    plugin.register(InputHtml, 'html_bithdtv', api_ver=2)

