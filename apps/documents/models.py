import uuid
from django.conf import settings
from django.db import models
from workspaces.models import Workspace


class Tag(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default="#3B82F6", help_text="Hex colour code")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_tag"
        unique_together = [("workspace", "name")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class Document(models.Model):

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"
        UNDER_REVIEW = "under_review", "Under Review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    tags = models.ManyToManyField(Tag, blank=True, related_name="documents")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_documents",
    )
    last_edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edited_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents_document"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return self.title


class DocumentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True)
    status = models.CharField(max_length=20)
    saved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="saved_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_documentversion"
        # Enforce uniqueness of version numbers per document
        unique_together = [("document", "version_number")]
        ordering = ["-version_number"]
        indexes = [
            models.Index(fields=["document", "version_number"]),
        ]

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class Comment(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="comments",
    )
    # Threaded replies: top-level comments have parent=None
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    body = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents_comment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["document", "parent"]),
        ]

    def __str__(self):
        return f"Comment by {self.author} on {self.document}"


class AuditLog(models.Model):

    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    # Generic reference: store model name + PK as strings
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=36)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_auditlog"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["actor"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"[{self.action}] {self.model_name}:{self.object_id} by {self.actor}"
