import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create development superuser if it doesn't exist"

    def handle(self, *args, **options):
        email = os.getenv("DJANGO_ADMIN_EMAIL")
        username = os.getenv("DJANGO_ADMIN_USER")
        password = os.getenv("DJANGO_ADMIN_PASSWORD")

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" already exists')
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created superuser "{username}" with password "{password}"'
            )
        )
