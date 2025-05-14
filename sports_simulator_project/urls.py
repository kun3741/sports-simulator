from django.contrib import admin
from django.urls import path, include
from simulator import views as simulator_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('simulator/', include('simulator.urls')),
    path('', simulator_views.index, name='home'),
]