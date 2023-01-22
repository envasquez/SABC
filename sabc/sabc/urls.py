# -*- coding: utf-8 -*-
from functools import partial

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView as Login
from django.contrib.auth.views import LogoutView as Logout
from django.contrib.auth.views import PasswordChangeDoneView as PWDone
from django.contrib.auth.views import PasswordResetCompleteView as PWComplete
from django.contrib.auth.views import PasswordResetConfirmView as PWConfirm
from django.contrib.auth.views import PasswordResetView as PWReset
from django.urls import path
from polls.views import LakePollListView as PollList
from polls.views import LakePollView as Poll
from tournaments.views import EventUpdateView as EventUpdate
from tournaments.views import ResultCreateView as ResultCreate
from tournaments.views import ResultDeleteView as ResultDelete
from tournaments.views import ResultUpdateView as ResultUpdate
from tournaments.views import TeamCreateView as TeamCreate
from tournaments.views import TeamResultDeleteView as TeamDelete
from tournaments.views import TournamentCreateView as TmntCreate
from tournaments.views import TournamentDeleteView as TmntDelete
from tournaments.views import TournamentDetailView as TmntDetail
from tournaments.views import TournamentListView as TmntList
from tournaments.views import TournamentUpdateView as TmntUpdate
from tournaments.views import annual_awards
from users.views import AnglerDetailView as Profile
from users.views import AnglerRegistrationView as Register
from users.views import AnglerUpdateView as Edit
from users.views import about, bylaws, calendar, roster

TMNT_CREATE = ("tournament/new/", "tournament-create")
TMNT_DETAIL = ("tournament/<int:pk>/", "tournament-details")
TMNT_UPDATE = ("tournament/<int:pk>/update/", "tournament-update")
TMNT_DELETE = ("tournament/<int:pk>/delete/", "tournament-delete")

TEAM_CREATE = ("tournament/<int:pk>/add_team/", "team-create")
TEAM_DELETE = ("teamresult/<int:pk>/delete/", "teamresult-delete")
RESULT_CREATE = ("tournament/<int:pk>/add_result/", "result-create")
RESULT_UPDATE = ("result/<int:pk>/update/", "result-update")
RESULT_DELETE = ("result/<int:pk>/delete/", "result-delete")

EVENT_UPDATE = ("event/<int:pk>/", "event-update")
LOGIN = ("login/", "users/login.html", "login")
LOGOUT = ("logout/", "users/logout.html", "logout")
PW_RESET = ("password-reset/", "users/password_reset.html", "password-reset")
PW_DONE = ("password-reset/done/", "users/password_reset_done.html", "password_reset_done")
PW_CONFIRM = ("password-reset-confirm/<uidb64>/<token>/", "users/password_reset_confirm.html", "password_reset_confirm")
PW_COMPLETE = ("password-reset-complete/", "users/password_reset_complete.html", "password_reset_complete")

urlpatterns = [
    path("", TmntList.as_view(), name="sabc-home"),
    path("polls/", PollList.as_view(), name="polls"),
    path("polls/<int:pid>/", Poll.as_view(), name="poll"),
    path("about/", about, name="about"),
    path("admin/", admin.site.urls),
    path("bylaws/", bylaws, name="bylaws"),
    path("roster/", roster, name="roster"),
    path("awards/", annual_awards, name="annual-awards"),
    path("calendar/", calendar, name="calendar"),
    path("register/", Register.as_view(), name="register"),
    path("profile/<int:pk>/", Profile.as_view(), name="profile"),
    path("profile_edit/<int:pk>/", Edit.as_view(), name="profile-edit"),
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
    path(PW_CONFIRM[0], PWConfirm.as_view(template_name=PW_CONFIRM[1]), name=PW_CONFIRM[2]),
    path(PW_COMPLETE[0], PWComplete.as_view(template_name=PW_COMPLETE[1]), name=PW_COMPLETE[2]),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
