from abc import abstractmethod


class ImageStorageGateway:
    """
    Interface for connecting to image storage providers
    such as Google Cloud Storage or Cloudflare Images
    """

    @abstractmethod
    def get_external_image_id_and_upload_url(self):
        raise NotImplementedError

    @abstractmethod
    def get_upload_url_with_external_id(self, external_id: str):
        raise NotImplementedError

    @abstractmethod
    def get_view_url(self, external_id: str, variant_name: str):
        raise NotImplementedError

    @abstractmethod
    def delete(self, external_id: str):
        raise NotImplementedError
