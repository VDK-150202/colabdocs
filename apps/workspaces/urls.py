from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkspaceMemberViewSet, WorkspaceViewSet

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")

# Nested member routes: /api/workspaces/{workspace_id}/members/
member_router = DefaultRouter()
member_router.register(r"members", WorkspaceMemberViewSet, basename="workspace-member")

urlpatterns = [
    path("", include(router.urls)),
    path("workspaces/<uuid:workspace_id>/", include(member_router.urls)),
]
