"""The Docker image must be able to produce every rendition format the pipeline uses."""

import pytest
import pyvips


@pytest.mark.parametrize("suffix", [".avif", ".jpg", ".webp"])
def test_libvips_encodes_rendition_formats(suffix):
    image = pyvips.Image.black(64, 48, bands=3).linear([1, 1, 1], [180, 120, 60])
    data = image.write_to_buffer(suffix, Q=60)
    decoded = pyvips.Image.new_from_buffer(data, "")
    assert (decoded.width, decoded.height) == (64, 48)


def test_libvips_converts_to_srgb():
    image = (pyvips.Image.black(8, 8, bands=3) + 128).copy(interpretation="srgb")
    assert image.colourspace("srgb").interpretation == "srgb"
