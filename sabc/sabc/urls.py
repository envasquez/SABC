"""sabc URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.utils.translation import ugettext_lazy as _

from users import views as user_views


urlpatterns = [
    # Admin site
    url(r'^admin/', admin.site.urls),
    # Global Pages
    url(r'^$', user_views.index, name='sabc-home'),
    url(r'^about', user_views.about, name='about'),
    # User Views
    url(r'^login', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    url(r'^logout', auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),
    url(r'^profile', user_views.profile, name='profile'),
    url(r'^register', user_views.register, name='register'),
]

admin.site.site_title = _('SABC')
admin.site.site_header = _('South Austin Bass Club Administration')
admin.site.index_title = _('Tournaments')
