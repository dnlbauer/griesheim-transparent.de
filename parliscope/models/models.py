from django.db import models


class BaseModel(models.Model):
    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)


class Organization(BaseModel):
    class Meta:
        db_table = "organizations"

    id = models.AutoField(primary_key=True)
    organization_id = models.IntegerField(unique=True, null=True)
    name = models.TextField(unique=True)


class Person(BaseModel):
    class Meta:
        db_table = "persons"
        unique_together = ("name", "person_id")

    id = models.AutoField(primary_key=True)
    person_id = models.IntegerField(
        null=True
    )  # not all persons are linked person objects?
    name = models.TextField(unique=True)


class Membership(BaseModel):
    class Meta:
        db_table = "memberships"
        unique_together = ("person_id", "organization_id")

    id = models.AutoField(primary_key=True)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, db_constraint=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, db_constraint=False
    )
    from_date = models.DateTimeField(null=True)
    to_date = models.DateTimeField(null=True)


class Document(BaseModel):
    class Meta:
        db_table = "documents"

    id = models.AutoField(primary_key=True)
    document_id = models.IntegerField(unique=True)
    file_name = models.TextField(null=True)
    uri = models.TextField(unique=True)
    content_type = models.TextField(null=True)
    size = models.IntegerField()
    title = models.TextField(null=True)
    checksum = models.TextField()


class Consultation(BaseModel):
    class Meta:
        db_table = "consultations"

    id = models.AutoField(primary_key=True)
    consultation_id = models.IntegerField(unique=True)
    name = models.TextField()
    topic = models.TextField()
    type = models.TextField()
    text = models.TextField(null=True)
    documents = models.ManyToManyField(Document)


class Meeting(BaseModel):
    class Meta:
        db_table = "meetings"

    id = models.AutoField(primary_key=True)
    meeting_id = models.IntegerField(unique=True)
    title = models.TextField()
    title_short = models.TextField()
    date = models.DateTimeField()
    organization = models.ForeignKey(
        Organization, null=True, on_delete=models.CASCADE, db_constraint=False
    )
    documents = models.ManyToManyField(Document, db_constraint=False)
    consultations = models.ManyToManyField(Consultation, db_constraint=False)


class AgendaItem(BaseModel):
    class Meta:
        db_table = "agendaitems"

    id = models.AutoField(primary_key=True)
    agenda_item_id = models.IntegerField(unique=True)
    title = models.TextField()
    decision = models.TextField(null=True)
    vote = models.TextField(null=True)
    text = models.TextField(null=True)
    meeting = models.ForeignKey(
        Meeting, null=True, on_delete=models.CASCADE, db_constraint=False
    )
    documents = models.ManyToManyField(Document)
    consultation = models.ForeignKey(
        Consultation, null=True, on_delete=models.CASCADE, db_constraint=False
    )
