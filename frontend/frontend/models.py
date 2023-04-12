from django.db import models


class Query(models.Model):
    class Meta:
        db_table = "queries"

    query = models.CharField(max_length=1000)
    date = models.DateTimeField(auto_now_add=True)
