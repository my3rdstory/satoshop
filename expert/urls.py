from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "expert"


urlpatterns = [
    path("", views.ExpertLandingView.as_view(), name="landing"),
    path("login/", views.ExpertLightningLoginGuideView.as_view(), name="login"),
    path("contracts/direct/", views.DirectContractDraftView.as_view(), name="direct-draft"),
    path(
        "contracts/direct/draft/",
        RedirectView.as_view(pattern_name="expert:direct-draft", permanent=False),
        name="legacy-direct-draft",
    ),
    path("contracts/direct/review/<str:token>/", views.DirectContractReviewView.as_view(), name="direct-review"),
    path("contracts/direct/library/", views.DirectContractLibraryView.as_view(), name="direct-library"),
    path("contracts/direct/verify/", views.DirectContractIntegrityCheckView.as_view(), name="direct-verify"),
    path("contracts/direct/link/<slug:slug>/", views.DirectContractInviteView.as_view(), name="direct-invite"),
    path("contracts/direct/payment/widget/", views.direct_contract_payment_widget, name="direct-payment-widget"),
    path("contracts/direct/payment/start/", views.direct_contract_payment_start, name="direct-payment-start"),
    path("contracts/direct/payment/cancel/", views.direct_contract_payment_cancel, name="direct-payment-cancel"),
    path("contracts/direct/payment/status/", views.direct_contract_payment_status, name="direct-payment-status"),
    path("contracts/<uuid:public_id>/", views.ContractDetailView.as_view(), name="contract-detail"),
]
