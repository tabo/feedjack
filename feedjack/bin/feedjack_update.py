#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
feedjack
Gustavo Picón
update_feeds.py
"""

import os
import time
import optparse
import datetime
import socket
import traceback
import sys

import feedparser

from feedjack import models, fjcache

VERSION = '0.9.8a1'
URL = 'http://www.feedjack.org/'
USER_AGENT = 'Feedjack %s - %s' % (VERSION, URL)

def encode(tstr):
    """ Encodes a unicode string in utf-8
    """
    if not tstr:
        return ''
    return tstr.encode('utf-8', "xmlcharrefreplace")

def mtime(ttime):
    """ datetime auxiliar function.
    """
    return datetime.datetime.fromtimestamp(time.mktime(ttime))

def get_tags(entry, tagdict):
    """ Returns a list of tag objects from an entry.
    """
    fcat = []
    if entry.has_key('tags'):
        for tcat in entry.tags:
            qcat = encode(tcat[1]).strip()
            if ',' in qcat or '/' in qcat:
                qcat = qcat.replace(',', '/').split('/')
            else:
                qcat = [qcat]
            for zcat in qcat:
                tagname = zcat.lower()
                while '  ' in tagname:
                    tagname = tagname.replace('  ', ' ')
                if not tagname or tagname == ' ':
                    continue
                if tagname not in tagdict:
                    cobj = models.Tag(name=tagname)
                    cobj.save()
                    tagdict[tagname] = cobj
                fcat.append(tagdict[tagname])
    return fcat

def get_entry_data(entry, feed, tagdict):
    """ Retrieves data from a post and returns it in a tuple.
    """
    try:
        link = encode(entry.link)
    except AttributeError:
        link = feed.link
    try:
        title = encode(entry.title)
    except AttributeError:
        title = link
    guid = encode(entry.get('id', title))

    if entry.has_key('author_detail'):
        author = encode(entry.author_detail.get('name', ''))
        author_email = encode(entry.author_detail.get('email', ''))
    else:
        author, author_email = '', ''

    if not author:
        author = encode(entry.get('author', entry.get('creator', '')))
    if not author_email:
        author_email = 'nospam@nospam.com'
    
    try:
        content = encode(entry.content[0].value)
    except:
        content = encode(entry.get('summary', entry.get('description', '')))
    
    if entry.has_key('modified_parsed'):
        date_modified = mtime(entry.modified_parsed)
    else:
        date_modified = None

    fcat = get_tags(entry, tagdict)
    comments = encode(entry.get('comments', ''))

    return (link, title, guid, author, author_email, content, date_modified, \
      fcat, comments)

def process_entry(entry, fpf, feed, postdict, tagdict, options):
    """ Process a post in a feed and saves it in the DB if necessary.
    """
    
    (link, title, guid, author, author_email, content, date_modified, fcat, \
      comments) = get_entry_data(entry, feed, tagdict)

    if options.verbose:
        print 'entry:'
        print '  title:', title
        print '  link:', link
        print '  guid:', guid
        print '  author:', author
        print '  author_email:', author_email
        print '  tags:', [tcat.name for tcat in fcat]

    if guid in postdict:
        tobj = postdict[guid]
        if options.verbose:
            print '  - Existing previous post object, updating..'
        postdict[guid] = tobj
        if tobj.content != content or \
          (date_modified and tobj.date_modified != date_modified):
            if options.verbose:
                print '  - Post has changed, updating...'
            if not date_modified:
                # damn non-standard feeds
                date_modified = tobj.date_modified
            tobj.title = title
            tobj.link = link
            tobj.content = content
            tobj.guid = guid
            tobj.date_modified = date_modified
            tobj.author = author
            tobj.author_email = author_email
            tobj.comments = comments
            tobj.tags.clear()
            [tobj.tags.add(tcat) for tcat in fcat]
            tobj.save()
        elif options.verbose:
            print '  - Post has not changed, ignoring.'
    else:
        if options.verbose:
            print '  - Creating post object...'
        if not date_modified:
            # if the feed has no date_modified info, we use the feed mtime or
            # the current time
            if fpf.feed.has_key('modified_parsed'):
                date_modified = mtime(fpf.feed.modified_parsed)
            elif fpf.has_key('modified'):
                date_modified = mtime(fpf.modified)
            else:
                date_modified = datetime.datetime.now()
        tobj = models.Post(feed=feed, title=title, link=link,
            content=content, guid=guid, date_modified=date_modified,
            author=author, author_email=author_email,
            comments=comments)
        tobj.save()
        [tobj.tags.add(tcat) for tcat in fcat]

def process_feed(feed, tagdict, options):
    """ Downloads and parses a feed.
    """
    if options.verbose:
        print '#\n# Processing feed:', feed.feed_url, '\n#'
    else:
        print '# Processing feed:', feed.feed_url
    
    # we check the etag and the modified time to save bandwith and avoid bans
    try:
        fpf = feedparser.parse(feed.feed_url, agent=USER_AGENT,
            etag=feed.etag)
    except:
        print '! ERROR: feed cannot be parsed'
        return 1
    
    if hasattr(fpf, 'status'):
        if options.verbose:
            print 'fpf.status:', fpf.status
        if fpf.status == 304:
            # this means the feed has not changed
            if options.verbose:
                print 'Feed has not changed since last check, ignoring.'
            return 2

        if fpf.status >= 400:
            # http error, ignore
            print '! HTTP ERROR'
            return 3

    if hasattr(fpf, 'bozo') and fpf.bozo and options.verbose:
        print '!BOZO'

    # the feed has changed (or it is the first time we parse it)
    # saving the etag and last_modified fields
    feed.etag = encode(fpf.get('etag', ''))
    try:
        feed.last_modified = mtime(fpf.modified)
    except:
        pass
    
    feed.title = encode(fpf.feed.get('title', ''))[0:254]
    feed.tagline = encode(fpf.feed.get('tagline', ''))
    feed.link = encode(fpf.feed.get('link', ''))
    feed.last_checked = datetime.datetime.now()

    if options.verbose:
        print 'feed.title', feed.title
        print 'feed.tagline', feed.tagline
        print 'feed.link', feed.link
        print 'feed.last_checked', feed.last_checked

    guids = []
    for entry in fpf.entries:
        if encode(entry.get('id', '')):
            guids.append(encode(entry.get('id', '')))
        elif entry.title:
            guids.append(encode(entry.title))
        elif entry.link:
            guids.append(encode(entry.link))
    feed.save()
    if guids:
        postdict = dict([(post.guid, post) \
          for post in models.Post.objects.filter(feed=feed.id).filter(guid__in=guids)])
    else:
        postdict = {}

    for entry in fpf.entries:
        try:
            process_entry(entry, fpf, feed, postdict, tagdict, options)
        except:
            (etype, eobj, etb) = sys.exc_info()
            print '! -------------------------'
            print traceback.format_exception(etype, eobj, etb)
            traceback.print_exception(etype, eobj, etb)
            print '! -------------------------'

    feed.save()

    return 0

def update_feeds(tagdict, options):
    """ Updates all active feeds.
    """

    #for feed in models.Feed.objects.filter(is_active=True).iterator():
    for feed in models.Feed.objects.filter(is_active=True):
        try:
            process_feed(feed, tagdict, options)
        except:
            (etype, eobj, etb) = sys.exc_info()
            print '! -------------------------'
            print traceback.format_exception(etype, eobj, etb)
            traceback.print_exception(etype, eobj, etb)
            print '! -------------------------'

def main():
    """ Main function. Nothing to see here. Move along.
    """
    parser = optparse.OptionParser(usage='%prog [options]', version=USER_AGENT)
    parser.add_option('--settings', \
      help='Python path to settings module. If this isn\'t provided, the DJANGO_SETTINGS_MODULE enviroment variable will be used.')
    parser.add_option('-f', '--feed', action='append', type='int', \
      help='A feed id to be updated. This option can be given multiple times to update several feeds at the same time (-f 1 -f 4 -f 7).')
    parser.add_option('-s', '--site', type='int', \
      help='A site id to update.')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', \
      default=False, help='Verbose output.')
    parser.add_option('-t', '--timeout', type='int', default=10, \
      help='Wait timeout in seconds when connecting to feeds.')
    options = parser.parse_args()[0]
    tagdict = dict([(tag.name, tag) for tag in models.Tag.objects.all()])
    if options.settings:
        os.environ["DJANGO_SETTINGS_MODULE"] = options.settings

    # settting socket timeout (default= 10 seconds)
    socket.setdefaulttimeout(options.timeout)
    
    if options.feed:
        for feed in options.feed:
            try:
                process_feed(models.Feed.objects.get(pk=feed), tagdict, options)
            except  models.Feed.DoesNotExist:
                print '! Unknown feed id: ', feed
    elif options.site:
        feeds = [sub.feed \
          for sub in \
          models.Site.objects.get(pk=int(options.site)).subscriber_set.all()]
        for feed in feeds:
            try:
                process_feed(feed, tagdict, options)
            except  models.Feed.DoesNotExist:
                print '! Unknown site id: ', feed
    else:
        update_feeds(tagdict, options)

    # removing the cached data in all sites, this will only work with the
    # memcached, db and file backends
    [fjcache.cache_delsite(site.id) for site in models.Site.objects.all()]

if __name__ == '__main__':
    main()

#~
