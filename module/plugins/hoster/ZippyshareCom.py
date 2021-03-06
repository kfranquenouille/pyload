# -*- coding: utf-8 -*-

import re
import urllib

import BeautifulSoup

from module.plugins.captcha.ReCaptcha import ReCaptcha
from module.plugins.internal.SimpleHoster import SimpleHoster


class ZippyshareCom(SimpleHoster):
    __name__    = "ZippyshareCom"
    __type__    = "hoster"
    __version__ = "0.90"
    __status__  = "testing"

    __pattern__ = r'http://www\d{0,3}\.zippyshare\.com/v(/|iew\.jsp.*key=)(?P<KEY>[\w^_]+)'
    __config__  = [("activated"   , "bool", "Activated"                                        , True),
                   ("use_premium" , "bool", "Use premium account if available"                 , True),
                   ("fallback"    , "bool", "Fallback to free download if premium fails"       , True),
                   ("chk_filesize", "bool", "Check file size"                                  , True),
                   ("max_wait"    , "int" , "Reconnect if waiting time is greater than minutes", 10  )]

    __description__ = """Zippyshare.com hoster plugin"""
    __license__     = "GPLv3"
    __authors__     = [("Walter Purcaro", "vuolter@gmail.com"         ),
                       ("sebdelsol"     , "seb.morin@gmail.com"       ),
                       ("GammaC0de"     , "nitzo2001[AT]yahoo[DOT]com")]

    COOKIES = [("zippyshare.com", "ziplocale", "en")]

    NAME_PATTERN         = r'(<title>Zippyshare.com - |"/)(?P<N>[^/]+)(</title>|";)'
    SIZE_PATTERN         = r'>Size:.+?">(?P<S>[\d.,]+) (?P<U>[\w^_]+)'
    OFFLINE_PATTERN      = r'does not exist (anymore )?on this server<'
    TEMP_OFFLINE_PATTERN = None

    LINK_PREMIUM_PATTERN = r"document.location = '(.+?)'"


    def setup(self):
        self.chunk_limit     = -1
        self.multiDL         = True
        self.resume_download = True


    def handle_free(self, pyfile):
        self.captcha   = ReCaptcha(pyfile)
        captcha_key = self.captcha.detect_key()

        if captcha_key:
            try:
                self.link = re.search(self.LINK_PREMIUM_PATTERN, self.data)
                self.captcha.challenge()

            except Exception, e:
                self.error(e)

        else:
            self.link = self.fixurl(self.get_link())

        if self.link and pyfile.name == "file.html":
            pyfile.name = urllib.unquote(self.link.split('/')[-1])


    def get_link(self):
        #: Get all the scripts inside the html body
        soup = BeautifulSoup.BeautifulSoup(self.data)
        scripts = [s.getText() for s in soup.body.findAll('script', type='text/javascript') if "('dlbutton').href =" in s.getText()]

        #: Emulate a document in JS
        inits = ['''
                var document = {}
                document.getElementById = function(x) {
                    if (!this.hasOwnProperty(x)) {
                        this[x] = {getAttribute : function(x) { return this[x] } }
                    }
                    return this[x]
                }
                ''']

        #: inits is meant to be populated with the initialization of all the DOM elements found in the scripts
        eltRE = r'getElementById\([\'"](.+?)[\'"]\)(\.)?(getAttribute\([\'"])?(\w+)?([\'"]\))?'
        for m in re.findall(eltRE, ' '.join(scripts)):
            JSid, JSattr = m[0], m[3]
            values = filter(None, (elt.get(JSattr, None) for elt in soup.findAll(id=JSid)))
            if values:
                inits.append('document.getElementById("%s")["%s"] = "%s"' %(JSid, JSattr, values[-1]))

        #: Add try/catch in JS to handle deliberate errors
        scripts = ['\n'.join(('try{', script, '} catch(err){}')) for script in scripts]

        #: Get the file's url by evaluating all the scripts
        scripts = inits + scripts + ['document.dlbutton.href']

        return self.js.eval('\n'.join(scripts))
