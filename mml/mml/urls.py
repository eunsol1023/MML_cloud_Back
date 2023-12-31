# mml/urls.py

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/', include('user.urls')), # user 앱의 URL 포함시킵니다.
    path('music/', include('music.urls')),
]
