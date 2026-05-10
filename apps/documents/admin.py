from django.contrib import admin
from .models import AuditLog, Comment, Document, DocumentVersion, Tag


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "workspace", "status", "created_by", "created_at", "updated_at"]
    list_filter = ["status", "workspace"]
    search_fields = ["title", "content"]
    raw_id_fields = ["created_by", "last_edited_by"]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ["document", "version_number", "status", "saved_by", "created_at"]
    list_filter = ["status"]
    raw_id_fields = ["saved_by"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["document", "author", "parent", "is_resolved", "created_at"]
    list_filter = ["is_resolved"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "color", "created_at"]
    search_fields = ["name"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "model_name", "object_id", "actor", "timestamp"]
    list_filter = ["action", "model_name"]
    search_fields = ["object_id", "description"]
    readonly_fields = ["id", "timestamp"]
