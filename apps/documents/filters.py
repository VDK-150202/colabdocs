import django_filters
from .models import AuditLog, Document


class AuditLogFilter(django_filters.FilterSet):
    timestamp_after = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    timestamp_before = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ["action", "model_name", "actor", "timestamp_after", "timestamp_before"]


class DocumentFilter(django_filters.FilterSet):

    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Document
        fields = ["workspace", "status", "created_by", "created_after", "created_before"]
