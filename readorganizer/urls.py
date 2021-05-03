"""api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include
from django.urls import path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/", include("readorganizer_api.urls")),
]
