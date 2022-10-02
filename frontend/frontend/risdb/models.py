from django.db import models


class Organization(models.Model):
    class Meta:
        managed = False
        abstract = False
        db_table = 'organizations'

    id = models.UUIDField(primary_key=True)
    org_id = models.IntegerField()
    name = models.TextField()


class Meeting(models.Model):
    class Meta:
        managed = False
        abstract = False
        db_table = 'meetings'

    id = models.UUIDField(primary_key=True)
    meeting_id = models.IntegerField()
    title = models.TextField()
    title_short = models.TextField()
    date = models.DateTimeField()
    organization = models.ForeignKey(Organization, on_delete=models.RESTRICT, related_name="meetings")
    documents = models.ManyToManyField("Document", through="DocumentMeeting", related_name="meeting_id")


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


class AgendaItem(models.Model):
    class Meta:
        managed = False
        abstract = False
        db_table = 'agendaitems'

    id = models.UUIDField(primary_key=True)
    agenda_item_id = models.IntegerField()
    title = models.TextField()
    decision = models.TextField()
    vote = models.TextField()
    text = models.TextField()
    consultation = models.ForeignKey(Consultation, on_delete=models.RESTRICT, related_name="agenda_items")
    meeting = models.ForeignKey(Meeting, on_delete=models.RESTRICT, related_name="agenda_items")
    documents = models.ManyToManyField("Document", through="DocumentAgendaItem", related_name="agenda_item_id")

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
    meetings = models.ManyToManyField(Meeting, through="DocumentMeeting", related_name="document_id")
    agenda_items = models.ManyToManyField(AgendaItem, through="DocumentAgendaItem", related_name="document_id")


class DocumentConsulation(models.Model):
    class Meta:
        managed = False
        abstract = False
        db_table = 'document_consultation'

    document = models.ForeignKey(Document, on_delete=models.RESTRICT)
    consultation = models.ForeignKey(Consultation, on_delete=models.RESTRICT)


class DocumentAgendaItem(models.Model):
    class Meta:
        managed = False
        abstract = False
        db_table = 'document_agenda_item'

    document = models.ForeignKey(Document, on_delete=models.RESTRICT)
    agenda_item = models.ForeignKey(AgendaItem, on_delete=models.RESTRICT)


class DocumentMeeting(models.Model):
    class Meta:
        managed = False
        abstract = False
        db_table = 'document_meeting'

    document = models.ForeignKey(Document, on_delete=models.RESTRICT)
    meeting = models.ForeignKey(Meeting, on_delete=models.RESTRICT)