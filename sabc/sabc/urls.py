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
# pylint: disable=invalid-name, import-error
from django.conf import settings
from django.contrib import admin
from django.urls import re_path
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.utils.translation import gettext_lazy as _

from users import views as user_views
from tournaments import views as tournament_views


urlpatterns = [
    re_path(
        r"^login", auth_views.LoginView.as_view(template_name="users/login.html"), name="login"
    ),
    re_path(
        r"^logout", auth_views.LogoutView.as_view(template_name="users/logout.html"), name="logout"
    ),
    re_path(
        r"^password-reset/$",
        auth_views.PasswordResetView.as_view(template_name="users/password_reset.html"),
        name="password-reset",
    ),
    re_path(
        r"^password-reset/done",
        auth_views.PasswordChangeDoneView.as_view(template_name="users/password_reset_done.html"),
        name="password_reset_done",
    ),
    re_path(
        r"^password-reset-confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    re_path(
        r"^password-reset-complete/$",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="users/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    re_path(r"^$", tournament_views.TournamentListView.as_view(), name="sabc-home"),
    re_path(r"^about", user_views.about, name="about"),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^bylaws", user_views.bylaws, name="bylaws"),
    re_path(r"^profile", user_views.profile, name="profile"),
    re_path(r"^gallery", user_views.gallery, name="gallery"),
    re_path(r"^register", user_views.register, name="register"),
    re_path(r"^calendar", user_views.calendar, name="calendar"),
    re_path(r"^members", user_views.list_members, name="list-members"),
    re_path(r"^officers", user_views.list_officers, name="list-officers"),
    re_path(r"^guests", user_views.list_guests, name="list-guests"),
    re_path(
        r"^tournament/new/$",
        tournament_views.TournamentCreateView.as_view(),
        name="tournament-create",
    ),
    re_path(
        r"^tournament/(?P<pk>\d+)/$",
        tournament_views.TournamentDetailView.as_view(),
        name="tournament-details",
    ),
    re_path(
        r"^tournament/(?P<pk>\d+)/update/$",
        tournament_views.TournamentUpdateView.as_view(),
        name="tournament-update",
    ),
    re_path(
        r"^tournament/(?P<pk>\d+)/delete/$",
        tournament_views.TournamentDeleteView.as_view(),
        name="tournament-delete",
    ),
    re_path(
        r"^tournament/(?P<pk>\d+)/add_team/$",
        tournament_views.TeamCreateView.as_view(),
        name="team-create",
    ),
    re_path(
        r"^tournament/(?P<pk>\d+)/list_teams/$",
        tournament_views.TeamListView.as_view(),
        name="team-list",
    ),
    re_path(r"^team/(?P<pk>\d+)/$", tournament_views.TeamDetailView.as_view(), name="team-details"),
    re_path(
        r"^tournament/(?P<pk>\d+)/add_result/$",
        tournament_views.ResultCreateView.as_view(),
        name="result-create",
    ),
    # Disable these for production use
    #
    # re_path(r"^gen_member", user_views.gen_member, name="gen-member"),
    # re_path(r"^gen_officers", user_views.gen_officers, name="gen-officers"),
    # re_path(r"^gen_guest", user_views.gen_guest, name="gen-guest"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customizations
admin.site.site_title = _("SABC")
admin.site.site_header = _("South Austin Bass Club Administration")
admin.site.index_title = _("Tournaments")
