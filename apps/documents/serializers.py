
from rest_framework import serializers

from users.serializers import UserMinimalSerializer
from .models import AuditLog, Comment, Document, DocumentVersion, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "workspace", "name", "color", "created_at"]
        read_only_fields = ["id", "created_at"]



class DocumentVersionSerializer(serializers.ModelSerializer):
    saved_by_detail = UserMinimalSerializer(source="saved_by", read_only=True)

    class Meta:
        model = DocumentVersion
        fields = [
            "id", "document", "version_number", "title", "content",
            "status", "saved_by", "saved_by_detail", "created_at",
        ]
        read_only_fields = ["id", "document", "version_number", "created_at"]


class CommentReplySerializer(serializers.ModelSerializer):
    """Nested serializer for direct replies (one level deep)."""
    author_detail = UserMinimalSerializer(source="author", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "author_detail", "body", "is_resolved", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CommentSerializer(serializers.ModelSerializer):
    author_detail = UserMinimalSerializer(source="author", read_only=True)
    replies = CommentReplySerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id", "document", "author", "author_detail",
            "parent", "body", "is_resolved",
            "replies", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        Ensure replies reference a comment on the same document,
        and prevent multi-level nesting (parent must be a top-level comment).
        """
        parent = attrs.get("parent")
        document = attrs.get("document") or (self.instance.document if self.instance else None)

        if parent:
            if parent.document_id != (document.id if document else None):
                raise serializers.ValidationError(
                    {"parent": "Parent comment must belong to the same document."}
                )
            if parent.parent is not None:
                raise serializers.ValidationError(
                    {"parent": "Cannot reply to a reply. Only one level of nesting is supported."}
                )
        return attrs

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)



class DocumentSerializer(serializers.ModelSerializer):
    created_by_detail = UserMinimalSerializer(source="created_by", read_only=True)
    last_edited_by_detail = UserMinimalSerializer(source="last_edited_by", read_only=True)
    tags_detail = TagSerializer(source="tags", many=True, read_only=True)
    version_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "workspace", "title", "content", "status",
            "tags", "tags_detail",
            "created_by", "created_by_detail",
            "last_edited_by", "last_edited_by_detail",
            "version_count", "comment_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "last_edited_by", "created_at", "updated_at"]

    def get_version_count(self, obj):
        # Served from prefetch cache — zero extra queries
        return obj.versions.count()

    def get_comment_count(self, obj):
        return obj.comments.count()

    def validate(self, attrs):
        """
        Business rule: a document cannot be moved back from 'archived'
        to 'draft' directly; it must go through 'under_review' first.
        """
        if self.instance:
            current_status = self.instance.status
            new_status = attrs.get("status", current_status)
            if current_status == Document.Status.ARCHIVED and new_status == Document.Status.DRAFT:
                raise serializers.ValidationError(
                    {"status": "An archived document must be set to 'under_review' before returning to draft."}
                )
        return attrs


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight representation for list endpoints."""

    created_by_detail = UserMinimalSerializer(source="created_by", read_only=True)
    version_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "workspace", "title", "status",
            "created_by_detail", "version_count", "comment_count",
            "created_at", "updated_at",
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_detail = UserMinimalSerializer(source="actor", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "actor", "actor_detail", "action",
            "model_name", "object_id", "description",
            "metadata", "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]