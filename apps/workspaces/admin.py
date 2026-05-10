from django.contrib import admin
from .models import Workspace, WorkspaceMember


class WorkspaceMemberInline(admin.TabularInline):
    model = WorkspaceMember
    extra = 0
    raw_id_fields = ["user"]


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "owner", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    inlines = [WorkspaceMemberInline]


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = ["workspace", "user", "role", "joined_at"]
    list_filter = ["role"]
    search_fields = ["workspace__name", "user__username"]
