"""SABC URL Configuration"""
# pylint: disable=invalid-name, import-error
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import (
    LoginView as Login,
    LogoutView as Logout,
    PasswordResetView as PWReset,
    PasswordChangeDoneView as PWChgDone,
    PasswordResetConfirmView as PWConfirm,
    PasswordResetCompleteView as PWRstComplete,
)
from django.conf.urls.static import static
from django.utils.translation import gettext_lazy as _

from tournaments.views import (
    TournamentCreateView as TmntCreate,
    TournamentDetailView as TmntDetail,
    TournamentListView as TmntList,
    TournamentUpdateView as TmntUpdate,
    TournamentDeleteView as TmntDelete,
    # TeamCreateView,
    # TeamDetailView,
    # TeamListView,
    ResultCreateView,
)

from users.views import (
    about,
    bylaws,
    profile,
    gallery,
    register,
    calendar,
    list_guests,
    list_members,
    list_officers,
)

TMNT_CREATE = ("tournament/new", "tournament-create")
TMNT_DETAIL = ("tournament/<int:pk>/", "tournament-details")
TMNT_UPDATE = (f"{TMNT_DETAIL}/update/", "tournament-update")
TMNT_DELETE = (f"{TMNT_DETAIL}/delete/", "tournament-delete")

# TODO Add Team Controls
# TEAM_LIST = ("tournament/<int:pk>/list_teams", "team-list")
# TEAM_CREATE = ("tournament/<int:pk>/add_team", "team-create")
# TEAM_DETAIL = ("team/<int:pk>/", "team-details")
# TEAM_DELETE = ("", "")
RESULT_CREATE = ("tournament/<int:pk>/add_result/", "result-create")

urlpatterns = [
    path("login", Login.as_view(template_name="users/login.html"), name="login"),
    path("logout", Logout.as_view(template_name="users/logout.html"), name="logout"),
    path(
        "password-reset/",
        PWReset.as_view(template_name="users/password_reset.html"),
        name="password-reset",
    ),
    path(
        "password-reset/done",
        PWChgDone.as_view(template_name="users/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>",
        PWConfirm.as_view(template_name="users/password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        PWRstComplete.as_view(template_name="users/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("about/", about, name="about"),
    path("admin/", admin.site.urls),
    path("bylaws/", bylaws, name="bylaws"),
    path("profile/", profile, name="profile"),
    path("gallery/", gallery, name="gallery"),
    path("register/", register, name="register"),
    path("calendar/", calendar, name="calendar"),
    path("members/", list_members, name="list-members"),
    path("officers/", list_officers, name="list-officers"),
    path("guests/", list_guests, name="list-guests"),
    path("", TmntList.as_view(), name="sabc-home"),
    path(TMNT_CREATE[0], TmntCreate.as_view(), name=TMNT_CREATE[1]),
    path(TMNT_DETAIL[0], TmntDetail.as_view(), name=TMNT_DETAIL[1]),
    path(TMNT_UPDATE[0], TmntUpdate.as_view(), name=TMNT_UPDATE[1]),
    path(TMNT_DELETE[0], TmntDelete.as_view(), name=TMNT_DELETE[1]),
    path(RESULT_CREATE[0], ResultCreateView.as_view(), name=RESULT_CREATE[1]),
    # path(TEAM_CREATE[0], TeamCreateView.as_view(), name=TEAM_CREATE[1]),
    # path(TEAM_LIST[0], TeamListView.as_view(), name=TEAM_LIST[1]),
    # path(TEAM_DETAIL[0], TeamDetailView.as_view(), name=TEAM_DETAIL[1]),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customizations
admin.site.site_title = _("SABC")
admin.site.site_header = _("South Austin Bass Club Administration")
admin.site.index_title = _("Tournaments")
