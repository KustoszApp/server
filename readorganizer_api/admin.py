from django.contrib import admin

from readorganizer_api import models

admin.site.register(models.Entry)
admin.site.register(models.EntryContent)
admin.site.register(models.EntryTag)
admin.site.register(models.Feed)
admin.site.register(models.FeedTag)
admin.site.register(models.Profile)
