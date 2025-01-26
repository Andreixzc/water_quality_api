from django.db import models
from api.models.reservoir import Reservoir
from api.models.user import User


class ReservoirUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reservoir = models.ForeignKey(
        Reservoir, on_delete=models.CASCADE, blank=False, null=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reservoir_user"
        unique_together = ["user", "reservoir"]

    def __str__(self):
        return f"{self.id}"
