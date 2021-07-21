import rest_framework.authtoken.views
from django.urls import path

from readorganizer_api import views

urlpatterns = [
    path("users/login", rest_framework.authtoken.views.obtain_auth_token),
    path("channels/", views.ChannelsList.as_view(), name="channels_list"),
    path("channels/<int:pk>/", views.ChannelDetail.as_view(), name="channel_detail"),
    path(
        "channels/inactivate",
        views.ChannelsInactivate.as_view(),
        name="channels_inactivate",
    ),
    path("entries/", views.EntriesList.as_view(), name="entries_list"),
    path("entries/<int:pk>/", views.EntryDetail.as_view(), name="entry_detail"),
    path("entries/archive", views.EntriesArchive.as_view(), name="entries_archive"),
    path("tags/channel", views.ChannelTagsList.as_view(), name="channel_tags_list"),
    path("tags/entry", views.EntryTagsList.as_view(), name="entry_tags_list"),
]
