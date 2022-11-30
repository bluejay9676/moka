from common.logger import StructuredLogger
from image.models import Page
from ninja import Schema

logger = StructuredLogger(__name__)


class PageIdSchema(Schema):
    id: int


class NewPageInputSchema(Schema):
    episode_id: int


class DeletePageInputSchema(Schema):
    id: int


class DeleteThumbnailInputSchema(Schema):
    id: int


class PageSchema(Schema):
    id: str
    signed_view_url: str
    order: int

    @staticmethod
    def resolve_from_page(obj: Page):
        return {
            "id": str(obj.id),
            "signed_view_url": obj.signed_cookie,
            "order": obj.order,
        }


class NewImageSchema(Schema):
    id: int
    signed_upload_url: str
