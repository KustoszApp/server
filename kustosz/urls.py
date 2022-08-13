import rest_framework.authtoken.views
from django.contrib import admin
from django.urls import include
from django.urls import path

from kustosz import views

api_authentication = [
    path("login", rest_framework.authtoken.views.obtain_auth_token, name="login"),
    path("me", views.UserDetail.as_view(), name="user_detail"),
]

main_api_paths = [
    path("users/", include(api_authentication)),
    path("autodetect_add", views.AutodetectAdd.as_view(), name="autodetect_add"),
    path("channels/", views.ChannelsList.as_view(), name="channels_list"),
    path("channels/<int:pk>/", views.ChannelDetail.as_view(), name="channel_detail"),
    path(
        "channels/inactivate",
        views.ChannelsInactivate.as_view(),
        name="channels_inactivate",
    ),
    path(
        "channels/activate", views.ChannelsActivate.as_view(), name="channels_activate"
    ),
    path("channels/delete", views.ChannelsDelete.as_view(), name="channels_delete"),
    path("entries/", views.EntriesList.as_view(), name="entries_list"),
    path("entries/<int:pk>/", views.EntryDetail.as_view(), name="entry_detail"),
    path("entries/archive", views.EntriesArchive.as_view(), name="entries_archive"),
    path("entries/manual_add", views.EntryManualAdd.as_view(), name="entry_manual_add"),
    path("export/ott", views.ExportOTT.as_view(), name="export_ott"),
    path("export/channels", views.ExportChannels.as_view(), name="export_channels"),
    path("filters/", views.EntryFiltersList.as_view(), name="entry_filters_list"),
    path(
        "filters/<int:pk>/",
        views.EntryFilterDetail.as_view(),
        name="entry_filter_detail",
    ),
    path("filters/run", views.EntryFiltersRun.as_view(), name="entry_filters_run"),
    path("tags/channel", views.ChannelTagsList.as_view(), name="channel_tags_list"),
    path("tags/entry", views.EntryTagsList.as_view(), name="entry_tags_list"),
]


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/", include(main_api_paths)),
]
