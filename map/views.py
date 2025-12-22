from django.shortcuts import render


def map_home(request):
    return render(request, 'map/map.html')
