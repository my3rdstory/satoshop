from django.urls import path

from . import views

app_name = "expert"


urlpatterns = [
    path("", views.ExpertLandingView.as_view(), name="landing"),
    path("login/", views.ExpertLightningLoginGuideView.as_view(), name="login"),
    path("contracts/direct/", views.DirectContractStartView.as_view(), name="create-direct"),
    path("contracts/direct/draft/", views.DirectContractDraftView.as_view(), name="direct-draft"),
    path("contracts/<uuid:public_id>/", views.ContractDetailView.as_view(), name="contract-detail"),
]
