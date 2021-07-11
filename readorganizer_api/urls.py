import rest_framework.authtoken.views
from django.urls import path

from readorganizer_api import views

urlpatterns = [
    path("users/login", rest_framework.authtoken.views.obtain_auth_token),
    path("channels/", views.ChannelList.as_view(), name="channels_list"),
    path("channels/<int:pk>/", views.ChannelDetail.as_view(), name="channel_detail"),
    path("entries/", views.EntriesList.as_view(), name="entries_list"),
    path("entries/<int:pk>/", views.EntryDetail.as_view(), name="entry_detail"),
]
