from django.utils.text import slugify
from rest_framework import serializers

from users.serializers import UserMinimalSerializer
from .models import Workspace, WorkspaceMember


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user_detail = UserMinimalSerializer(source="user", read_only=True)
    user = serializers.UUIDField(write_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ["id", "workspace", "user", "user_detail", "role", "joined_at"]
        read_only_fields = ["id", "joined_at"]

    def validate(self, attrs):
        """
        Prevent duplicate memberships.
        UniqueConstraint at the DB level is the last line of defence;
        we raise a friendly error here first.
        """
        workspace = attrs.get("workspace") or self.instance.workspace
        user_id = attrs.get("user")
        if user_id and WorkspaceMember.objects.filter(workspace=workspace, user_id=user_id).exists():
            raise serializers.ValidationError(
                {"user": "This user is already a member of the workspace."}
            )
        return attrs

    def create(self, validated_data):
        from users.models import User
        user_id = validated_data.pop("user")
        user = User.objects.get(pk=user_id)
        return WorkspaceMember.objects.create(user=user, **validated_data)


class WorkspaceSerializer(serializers.ModelSerializer):
    owner_detail = UserMinimalSerializer(source="owner", read_only=True)
    member_count = serializers.SerializerMethodField()
    members = WorkspaceMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Workspace
        fields = [
            "id", "name", "slug", "description",
            "owner", "owner_detail", "is_active",
            "member_count", "members",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]

    def get_member_count(self, obj):
        # Uses prefetch cache – no extra query
        return obj.members.count()

    def validate_name(self, value):
        slug = slugify(value)
        qs = Workspace.objects.filter(slug=slug)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A workspace with this name already exists.")
        return value


class WorkspaceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    owner_detail = UserMinimalSerializer(source="owner", read_only=True)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "is_active", "owner_detail", "member_count", "created_at"]
