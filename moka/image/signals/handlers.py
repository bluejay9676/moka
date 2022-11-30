from common.logger import StructuredLogger
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from episode.models import Episode
from image.gateway.cloudflare.gateway import CloudflareImagesGateway
from image.gateway.google.gateway import GoogleCloudStorageGateway
from image.models import Image, Page, Storage, Thumbnail
from moka_profile.models import MokaProfile
from series.models import Series

logger = StructuredLogger(__name__)


@receiver(pre_delete, sender=Thumbnail)
@receiver(pre_delete, sender=Page)
def remove_image_source(sender, instance, **kwargs):
    if instance.storage == Storage.CLOUDFLARE_IMAGES:
        try:
            CloudflareImagesGateway().delete(
                external_id=instance.external_id,
            )
        except Exception as e:
            logger.exception(
                event_name="CLOUDFLARE_IMAGES_DELETE_FAIL",
                msg=str(e),
                image_id=instance.id,
                cf_image_id=instance.external_id,
            )
    elif instance.storage == Storage.GOOGLE_CLOUD_STORAGE:
        try:
            GoogleCloudStorageGateway().delete(
                external_id=instance.external_id,
            )
        except Exception as e:
            logger.exception(
                event_name="GCS_DELETE_FAIL",
                msg=str(e),
                image_id=instance.id,
                blob_name=instance.external_id,
            )


def remove_old_thumbnail_if_exists(previous, instance):
    if previous.thumbnail and previous.thumbnail != instance.thumbnail:
        previous.thumbnail.status = Image.ImageStatus.REMOVED
        previous.thumbnail.save()


@receiver(pre_save, sender=Episode)
def remove_old_episode_thumbnail(sender, instance, update_fields, **kwargs):
    if instance.id is None:
        return
    previous = Episode.objects.get(id=instance.id)
    remove_old_thumbnail_if_exists(previous, instance)


@receiver(pre_save, sender=Series)
def remove_old_series_thumbnail(sender, instance, update_fields, **kwargs):
    if instance.id is None:
        return
    previous = Series.objects.get(id=instance.id)
    remove_old_thumbnail_if_exists(previous, instance)


@receiver(pre_save, sender=MokaProfile)
def remove_old_profile_thumbnail(sender, instance, update_fields, **kwargs):
    if instance.id is None:
        return
    previous = MokaProfile.objects.get(id=instance.id)
    remove_old_thumbnail_if_exists(previous, instance)


@receiver(pre_delete, sender=Episode)
def delete_pages(sender, instance, **kwargs):
    pages = instance.pages.all()
    for page in pages:
        page.status = Image.ImageStatus.REMOVED
    Page.objects.bulk_update(pages, ["status"])


@receiver(pre_delete, sender=Episode)
@receiver(pre_delete, sender=Series)
@receiver(pre_delete, sender=MokaProfile)
def delete_thumbnail(sender, instance, **kwargs):
    if instance.thumbnail:
        instance.thumbnail.status = Image.ImageStatus.REMOVED
        instance.thumbnail.save()
