# maunium-stickerpicker - A fast and simple Matrix sticker picker widget.
# Copyright (C) 2024 Lukser
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations
from dataclasses import dataclass
import enum
from io import BytesIO
import gzip
import json
import tempfile
import os
from pathlib import Path
from rlottie_python.rlottie_wrapper import LottieAnimation

from PIL import Image

"""
Other formats:
video/mp4
video/webm
video/ogg
video/quicktime
audio/mp4
audio/webm
audio/aac
audio/mpeg
audio/ogg
audio/wave
audio/wav
audio/x-wav
audio/x-pn-wav
audio/flac
audio/x-flac
"""


class ImageFormat(enum.Enum):
    """
    Image formats supported by Matrix.

    image/jpeg
    image/gif
    image/png
    image/apng
    image/webp
    image/avif

    application/x-tgsticker - TGS
    """

    JPEG = enum.auto()
    GIF = enum.auto()
    PNG = enum.auto()
    APNG = enum.auto()
    WEBP = enum.auto()
    AVIF = enum.auto()
    TGS = enum.auto()
    UNKNOWN = enum.auto()

    @classmethod
    def from_mime_type(cls, mime_type: str) -> ImageFormat:
        match mime_type:
            case "image/png":
                return cls.PNG
            case "application/x-tgsticker":
                return cls.TGS
            case "image/webp":
                return cls.WEBP
            case "image/jpeg":
                return cls.JPEG
            case "image/gif":
                return cls.GIF
            case "image/apng":
                return cls.APNG
            case "image/avif":
                return cls.AVIF
            case _:
                return cls.UNKNOWN

    def to_mime_type(self) -> str:
        match self:
            case ImageFormat.PNG:
                return "image/png"
            case ImageFormat.TGS:
                return "application/x-tgsticker"
            case ImageFormat.WEBP:
                return "image/webp"
            case ImageFormat.JPEG:
                return "image/jpeg"
            case ImageFormat.GIF:
                return "image/gif"
            case ImageFormat.APNG:
                return "image/apng"
            case ImageFormat.AVIF:
                return "image/avif"
            case ImageFormat.UNKNOWN:
                return "image/unknown"

    @classmethod
    def from_extension(cls, extension: str) -> ImageFormat:
        match extension:
            case "png":
                return cls.PNG
            case "tgs":
                return cls.TGS
            case "webp":
                return cls.WEBP
            case "jpg":
                return cls.JPEG
            case "gif":
                return cls.GIF
            case "apng":
                return cls.APNG
            case "avif":
                return cls.AVIF
            case _:
                return cls.UNKNOWN

    def to_extension(self) -> str:
        match self:
            case ImageFormat.PNG:
                return "png"
            case ImageFormat.TGS:
                return "tgs"
            case ImageFormat.WEBP:
                return "webp"
            case ImageFormat.JPEG:
                return "jpg"
            case ImageFormat.GIF:
                return "gif"
            case ImageFormat.APNG:
                return "apng"
            case ImageFormat.AVIF:
                return "avif"
            case ImageFormat.UNKNOWN:
                return "unknown"


@dataclass
class GenericImage:
    data: bytes
    width: int
    height: int
    format: ImageFormat

    @classmethod
    def from_bytes(
        cls, data: bytes, format: ImageFormat = ImageFormat.PNG
    ) -> GenericImage:
        if format == ImageFormat.TGS:
            converted_data = convert_tgs_to_webp(data)
            return cls.from_bytes(converted_data, ImageFormat.WEBP)

        image: Image.Image = Image.open(BytesIO(data)).convert("RGBA")
        new_file = BytesIO()
        image.save(new_file, format=format.to_extension())
        width, height = image.size
        return GenericImage(new_file.getvalue(), width, height, format)

    def to_thumbnail(self) -> GenericImage:
        """Convert image to the size of a sticker thumbnail."""
        width = self.width
        height = self.height
        if self.width > 256 or self.height > 256:
            # Set the width and height to lower values so clients wouldn't show them as huge images
            if self.width > self.height:
                height = int(self.height / (self.width / 256))
                width = 256
            else:
                width = int(self.width / (self.height / 256))
                height = 256
        return GenericImage(self.data, width, height, self.format)

    def __len__(self) -> int:
        return len(self.data)


def convert_tgs_to_webp(data: bytes) -> bytes:
    """
    Convert a TGS (Telegram Sticker) file to WebP format using rlottie.

    Args:
        data: The TGS file data as bytes

    Returns:
        The converted WebP file as bytes
    """
    # Create a temporary directory for the conversion process
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Save the decompressed Lottie JSON
        lottie_path = temp_path / "animation.json"
        lottie_path.write_bytes(data)

        # Load the animation using rlottie
        animation = LottieAnimation.from_tgs(path=str(lottie_path))
        frame_count = animation.lottie_animation_get_totalframe()
        width, height = animation.lottie_animation_get_size()

        # Create frames using rlottie
        frames: list[Image.Image] = []
        for i in range(frame_count):
            surface = animation.lottie_animation_render(i)
            # Convert surface data to PIL Image
            img = Image.frombytes('RGBA', (width, height), surface)
            frames.append(img)

        # Save as animated WebP
        output = BytesIO()
        if len(frames) > 1:
            # Save as animated WebP if there are multiple frames
            frames[0].save(
                output,
                format='WEBP',
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / animation.lottie_animation_get_framerate()),  # Duration in milliseconds
                loop=0  # Loop forever
            )
        else:
            # Save as static WebP if there's only one frame
            frames[0].save(output, format='WEBP', quality=95)

        return output.getvalue()
