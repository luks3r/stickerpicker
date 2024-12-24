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
from functools import partial
import os.path
import json

from . import matrix

open_utf8 = partial(open, encoding="UTF-8")


def add_to_index(name: str, output_dir: str) -> None:
    index_path = os.path.join(output_dir, "index.json")

    # Load existing index data or initialize a new structure
    index_data: dict = load_index_data(index_path)

    if "homeserver_url" not in index_data and matrix.homeserver_url:
        index_data["homeserver_url"] = matrix.homeserver_url

    # Add name to packs if not already present
    add_name_to_packs(index_data, name, index_path)


def load_index_data(index_path: str) -> dict:
    try:
        with open_utf8(index_path) as index_file:
            return json.load(index_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"packs": []}


def add_name_to_packs(index_data: dict, name: str, index_path: str) -> None:
    if name not in index_data["packs"]:
        index_data["packs"].append(name)
        with open_utf8(index_path, "w") as index_file:
            json.dump(index_data, index_file, indent="  ")
        print(f"Added {name} to {index_path}")


def make_sticker(
    mxc: str,
    width: int,
    height: int,
    size: int,
    body: str = "",
    mimetype: str = "image/png",
) -> matrix.StickerInfo:
    return {
        "id": f"scalar-{mxc.split('/')[-1]}",
        "body": body,
        "url": mxc,
        "info": {
            "w": width,
            "h": height,
            "size": size,
            "mimetype": mimetype,
            # Element iOS compatibility hack
            "thumbnail_url": mxc,
            "thumbnail_info": {
                "w": width,
                "h": height,
                "size": size,
                "mimetype": mimetype,
            },
        },
        "msgtype": "m.sticker",
    }
