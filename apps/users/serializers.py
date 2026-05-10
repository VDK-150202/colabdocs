from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    token = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "password", "token"]
        read_only_fields = ["id", "token"]

    def get_token(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        return token.key

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            full_name=validated_data.get("full_name", ""),
        )


class UserLoginSerializer(serializers.Serializer):
    """Validates credentials and returns auth token."""

    email = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        user = authenticate(username=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials. Please try again.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")
        attrs["user"] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Read/update current user's profile."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name", "bio", "avatar_url", "date_joined", "updated_at"]
        read_only_fields = ["id", "email", "date_joined", "updated_at"]


class UserMinimalSerializer(serializers.ModelSerializer):
    """Lightweight representation used inside nested serializers."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name"]
