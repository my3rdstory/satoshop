from django.urls import path

from . import views

app_name = "wiki_api"

urlpatterns = [
    path("discord/interactions/", views.discord_interaction_view, name="discord_interaction"),
]
