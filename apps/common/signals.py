from django.db.models.signals import post_save
from django.dispatch import receiver


def register_signals():

    from documents.models import AuditLog, Document  # deferred import avoids circular refs

    @receiver(post_save, sender=Document)
    def document_post_save(sender, instance, created, **kwargs):
        action = AuditLog.Action.CREATED if created else AuditLog.Action.UPDATED

        # Determine the actor: last_edited_by on updates, created_by on creates
        actor = instance.created_by if created else (instance.last_edited_by or instance.created_by)

        description = (
            f"Document '{instance.title}' was {action} "
            f"in workspace '{instance.workspace.name}'."
        )

        AuditLog.objects.create(
            actor=actor,
            action=action,
            model_name="Document",
            object_id=str(instance.pk),
            description=description,
            metadata={
                "title": instance.title,
                "status": instance.status,
                "workspace_id": str(instance.workspace_id),
            },
        )
