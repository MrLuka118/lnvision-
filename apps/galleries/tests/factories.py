import factory
from factory.django import DjangoModelFactory

from apps.core.tests.factories import StudioFactory
from apps.core.tests.tenancy import register_factory
from apps.galleries.models import Gallery, GallerySection
from apps.photos.models import Photo, UploadSession


class GalleryFactory(DjangoModelFactory):
    class Meta:
        model = Gallery

    studio = factory.SubFactory(StudioFactory)
    title = factory.Sequence(lambda n: f"Galerija {n}")


class GallerySectionFactory(DjangoModelFactory):
    class Meta:
        model = GallerySection

    studio = factory.SubFactory(StudioFactory)
    gallery = factory.SubFactory(GalleryFactory, studio=factory.SelfAttribute("..studio"))
    title = factory.Sequence(lambda n: f"Sekcija {n}")


class PhotoFactory(DjangoModelFactory):
    """A photo record without a real file; for tests that don't touch the pipeline."""

    class Meta:
        model = Photo

    studio = factory.SubFactory(StudioFactory)
    gallery = factory.SubFactory(GalleryFactory, studio=factory.SelfAttribute("..studio"))
    original = factory.django.FileField(filename="IMG_0001.jpg", data=b"not-an-image")
    original_name = "IMG_0001.jpg"
    width = 3000
    height = 2000
    status = Photo.Status.READY
    renditions = factory.LazyFunction(lambda: {"widths": [480, 960], "formats": ["avif", "jpg"]})
    rendition_version = 1


register_factory(Gallery, GalleryFactory)
register_factory(GallerySection, GallerySectionFactory)
register_factory(Photo, PhotoFactory)


class UploadSessionFactory(DjangoModelFactory):
    class Meta:
        model = UploadSession

    studio = factory.SubFactory(StudioFactory)
    gallery = factory.SubFactory(GalleryFactory, studio=factory.SelfAttribute("..studio"))
    filename = "IMG_0001.jpg"
    size_bytes = 1000


register_factory(UploadSession, UploadSessionFactory)
