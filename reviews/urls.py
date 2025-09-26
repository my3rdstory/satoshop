from django.urls import path

from .views import (
    ReviewCreateView,
    ReviewDeleteView,
    ReviewImageDeleteView,
    ReviewUpdateView,
)

app_name = 'reviews'

urlpatterns = [
    path('<str:store_id>/<int:product_id>/create/', ReviewCreateView.as_view(), name='create'),
    path('<str:store_id>/<int:product_id>/<int:review_id>/update/', ReviewUpdateView.as_view(), name='update'),
    path('<str:store_id>/<int:product_id>/<int:review_id>/delete/', ReviewDeleteView.as_view(), name='delete'),
    path(
        '<str:store_id>/<int:product_id>/<int:review_id>/images/<int:image_id>/delete/',
        ReviewImageDeleteView.as_view(),
        name='delete_image',
    ),
]
