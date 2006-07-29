# -*- coding: utf-8 -*-
# pylint: disable-msg=W0232, R0903, W0131

"""
feedjack
Gustavo Picón
models.py
"""

from django.db import models

from feedjack import fjcache

SITE_ORDERBY_CHOICES = (
    (1, 'Date published.'),
    (2, 'Date the post was first obtained.')
)

class Link(models.Model):
    name = models.CharField(maxlength=100, unique=True)
    link = models.URLField(verify_exists=True)

    class Admin:
        pass

    def __str__(self):
        return '%s (%s)' % (self.name, self.link)


class Site(models.Model):
    name = models.CharField(maxlength=100)
    url = models.CharField(maxlength=100, unique=True, \
      help_text='Example: http://www.planetexample.com, ' \
        'http://www.planetexample.com:8000/foo')
    title = models.CharField(maxlength=200)
    description = models.TextField()
    welcome = models.TextField(null=True, blank=True)
    greets = models.TextField(null=True, blank=True)

    default_site = models.BooleanField(default=False)
    posts_per_page = models.IntegerField(default=20)
    order_posts_by = models.IntegerField(default=1, \
      choices=SITE_ORDERBY_CHOICES)
    tagcloud_levels = models.IntegerField(default=5)
    show_tagcloud = models.BooleanField(default=True)
    
    use_internal_cache = models.BooleanField(default=True)
    cache_duration = models.IntegerField(default=60*60*24, \
      help_text='Duration in seconds of the cached pages and data.')

    links = models.ManyToManyField(Link, filter_interface=models.VERTICAL, \
      null=True, blank=True)
    template = models.CharField(maxlength=100, null=True, blank=True, \
      help_text='This template must be a directory in your feedjack ' \
        'templates directory. Leave blank to use the default template.')

    class Admin:
        list_display = ('url', 'name')

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def save(self):
        if not self.template:
            self.template = 'default'
        # there must be only ONE default site
        defs = Site.objects.filter(default_site=True)
        if not defs:
            self.default_site = True
        elif self.default_site:
            for tdef in defs:
                if tdef.id != self.id:
                    tdef.default_site = False
                    tdef.save()
        self.url = self.url.rstrip('/')
        fjcache.hostcache_set({})
        super(Site, self).save()



class Feed(models.Model):
    feed_url = models.URLField(unique=True)

    name = models.CharField(maxlength=100)
    shortname = models.CharField(maxlength=50)
    is_active = models.BooleanField(default=True, \
      help_text='If this is disabled, ths feed will not be further updated.')

    title = models.CharField(maxlength=200, blank=True)
    tagline = models.TextField(blank=True)
    link = models.URLField(blank=True)

    # http://feedparser.org/docs/http-etag.html
    etag = models.CharField(maxlength=50, blank=True)
    last_modified = models.DateTimeField(null=True, blank=True)
    last_checked = models.DateTimeField(null=True, blank=True)

    class Admin:
        list_display = ('name', 'feed_url', 'title', 'last_modified', \
          'is_active')
        fields = (
          (None, {'fields':('feed_url', 'name', 'shortname', 'is_active')}),
          ('Fields updated automatically by Feedjack', {
            'classes':'collapse',
            'fields':('title', 'tagline', 'link', 'etag', 'last_modified', \
              'last_checked')})
        )
        search_fields = ['feed_url', 'name', 'title']

    class Meta:
        ordering = ('name', 'feed_url',)

    def __str__(self):
        return '%s (%s)' % (self.name, self.feed_url)

    def save(self):
        super(Feed, self).save()

class Tag(models.Model):
    name = models.CharField(maxlength=50, unique=True)

    class Meta:
        ordering = ('name',)
    
    def __str__(self):
        return self.name

    def save(self):
        super(Tag, self).save()

class Post(models.Model):
    feed = models.ForeignKey(Feed, null=False, blank=False)
    title = models.CharField(maxlength=255)
    link = models.URLField()
    content = models.TextField(blank=True)
    date_modified = models.DateTimeField(null=True, blank=True)
    guid = models.CharField(maxlength=200, db_index=True)
    author = models.CharField(maxlength=50, blank=True)
    author_email = models.EmailField(blank=True)
    comments = models.URLField(blank=True)
    tags = models.ManyToManyField(Tag, filter_interface=models.VERTICAL)
    date_created = models.DateField(auto_now_add=True)

    class Admin:
        list_display = ('title', 'link', 'author', 'date_modified')
        search_fields = ['link', 'title']
        date_hierarchy = 'date_modified'

    class Meta:
        ordering = ('-date_modified',)
        unique_together = (('feed', 'guid'),)

    def __str__(self):
        return self.title

    def save(self):
        super(Post, self).save()

    def get_absolute_url(self):
        return self.link


class Subscriber(models.Model):
    site = models.ForeignKey(Site)
    feed = models.ForeignKey(Feed)

    name = models.CharField(maxlength=100, null=True, blank=True, \
      help_text='Keep blank to use the Feed\'s original name.')
    shortname = models.CharField(maxlength=50, null=True, blank=True, \
      help_text='Keep blank to use the Feed\'s original shortname.')
    is_active = models.BooleanField(default=True, \
      help_text='If disabled, this subscriber will not appear in the site or '\
        'in the site\'s feed.')

    class Admin:
        list_display = ('name', 'site', 'feed')
        list_filter = ('site',)

    class Meta:
        ordering = ('site', 'name', 'feed')
        unique_together = (('site', 'feed'),)

    def __str__(self):
        return '%s in %s' % (self.feed, self.site)

    def get_cloud(self):
        from feedjack import fjcloud
        return fjcloud.getcloud(self.site, self.feed.id)

    def save(self):
        if not self.name:
            self.name = self.feed.name
        if not self.shortname:
            self.shortname = self.feed.shortname
        super(Subscriber, self).save()


#~
