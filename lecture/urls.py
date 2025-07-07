from django.urls import path
from . import views

app_name = 'lecture'

urlpatterns = [
    path('', views.LectureListView.as_view(), name='list'),
    path('<int:pk>/', views.LectureDetailView.as_view(), name='detail'),
    path('<int:pk>/enroll/', views.enroll_lecture, name='enroll'),
    path('my-lectures/', views.MyLecturesView.as_view(), name='my_lectures'),
    path('category/<int:category_id>/', views.LectureListView.as_view(), name='category'),
] 