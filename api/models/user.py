from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    cpf = models.CharField(max_length=11, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "cpf"]

    class Meta:
        db_table = "user"

    def __str__(self):
        return f"{self.id}"
