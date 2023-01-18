# -*- coding: utf-8 -*-
from django.contrib import admin
from polls.models import LakePoll, LakeVote

admin.site.register([LakePoll, LakeVote])
