from __future__ import annotations

from PIL import Image

from services.image_utils import preprocess_image


def test_preprocess_image_outputs_three_channel_224_tensor():
    image = Image.new("RGB", (320, 240), color=(120, 80, 40))

    tensor = preprocess_image(image)

    assert tuple(tensor.shape) == (3, 224, 224)
