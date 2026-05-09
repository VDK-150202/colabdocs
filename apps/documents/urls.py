"""documents/urls.py"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet, CommentViewSet, DocumentViewSet, TagViewSet

router = DefaultRouter()
router.register(r"documents", DocumentViewSet, basename="document")
router.register(r"tags", TagViewSet, basename="tag")
router.register(r"audit-logs", AuditLogViewSet, basename="auditlog")

# Nested comments: /api/documents/{document_id}/comments/
comment_router = DefaultRouter()
comment_router.register(r"comments", CommentViewSet, basename="document-comment")

urlpatterns = [
    path("", include(router.urls)),
    path("documents/<uuid:document_id>/", include(comment_router.urls)),
]
