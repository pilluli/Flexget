import urllib, urllib2, logging, re
from flexget.plugins.plugin_urlrewriting import UrlRewritingError
from flexget import plugin
from flexget.utils.soup import get_soup
from flexget.event import event

log = logging.getLogger('resurrectthenet')

class UrlRewriteResurrectTheNet(object):
    """LeechersLair UrlRewrite."""

    # resolver API
    def url_rewritable(self, feed, entry):
        if entry['url'].startswith('http://resurrectthe.net/index.php?page=downloadcheck'):
            return True
        return False
        
    # resolver API
    def url_rewrite(self, feed, entry):
        # parse page 
        page = urllib2.urlopen(entry['url'])
        try:
            soup = get_soup(page)
            tag_div = soup.find_all('a')
            for l in tag_div:
                try:
                    torrent_url = l['href']
                    if torrent_url.startswith('download.php'):
                        entry['url'] = 'http://resurrectthe.net/' + torrent_url
                except:
                    pass
        except Exception, e:
            raise UrlRewritingError(e)

            
@event('plugin.register')
def register_plugin():
    plugin.register(UrlRewriteResurrectTheNet, 'resurrectthenet', groups=['urlrewriter'], api_ver=2)
