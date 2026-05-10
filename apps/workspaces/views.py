from django.db import transaction
from django.db.models import Count
from django.utils.text import slugify
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Workspace, WorkspaceMember
from .serializers import (
    WorkspaceListSerializer,
    WorkspaceMemberSerializer,
    WorkspaceSerializer,
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    """

    CRUD for Workspaces.
    POST /api/workspaces/           # to create workspace
    GET  /api/workspaces/           # list  member_count
    GET  /api/workspaces/{id}/      # detail
    PATCH/PUT /api/workspaces/{id}/     # update
    DELETE /api/workspaces/{id}/        # destroy the workspace
    GET  /api/workspaces/{id}/stats/    # get aggregate stats

    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return (
            Workspace.objects.filter(members__user=self.request.user)
            .select_related("owner")
            .prefetch_related("members__user")
            .annotate(member_count=Count("members", distinct=True))
            .distinct()
        )

    def get_serializer_class(self):
        if self.action == "list":
            return WorkspaceListSerializer
        return WorkspaceSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        """
        1. Creates the Workspace.
        2. Add the creator as an Admin member.
        """
        try:   
            workspace = serializer.save(
                owner=self.request.user,
                slug=slugify(serializer.validated_data["name"]),
            )
            
            WorkspaceMember.objects.create(
                workspace=workspace,
                user=self.request.user,
                role=WorkspaceMember.Role.ADMIN,
            )
        except Exception as e:

            raise ValidationError({
            "detail": "Could not create workspace. All changes have been rolled back.",
            "error": str(e)
        })


    @action(detail=True, methods=["get"], url_path="stats")
    def stats(self, request, id=None):

        workspace = self.get_object()

        from apps.documents.models import Document

        doc_stats = Document.objects.filter(workspace=workspace).aggregate(
            total_documents=Count("id"),
        )
        member_by_role = (
            WorkspaceMember.objects.filter(workspace=workspace)
            .values("role")
            .annotate(count=Count("id"))
        )

        return Response(
            {
                "workspace_id": str(workspace.id),
                "workspace_name": workspace.name,
                "total_members": workspace.members.count(),
                "members_by_role": list(member_by_role),
                **doc_stats,
            }
        )


class WorkspaceMemberViewSet(viewsets.ModelViewSet):

    serializer_class = WorkspaceMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def _get_workspace(self):
        return Workspace.objects.get(id=self.kwargs["workspace_id"])

    def get_queryset(self):
        return (
            WorkspaceMember.objects.filter(workspace_id=self.kwargs["workspace_id"])
            .select_related("user", "workspace")
        )

    def perform_create(self, serializer):
        workspace = self._get_workspace()
        serializer.save(workspace=workspace)
