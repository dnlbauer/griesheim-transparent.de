from django.db import models


class Query(models.Model):
    class Meta:
        db_table = "queries"

    date = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=1000, null=True)
    query = models.CharField(max_length=1000)
    organization = models.CharField(max_length=1000, null=True)
    doc_type = models.CharField(max_length=1000, null=True)
    sort = models.CharField(max_length=1000, null=True)
    page = models.IntegerField(null=True)
    num_results = models.IntegerField(null=True)
    query_time = models.IntegerField(null=True)

    def __str__(self) -> str:
        return f"{self.date} - {self.query}"
