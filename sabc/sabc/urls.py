# -*- coding: utf-8 -*-
from django.conf import settings
from django.urls import path
from django.contrib import admin
from django.contrib.auth.views import (
    LoginView as Login,
    LogoutView as Logout,
    PasswordResetView as PWReset,
    PasswordChangeDoneView as PWDone,
    PasswordResetConfirmView as PWConfirm,
    PasswordResetCompleteView as PWComplete,
)
from django.conf.urls.static import static
from django.utils.translation import gettext_lazy as _

from tournaments.views import (
    annual_awards,
    ResultCreateView as ResultCreate,
    TournamentListView as TmntList,
    TournamentCreateView as TmntCreate,
    TournamentDetailView as TmntDetail,
    TournamentUpdateView as TmntUpdate,
    TournamentDeleteView as TmntDelete,
    # TeamCreateView,
    # TeamDetailView,
    # TeamListView,
)

from users.views import (
    about,
    bylaws,
    roster,
    calendar,
    AnglerDetailView as Profile,
    AnglerEditView as Edit,
    AnglerRegistrationView as Register,
)

TMNT_CREATE = ("tournament/new/", "tournament-create")
TMNT_DETAIL = ("tournament/<int:pk>/", "tournament-details")
TMNT_UPDATE = (f"{TMNT_DETAIL}/update/", "tournament-update")
TMNT_DELETE = (f"{TMNT_DETAIL}/delete/", "tournament-delete")

# TODO Add Team Controls
# TEAM_LIST = ("tournament/<int:pk>/list_teams", "team-list")
# TEAM_CREATE = ("tournament/<int:pk>/add_team", "team-create")
# TEAM_DETAIL = ("team/<int:pk>/", "team-details")
# TEAM_DELETE = ("", "")
RESULT_CREATE = ("tournament/<int:pk>/add_result/", "result-create")

LOGIN = ("login/", "users/login.html", "login")
LOGOUT = ("logout/", "users/logout.html", "logout")
PW_RESET = ("password-reset/", "users/password_reset.html", "password-reset")
PW_DONE = ("password-reset/done/", "users/password_reset_done.html", "password_reset_done")
PW_CONFIRM = (
    "password-reset-confirm/<uidb64>/<token>/",
    "users/password_reset_confirm.html",
    "password_reset_confirm",
)
PW_COMPLETE = (
    "password-reset-complete/",
    "users/password_reset_complete.html",
    "password_reset_complete",
)

urlpatterns = [
    path("", TmntList.as_view(), name="sabc-home"),
    path("about/", about, name="about"),
    path("admin/", admin.site.urls),
    path("bylaws/", bylaws, name="bylaws"),
    path("roster/", roster, name="roster"),
    path("awards/", annual_awards, name="annual-awards"),
    path("calendar/", calendar, name="calendar"),
    path("register/", Register.as_view(), name="register"),
    path("profile/<int:pk>/", Profile.as_view(), name="profile"),
    path("profile_edit/<int:pk>/", Edit.as_view(), name="profile-edit"),
    path(TMNT_CREATE[0], TmntCreate.as_view(), name=TMNT_CREATE[1]),
    path(TMNT_DETAIL[0], TmntDetail.as_view(), name=TMNT_DETAIL[1]),
    path(TMNT_UPDATE[0], TmntUpdate.as_view(), name=TMNT_UPDATE[1]),
    path(TMNT_DELETE[0], TmntDelete.as_view(), name=TMNT_DELETE[1]),
    path(RESULT_CREATE[0], ResultCreate.as_view(), name=RESULT_CREATE[1]),
    # path(TEAM_CREATE[0], TeamCreateView.as_view(), name=TEAM_CREATE[1]),
    # path(TEAM_LIST[0], TeamListView.as_view(), name=TEAM_LIST[1]),
    # path(TEAM_DETAIL[0], TeamDetailView.as_view(), name=TEAM_DETAIL[1]),
    path(LOGIN[0], Login.as_view(template_name=LOGIN[1]), name=LOGIN[2]),
    path(LOGOUT[0], Logout.as_view(template_name=LOGOUT[1]), name=LOGOUT[2]),
    path(PW_RESET[0], PWReset.as_view(template_name=PW_RESET[1]), name=PW_RESET[2]),
    path(PW_DONE[0], PWDone.as_view(template_name=PW_DONE[1]), name=PW_DONE[2]),
    path(PW_CONFIRM[0], PWConfirm.as_view(template_name=PW_CONFIRM[1]), name=PW_CONFIRM[2]),
    path(PW_COMPLETE[0], PWComplete.as_view(template_name=PW_COMPLETE[1]), name=PW_COMPLETE[2]),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customizations
admin.site.site_title = _("SABC")
admin.site.site_header = _("South Austin Bass Club Administration")
admin.site.index_title = _("Tournaments")
