from django.urls import path

from . import views

app_name = "wiki_backoffice"

urlpatterns = [
    path("", views.WikiEntryListView.as_view(), name="entry_list"),
    path("entries/new/", views.WikiEntryCreateView.as_view(), name="entry_create"),
    path("entries/<int:pk>/edit/", views.WikiEntryUpdateView.as_view(), name="entry_edit"),
]
