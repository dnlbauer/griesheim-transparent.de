from django.db import models


class Organization(models.Model):
    class Meta:
        db_table = 'organizations'

    id = models.AutoField(primary_key=True)
    organization_id = models.IntegerField()
    name = models.TextField()


class Person(models.Model):
    class Meta:
        db_table = "persons"

    id = models.AutoField(primary_key=True)
    person_id = models.IntegerField()
    name = models.TextField()


class Membership(models.Model):
    class Meta:
        db_table = "memberships"

    id = models.AutoField(primary_key=True)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)


class Document(models.Model):
    class Meta:
        db_table = 'documents'

    id = models.AutoField(primary_key=True)
    document_id = models.IntegerField()
    file_name = models.TextField()
    content_type = models.TextField()
    content_binary = models.BinaryField()
    size = models.IntegerField()
    title = models.TextField()


class Consultation(models.Model):
    class Meta:
        db_table = 'consultations'

    id = models.AutoField(primary_key=True)
    consultation_id = models.IntegerField()
    name = models.TextField()
    topic = models.TextField()
    type = models.TextField()
    text = models.TextField()
    documents = models.ManyToManyField(Document)


class Meeting(models.Model):
    class Meta:
        db_table = 'meetings'

    id = models.AutoField(primary_key=True)
    meeting_id = models.IntegerField()
    title = models.TextField()
    title_short = models.TextField()
    date = models.DateTimeField()
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    documents = models.ManyToManyField(Document)
    consultations = models.ManyToManyField(Consultation)


class AgendaItem(models.Model):
    class Meta:
        db_table = 'agendaitems'

    id = models.AutoField(primary_key=True)
    agenda_item_id = models.IntegerField()
    title = models.TextField()
    decision = models.TextField()
    vote = models.TextField()
    text = models.TextField()
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE)
    documents = models.ManyToManyField(Document)
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE)
