# maunium-stickerpicker - A fast and simple Matrix sticker picker widget.
# Copyright (C) 2020 Tulir Asokan
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
import argparse
import asyncio
import json
import mimetypes
import os.path
import string
from hashlib import sha256
from typing import Dict, Optional
from .lib.image import GenericImage, ImageFormat

try:
    import magic
except ImportError:
    print("[Warning] Magic is not installed, using file extensions to guess mime types")
    magic = None

from .lib import matrix, util


def convert_name(name: str) -> str:
    name_translate = {
        ord(" "): ord("_"),
    }
    allowed_chars = string.ascii_letters + string.digits + "_-/.#"
    return "".join(
        filter(lambda char: char in allowed_chars, name.translate(name_translate))
    )


async def upload_sticker(
    file: str, directory: str, old_stickers: Dict[str, matrix.StickerInfo]
) -> Optional[matrix.StickerInfo]:
    if file.startswith("."):
        return None
    path = os.path.join(directory, file)
    if not os.path.isfile(path):
        return None

    if magic:
        mime = magic.from_file(path, mime=True)
    else:
        mime, _ = mimetypes.guess_type(file)
    if not mime or not mime.startswith("image/"):
        return None

    print(f"Processing {file}", end="", flush=True)
    try:
        with open(path, "rb") as image_file:
            image_data = image_file.read()
    except Exception as e:
        print(f"... failed to read file: {e}")
        return None
    name = os.path.splitext(file)[0]

    # If the name starts with "number-", remove the prefix
    name_split = name.split("-", 1)
    if len(name_split) == 2 and name_split[0].isdecimal():
        name = name_split[1]

    sticker_id = f"sha256:{sha256(image_data).hexdigest()}"
    print(".", end="", flush=True)
    if sticker_id in old_stickers:
        sticker = {
            **old_stickers[sticker_id],
            "body": name,
        }
        print(".. using existing upload")
    else:
        image_format = ImageFormat.from_mime_type(mime)
        generic_image = GenericImage.from_bytes(image_data, image_format)

        print(".", end="", flush=True)
        mxc = await matrix.upload(
            generic_image.data,
            image_format.to_mime_type(),
            f"{file}.{image_format.to_extension()}",
        )
        print(".", end="", flush=True)
        sticker: matrix.StickerInfo = util.make_sticker(
            mxc,
            generic_image.width,
            generic_image.height,
            len(generic_image.data),
            name,
        )
        sticker["id"] = sticker_id
        print(" uploaded", flush=True)
    return sticker


async def main(args: argparse.Namespace) -> None:
    await matrix.load_config(args.config)

    dirname = os.path.basename(os.path.abspath(args.path))
    meta_path = os.path.join(args.path, "pack.json")
    try:
        with util.open_utf8(meta_path) as pack_file:
            pack = json.load(pack_file)
            print(f"Loaded existing pack meta from {meta_path}")
    except FileNotFoundError:
        pack = {
            "title": args.title or dirname,
            "id": args.id or convert_name(dirname),
            "stickers": [],
        }
        old_stickers = {}
    else:
        old_stickers = {sticker["id"]: sticker for sticker in pack["stickers"]}
        pack["stickers"] = []

    for file in sorted(os.listdir(args.path)):
        sticker = await upload_sticker(file, args.path, old_stickers=old_stickers)
        if sticker:
            pack["stickers"].append(sticker)

    with util.open_utf8(meta_path, "w") as pack_file:
        json.dump(pack, pack_file)
    print(f"Wrote pack to {meta_path}")

    if args.add_to_index:
        picker_file_name = f"{pack['id']}.json"
        picker_pack_path = os.path.join(args.add_to_index, picker_file_name)
        with util.open_utf8(picker_pack_path, "w") as pack_file:
            json.dump(pack, pack_file)
        print(f"Copied pack to {picker_pack_path}")
        util.add_to_index(picker_file_name, args.add_to_index)


def cmd():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        help="Path to JSON file with Matrix homeserver and access_token",
        type=str,
        default="config.json",
        metavar="file",
    )
    parser.add_argument(
        "--title",
        help="Override the sticker pack displayname",
        type=str,
        metavar="title",
    )
    parser.add_argument(
        "--id", help="Override the sticker pack ID", type=str, metavar="id"
    )
    parser.add_argument(
        "--add-to-index",
        help="Sticker picker pack directory (usually 'web/packs/')",
        type=str,
        metavar="path",
    )
    parser.add_argument("path", help="Path to the sticker pack directory", type=str)

    args = parser.parse_args()
    asyncio.get_event_loop().run_until_complete(main(args))


if __name__ == "__main__":
    cmd()
