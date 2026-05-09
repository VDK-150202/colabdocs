"""
documents/views.py
ViewSets for Document, Comment, Tag, and AuditLog.

SDE-2 patterns demonstrated:
- @transaction.atomic on create and update (version snapshots).
- select_related / prefetch_related globally in get_queryset.
- @action for /summary/, /versions/, /stats/ endpoints.
- Q objects for cross-field search.
- .annotate() + .aggregate() for aggregated endpoints.
- django-filter for AuditLog range queries.
"""

from django.db import transaction
from django.db.models import Avg, Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import AuditLogFilter, DocumentFilter
from .models import AuditLog, Comment, Document, DocumentVersion, Tag
from .serializers import (
    AuditLogSerializer,
    CommentSerializer,
    DocumentListSerializer,
    DocumentSerializer,
    DocumentVersionSerializer,
    TagSerializer,
)


# ---------------------------------------------------------------------------
# Tag ViewSet
# ---------------------------------------------------------------------------

class TagViewSet(viewsets.ModelViewSet):
    """CRUD for Tags inside a workspace."""

    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    search_fields = ["name"]

    def get_queryset(self):
        return Tag.objects.filter(workspace__members__user=self.request.user).distinct()


# ---------------------------------------------------------------------------
# Document ViewSet
# ---------------------------------------------------------------------------

class DocumentViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Documents plus custom actions:
      GET  /api/documents/{id}/versions/  – version history
      GET  /api/documents/{id}/summary/   – AI-style summary placeholder
      GET  /api/documents/stats/          – aggregate stats across workspace
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    filterset_class = DocumentFilter
    search_fields = ["title", "content"]
    ordering_fields = ["created_at", "updated_at", "title"]

    def get_queryset(self):
        """
        Scoped to workspaces the user is a member of.
        Annotated with version_count and comment_count for list serializer.
        Q-object search across title + content.
        """
        qs = (
            Document.objects.filter(workspace__members__user=self.request.user)
            .select_related("workspace", "created_by", "last_edited_by")
            .prefetch_related("versions", "comments", "tags")
            .annotate(
                version_count=Count("versions", distinct=True),
                comment_count=Count("comments", distinct=True),
            )
            .distinct()
        )

        # Q-object free-text search across title AND content
        search = self.request.query_params.get("q")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        return DocumentSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Atomically create Document + first DocumentVersion snapshot.
        If the version insert fails, the document insert is rolled back.
        """
        doc = serializer.save(created_by=self.request.user)
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            title=doc.title,
            content=doc.content,
            status=doc.status,
            saved_by=self.request.user,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        """
        Atomically update Document + append a new DocumentVersion snapshot.
        version_number = MAX(existing) + 1 to keep sequential ordering.
        select_for_update() prevents a race condition on version_number.
        """
        doc = serializer.save(last_edited_by=self.request.user)

        last_version = (
            DocumentVersion.objects.select_for_update()
            .filter(document=doc)
            .order_by("-version_number")
            .first()
        )
        next_version_number = (last_version.version_number + 1) if last_version else 1

        DocumentVersion.objects.create(
            document=doc,
            version_number=next_version_number,
            title=doc.title,
            content=doc.content,
            status=doc.status,
            saved_by=self.request.user,
        )

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, id=None):
        """GET /api/documents/{id}/versions/ – full version history."""
        doc = self.get_object()
        versions = doc.versions.select_related("saved_by").all()
        serializer = DocumentVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, id=None):
        """
        GET /api/documents/{id}/summary/
        Returns a lightweight document summary with aggregated metadata.
        (Placeholder for an AI-generated summary integration.)
        """
        doc = self.get_object()
        version_count = doc.versions.count()
        comment_count = doc.comments.count()
        resolved_count = doc.comments.filter(is_resolved=True).count()

        return Response(
            {
                "document_id": str(doc.id),
                "title": doc.title,
                "status": doc.status,
                "word_count": len(doc.content.split()) if doc.content else 0,
                "character_count": len(doc.content),
                "version_count": version_count,
                "comment_count": comment_count,
                "resolved_comments": resolved_count,
                "open_comments": comment_count - resolved_count,
                "created_by": doc.created_by.username if doc.created_by else None,
                "last_edited_by": doc.last_edited_by.username if doc.last_edited_by else None,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
            }
        )

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """
        GET /api/documents/stats/
        Aggregate statistics across all documents the user can access.
        Uses .aggregate() and .annotate() – no Python-level loops.
        """
        qs = self.get_queryset()

        totals = qs.aggregate(total=Count("id"))
        by_status = list(qs.values("status").annotate(count=Count("id")))
        by_workspace = list(
            qs.values("workspace__name", "workspace__id")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return Response(
            {
                "total_documents": totals["total"],
                "by_status": by_status,
                "top_workspaces": by_workspace,
            }
        )


# ---------------------------------------------------------------------------
# Comment ViewSet
# ---------------------------------------------------------------------------

class CommentViewSet(viewsets.ModelViewSet):
    """
    Comments nested under a document.
    /api/documents/{document_id}/comments/
    """

    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return (
            Comment.objects.filter(document_id=self.kwargs["document_id"])
            .select_related("author", "document", "parent")
            .prefetch_related("replies__author")
        )

    def perform_create(self, serializer):
        doc = Document.objects.get(id=self.kwargs["document_id"])
        serializer.save(document=doc, author=self.request.user)


# ---------------------------------------------------------------------------
# AuditLog ViewSet (read-only)
# ---------------------------------------------------------------------------

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only audit trail.
    Supports django-filter range queries:
      GET /api/audit-logs/?timestamp_after=2024-01-01&timestamp_before=2024-12-31
      GET /api/audit-logs/?action=created&model_name=Document
    """

    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = AuditLogFilter
    search_fields = ["description", "model_name", "object_id"]
    ordering_fields = ["timestamp"]
    lookup_field = "id"

    def get_queryset(self):
        return AuditLog.objects.select_related("actor").all()
