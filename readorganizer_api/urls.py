import rest_framework.authtoken.views
from django.urls import path

from readorganizer_api import views

urlpatterns = [
    path("users/login", rest_framework.authtoken.views.obtain_auth_token),
    path("feeds/", views.FeedList.as_view()),
    path("feeds/<int:pk>/", views.FeedDetail.as_view()),
]
