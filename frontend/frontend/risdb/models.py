from django.db import models

class Consultation(models.Model):
    class Meta:
        managed = False
        abstract = False
        db_table = 'consultations'

    id = models.UUIDField(primary_key=True)
    consultation_id = models.IntegerField()
    name = models.TextField()
    topic = models.TextField()
    type = models.TextField()
    text = models.TextField()


class Document(models.Model):
    class Meta:
        managed = False
        abstract = False
        db_table = 'documents'

    id = models.UUIDField(primary_key=True)
    document_id = models.IntegerField()
    file_name = models.TextField()
    content_type = models.TextField()
    content_binary = models.BinaryField()
    size = models.IntegerField()
    author = models.TextField()
    creation_date = models.DateTimeField()
    last_modified = models.DateTimeField()
    last_saved = models.DateTimeField()
    content_text = models.TextField()
    content_text_ocr = models.TextField()
    consultations = models.ManyToManyField(Consultation, through="DocumentConsulation", related_name="document_id")

class DocumentConsulation(models.Model):
    class Meta:
        managed = False
        abstract = False
        db_table = 'document_consultation'

    document = models.ForeignKey(Document, on_delete=models.RESTRICT)
    consultation = models.ForeignKey(Consultation, on_delete=models.RESTRICT)
