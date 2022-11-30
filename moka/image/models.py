from typing import Any
from uuid import uuid4

from django.db import models
from image.gateway.cloudflare.gateway import CloudflareImagesGateway
from image.gateway.google.gateway import GoogleCloudStorageGateway


class Storage(models.TextChoices):
    CLOUDFLARE_IMAGES = "CLOUDFLARE_IMAGES"
    GOOGLE_CLOUD_STORAGE = "GOOGLE_CLOUD_STORAGE"


def generate_blob_name_v1():
    return str(uuid4())


class Image(models.Model):
    class ImageStatus(models.TextChoices):
        PUBLIC = "PUBLIC"
        DRAFT = "DRAFT"
        REMOVED = "REMOVED"

    status = models.CharField(
        choices=ImageStatus.choices,
        null=False,
        max_length=10,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    external_id = models.CharField(max_length=200, null=False, unique=True)
    storage = models.CharField(
        choices=Storage.choices,
        null=False,
        max_length=100,
    )

    class Meta:
        abstract = True

    @property
    def signed_cookie(self):
        if self.storage == Storage.CLOUDFLARE_IMAGES:
            return CloudflareImagesGateway().get_view_url(
                external_id=self.external_id,
                variant_name="public",
            )
        elif self.storage == Storage.GOOGLE_CLOUD_STORAGE:
            return GoogleCloudStorageGateway().get_view_url(
                external_id=self.external_id,
            )
        else:
            return None


class Thumbnail(Image):
    owner = models.ForeignKey(
        "moka_profile.MokaProfile",
        null=False,
        on_delete=models.CASCADE,
        related_name="owning_thumbnails",
        related_query_name="owning_thumbnail",
    )

    @staticmethod
    def get_new_draft_image_and_signed_upload_url(
        storage: Storage, owner: Any  # MokaProfile
    ):
        if storage == Storage.CLOUDFLARE_IMAGES:
            (
                cf_image_id,
                signed_upload_url,
            ) = CloudflareImagesGateway().get_external_image_id_and_upload_url()
            new_draft_image = Thumbnail.objects.create(
                status=Image.ImageStatus.DRAFT,
                external_id=cf_image_id,
                storage=storage,
                owner=owner,
            )
            return new_draft_image, signed_upload_url
        elif storage == Storage.GOOGLE_CLOUD_STORAGE:
            new_draft_image = Thumbnail.objects.create(
                status=Image.ImageStatus.DRAFT,
                external_id=generate_blob_name_v1(),
                storage=storage,
                owner=owner,
            )
            signed_upload_url = (
                GoogleCloudStorageGateway().get_upload_url_with_external_id(
                    external_id=new_draft_image.external_id,
                )
            )
            return new_draft_image, signed_upload_url
        else:
            return None


class Page(Image):
    owner = models.ForeignKey(
        "moka_profile.MokaProfile",
        null=False,
        on_delete=models.CASCADE,
        related_name="pages",
        related_query_name="page",
    )

    episode = models.ForeignKey(
        "episode.Episode",
        null=False,
        on_delete=models.CASCADE,
        related_name="pages",
        related_query_name="page",
    )
    order = models.PositiveSmallIntegerField(null=False)

    def generate_blob_name_v1(self):
        return f"{self.owner.id}-{self.episode.id}-{self.id}"

    @staticmethod
    def get_new_draft_image_and_signed_upload_url(
        storage: Storage,
        episode: Any,  # Set as Any type avoid circular import
        owner: Any,  # MokaProfile
    ):
        if storage == Storage.CLOUDFLARE_IMAGES:
            (
                cf_image_id,
                signed_upload_url,
            ) = CloudflareImagesGateway().get_external_image_id_and_upload_url()
            new_draft_image = Page.objects.create(
                status=Image.ImageStatus.DRAFT,
                external_id=cf_image_id,
                storage=storage,
                episode=episode,
                owner=owner,
                order=0,  # Temporarily set as 0
            )
            return new_draft_image, signed_upload_url
        elif storage == Storage.GOOGLE_CLOUD_STORAGE:
            new_draft_image = Page.objects.create(
                status=Image.ImageStatus.DRAFT,
                external_id=generate_blob_name_v1(),
                storage=storage,
                episode=episode,
                owner=owner,
                order=0,  # Temporarily set as 0
            )
            signed_upload_url = (
                GoogleCloudStorageGateway().get_upload_url_with_external_id(
                    external_id=new_draft_image.external_id,
                )
            )
            return new_draft_image, signed_upload_url
        else:
            return None
