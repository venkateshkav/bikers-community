from django.urls import path

from . import views

app_name = "rides"

urlpatterns = [
    path("rides/", views.my_rides_view, name="my-rides"),
    path("rides/<int:ride_id>/", views.ride_detail_view, name="ride-detail"),
    path("rides/<int:ride_id>/starting-point/", views.starting_point_action, name="starting-point"),
    path("rides/<int:ride_id>/destination/", views.destination_action, name="destination"),
    path("rides/<int:ride_id>/home-confirmation/", views.home_confirmation_action, name="home-confirmation"),
]
