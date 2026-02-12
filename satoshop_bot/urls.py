from django.urls import path

from . import views

app_name = "satoshop_bot"

urlpatterns = [
    path("discord/interactions/", views.discord_interactions, name="discord_interactions"),
    path(
        "webview/recent-registered/",
        views.recent_registered_items_webview,
        name="recent_registered_items_webview",
    ),
    path(
        "webview/recent-sold/",
        views.recent_sold_items_webview,
        name="recent_sold_items_webview",
    ),
]
