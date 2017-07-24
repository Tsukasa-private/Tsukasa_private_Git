from django.conf.urls import url

from . import views

app_name = 'dumpviewer'
urlpatterns = [
    url(r'^search/?$', views.search, name='search'),
    url(r'^save/?$', views.save, name='save'),
    url(r'^saved/(?P<identifier>.*?)?$', views.saved, name='saved'),
    url(r'^$', views.delete, name='delete'),
    url(r'^$', views.welcome, name='welcome'),
]
