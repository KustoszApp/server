import rest_framework.authtoken.views
from django.urls import path

from readorganizer_api import views

urlpatterns = [
    path("users/login", rest_framework.authtoken.views.obtain_auth_token),
    path("channels/", views.ChannelList.as_view()),
    path("channels/<int:pk>/", views.ChannelDetail.as_view()),
]
