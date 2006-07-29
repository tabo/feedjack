# -*- coding: utf-8 -*-

"""
feedjack
Gustavo Picón
urls.py
"""

from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^rss20.xml$', 'django.views.generic.simple.redirect_to',
        {'url':'/feed/rss/'}),
    (r'^feed/$', 'django.views.generic.simple.redirect_to',
        {'url':'/feed/rss/'}),
    (r'^feed/rss/$', 'feedjack.views.rssfeed'),
    (r'^feed/atom/$', 'feedjack.views.atomfeed'),
    (r'^feed/user/(?P<user>.*)/tag/(?P<tag>.*)/$', 'feedjack.views.buildfeed'),
    (r'^feed/user/(?P<user>.*)/$', 'feedjack.views.buildfeed'),
    (r'^feed/tag/(?P<tag>.*)/$', 'feedjack.views.buildfeed'),
    (r'^user/(?P<user>.*)/tag/(?P<tag>.*)/$', 'feedjack.views.mainview'),
    (r'^user/(?P<user>.*)/$', 'feedjack.views.mainview'),
    (r'^tag/(?P<tag>.*)/$', 'feedjack.views.mainview'),
    (r'^opml/$', 'feedjack.views.opml'),
    (r'^foaf/$', 'feedjack.views.foaf'),
    (r'^$', 'feedjack.views.mainview'),
)
