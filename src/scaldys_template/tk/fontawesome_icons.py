"""FontAwesome SVG icon loader for Tkinter.

Converts bundled SVG files into ``tksvg.SvgImage`` objects that can be used
anywhere a ``tkinter.PhotoImage`` is accepted.
"""

import io
from enum import StrEnum
from pathlib import Path

import tksvg
from lxml import etree


_ICONS_DIR = Path(__file__).parent / "assets" / "fa"


class Icons(StrEnum):
    """Names of the bundled FontAwesome SVG icons.

    Values are the bare filename stems (without ``.svg``) stored in
    ``assets/fa/``.  As a ``StrEnum`` each member *is* the string, so
    ``faw.Icons.gear_solid`` can be passed anywhere a plain ``str`` is expected.
    """

    angle_left_solid = "angle-left-solid-full"
    angle_right_solid = "angle-right-solid-full"
    angles_left_solid = "angles-left-solid-full"
    angles_right_solid = "angles-right-solid-full"
    arrow_left_solid = "arrow-left-solid-full"
    arrow_right_solid = "arrow-right-solid-full"
    bars_solid_full = "bars-solid-full"
    chevron_left_solid = "chevron-left-solid-full"
    chevron_right_solid = "chevron-right-solid-full"
    circle_play_solid = "circle-play-solid-full"
    circle_stop_solid = "circle-stop-solid-full"
    check_solid = "check-solid-full"
    cubes_solid = "cubes-solid-full"
    file_lines_regular = "file-lines-regular-full"
    floppy_disk_regular = "floppy-disk-regular-full"
    folder_open_regular = "folder-open-regular-full"
    folder_tree_solid = "folder-tree-solid-full"
    gear_solid = "gear-solid-full"
    play_solid = "play-solid-full"
    square_poll_solid = "square-poll-vertical-solid-full"
    stop_solid = "stop-solid-full"


def icon_to_image(
    name: str,
    fill: str | None = None,
    scale_to_width: int | None = None,
    scale_to_height: int | None = None,
    scale: float = 1,
) -> tksvg.SvgImage:
    """Load a bundled FontAwesome SVG icon and return it as an ``SvgImage``.

    Parameters
    ----------
    name:
        Icon name — use the ``Icons`` enum (e.g. ``Icons.gear_solid``).
        The value must match a file name inside ``assets/fa/``.
    fill:
        Optional fill colour applied to the SVG root element (e.g. ``"#ffffff"``).
    scale_to_width:
        Scale the image to this pixel width, preserving aspect ratio.
    scale_to_height:
        Scale the image to this pixel height, preserving aspect ratio.
    scale:
        Uniform scale factor applied on top of any ``scale_to_*`` setting.

    Returns
    -------
    tksvg.SvgImage
        Ready to use as a ``PhotoImage`` in any Tkinter widget.

    Raises
    ------
    FileNotFoundError
        If ``name`` does not correspond to a file in ``assets/fa/``.
    """
    svg_path = _ICONS_DIR / f"{name}.svg"
    xml_data = svg_path.read_text(encoding="utf-8")
    return svg_to_image(xml_data, fill, scale_to_width, scale_to_height, scale)


def svg_to_image(
    source: str | bytes,
    fill: str | None = None,
    scale_to_width: int | None = None,
    scale_to_height: int | None = None,
    scale: float = 1,
) -> tksvg.SvgImage:
    """Convert SVG source data into a Tkinter-compatible ``SvgImage``.

    Parameters
    ----------
    source:
        SVG XML as a string or bytes.
    fill:
        Optional fill colour applied to the root SVG element.
    scale_to_width:
        Scale to this pixel width while preserving aspect ratio.
    scale_to_height:
        Scale to this pixel height while preserving aspect ratio.
    scale:
        Uniform scale factor.

    Returns
    -------
    tksvg.SvgImage
    """
    source_bytes = source.encode("utf-8") if isinstance(source, str) else source
    root = etree.fromstring(source_bytes)

    if fill is not None:
        root.attrib["fill"] = fill

    buf = io.BytesIO()
    etree.ElementTree(root).write(buf)

    kwargs: dict[str, object] = {"data": buf.getvalue()}
    if scale_to_width:
        kwargs["scaletowidth"] = scale_to_width
    if scale_to_height:
        kwargs["scaletoheight"] = scale_to_height
    if scale != 1:
        kwargs["scale"] = scale

    return tksvg.SvgImage(**kwargs)
