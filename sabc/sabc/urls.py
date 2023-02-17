# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView as Login
from django.contrib.auth.views import LogoutView as Logout
from django.contrib.auth.views import PasswordChangeDoneView as PWDone
from django.contrib.auth.views import PasswordResetCompleteView as PWComplete
from django.contrib.auth.views import PasswordResetConfirmView as PWConfirm
from django.contrib.auth.views import PasswordResetView as PWReset
from django.urls import URLPattern, URLResolver, path
from polls.views import LakePollCreateView as PollCreate
from polls.views import LakePollListView as PollList
from polls.views import LakePollView as Poll
from tournaments.views import annual_awards
from tournaments.views.events import EventUpdateView as EventUpdate
from tournaments.views.results import ResultCreateView as ResultCreate
from tournaments.views.results import ResultDeleteView as ResultDelete
from tournaments.views.results import ResultUpdateView as ResultUpdate
from tournaments.views.results import TeamCreateView as TeamCreate
from tournaments.views.results import TeamResultDeleteView as TeamDelete
from tournaments.views.tournaments import TournamentCreateView as TmntCreate
from tournaments.views.tournaments import TournamentDeleteView as TmntDelete
from tournaments.views.tournaments import TournamentDetailView as TmntDetail
from tournaments.views.tournaments import TournamentListView as TmntList
from tournaments.views.tournaments import TournamentUpdateView as TmntUpdate
from users.views import AnglerDetailView as Profile
from users.views import AnglerRegistrationView as Register
from users.views import AnglerUpdateView as Edit
from users.views import about, bylaws, calendar, roster

POLL_CREATE: tuple[str, str] = ("polls/new/", "lakepoll-create")
TMNT_CREATE: tuple[str, str] = ("tournament/new/", "tournament-create")
TMNT_DETAIL: tuple[str, str] = ("tournament/<int:pk>/", "tournament-details")
TMNT_UPDATE: tuple[str, str] = ("tournament/<int:pk>/update/", "tournament-update")
TMNT_DELETE: tuple[str, str] = ("tournament/<int:pk>/delete/", "tournament-delete")

TEAM_CREATE: tuple[str, str] = ("tournament/<int:pk>/add_team/", "team-create")
TEAM_DELETE: tuple[str, str] = ("teamresult/<int:pk>/delete/", "teamresult-delete")
RESULT_CREATE: tuple[str, str] = ("tournament/<int:pk>/add_result/", "result-create")
RESULT_UPDATE: tuple[str, str] = ("result/<int:pk>/update/", "result-update")
RESULT_DELETE: tuple[str, str] = ("result/<int:pk>/delete/", "result-delete")

EVENT_UPDATE: tuple[str, str] = ("event/<int:pk>/", "event-update")
LOGIN: tuple[str, str, str] = ("login/", "users/login.html", "login")
LOGOUT: tuple[str, str, str] = ("logout/", "users/logout.html", "logout")
PW_RESET: tuple[str, str, str] = (
    "password-reset/",
    "users/password_reset.html",
    "password-reset",
)
PW_DONE: tuple[str, str, str] = (
    "password-reset/done/",
    "users/password_reset_done.html",
    "password_reset_done",
)
PW_CONFIRM: tuple[str, str, str] = (
    "password-reset-confirm/<uidb64>/<token>/",
    "users/password_reset_confirm.html",
    "password_reset_confirm",
)
PW_COMPLETE: tuple[str, str, str] = (
    "password-reset-complete/",
    "users/password_reset_complete.html",
    "password_reset_complete",
)

urlpatterns: list[URLPattern | URLResolver] = [
    path("", TmntList.as_view(), name="sabc-home"),
    path("polls/", PollList.as_view(), name="polls"),
    path("polls/<int:pid>/", Poll.as_view(), name="poll"),
    path("about/", about, name="about"),
    path("admin/", admin.site.urls),
    path("bylaws/", bylaws, name="bylaws"),
    path("roster/", roster, name="roster"),
    path("awards/<int:year>/", annual_awards, name="annual-awards"),
    path("calendar/", calendar, name="calendar"),
    path("register/", Register.as_view(), name="register"),
    path("profile/<int:pk>/", Profile.as_view(), name="profile"),
    path("profile_edit/<int:pk>/", Edit.as_view(), name="profile-edit"),
    path(POLL_CREATE[0], PollCreate.as_view(), name=POLL_CREATE[1]),
    path(EVENT_UPDATE[0], EventUpdate.as_view(), name=EVENT_UPDATE[1]),
    path(TMNT_CREATE[0], TmntCreate.as_view(), name=TMNT_CREATE[1]),
    path(TMNT_DETAIL[0], TmntDetail.as_view(), name=TMNT_DETAIL[1]),
    path(TMNT_UPDATE[0], TmntUpdate.as_view(), name=TMNT_UPDATE[1]),
    path(TMNT_DELETE[0], TmntDelete.as_view(), name=TMNT_DELETE[1]),
    path(RESULT_CREATE[0], ResultCreate.as_view(), name=RESULT_CREATE[1]),
    path(RESULT_UPDATE[0], ResultUpdate.as_view(), name=RESULT_UPDATE[1]),
    path(RESULT_DELETE[0], ResultDelete.as_view(), name=RESULT_DELETE[1]),
    path(TEAM_CREATE[0], TeamCreate.as_view(), name=TEAM_CREATE[1]),
    path(TEAM_DELETE[0], TeamDelete.as_view(), name=TEAM_DELETE[1]),
    path(LOGIN[0], Login.as_view(template_name=LOGIN[1]), name=LOGIN[2]),
    path(LOGOUT[0], Logout.as_view(template_name=LOGOUT[1]), name=LOGOUT[2]),
    path(PW_RESET[0], PWReset.as_view(template_name=PW_RESET[1]), name=PW_RESET[2]),
    path(PW_DONE[0], PWDone.as_view(template_name=PW_DONE[1]), name=PW_DONE[2]),
    path(
        PW_CONFIRM[0],
        PWConfirm.as_view(template_name=PW_CONFIRM[1]),
        name=PW_CONFIRM[2],
    ),
    path(
        PW_COMPLETE[0],
        PWComplete.as_view(template_name=PW_COMPLETE[1]),
        name=PW_COMPLETE[2],
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
