from django.db import models
from api.models.user import User


class Parameter(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "parameter"

    def __str__(self):
        return f"{self.id}"
