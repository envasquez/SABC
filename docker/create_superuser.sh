#!/bin/sh

cat <<EOF | python3 sabc/manage.py shell
import sys
from django.contrib.auth.models import User
if len(User.objects.all()) == 0:
    sys.exit(1)
EOF
if [ $? -eq 1 ]; then
    python3 sabc/manage.py createsuperuser --noinput --email sabc.site@gmail.com
fi
