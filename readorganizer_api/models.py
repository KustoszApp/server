from django.contrib.auth.models import User
from django.db import models


class SourceTypes(models.TextChoices):
    FEED_SUMMARY = "summary", "Feed summary"
    FEED_CONTENT = "content", "Feed content"
    READABILITY = "readability", "Readability"
    NODE_READABILITY = "nodereadability", "Node Readability"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - profile"


class Feed(models.Model):
    # TODO: type - RSS/Atom, JSON Feed, WebSub, email
    url = models.URLField(max_length=2048, unique=True)
    title = models.TextField(blank=True)
    custom_title = models.TextField(blank=True)
    last_checked = models.DateTimeField(blank=True, null=True)
    added = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    update_frequency = models.IntegerField(
        default=3600, help_text="How often feed should be checked, in seconds"
    )


class Entry(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    title = models.TextField(blank=True)
    link = models.URLField(max_length=2048)
    updated = models.DateTimeField(blank=True, null=True)
    author = models.TextField(blank=True)
    published = models.DateTimeField(blank=True, null=True)
    read = models.BooleanField(default=True)


class EntryContent(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE)
    source = models.CharField(max_length=20, choices=SourceTypes.choices)
    content = models.TextField()


class FeedTag(models.Model):
    name = models.CharField(max_length=255, unique=True)


class EntryTag(models.Model):
    name = models.CharField(max_length=255, unique=True)
