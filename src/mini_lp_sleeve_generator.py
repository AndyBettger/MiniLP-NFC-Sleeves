from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

MM_PER_INCH = 25.4
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class SleeveConfig:
    cover_size_mm: float = 60.0
    flap_size_mm: float = 8.0
    seal_flap_size_mm: float = 6.0
    guide_margin_mm: float = 5.0
    dpi: int = 300
    pocket_mode: str = "open"  # "open" or "sealed"
    front_mode: str = "crop"  # "crop" or "fit"
    back_mode: str = "crop"  # "crop" or "fit"
    auto_trim: bool = False


@dataclass(frozen=True)
class AlbumArtwork:
    album_folder: Path
    front_path: Path
    back_path: Path | None


def mm_to_points(mm: float) -> float:
    return mm * 72.0 / MM_PER_INCH


def mm_to_px(mm: float, dpi: int) -> int:
    return int(round(mm * dpi / MM_PER_INCH))


def find_case_insensitive_image(folder: Path, stem: str) -> Path | None:
    for path in folder.iterdir():
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
            continue

        if path.stem.lower() == stem.lower():
            return path

    return None


def discover_albums(covers_folder: Path) -> list[AlbumArtwork]:
    albums: list[AlbumArtwork] = []

    for album_folder in sorted(covers_folder.iterdir()):
        if not album_folder.is_dir():
            continue

        front_path = find_case_insensitive_image(album_folder, "front")
        back_path = find_case_insensitive_image(album_folder, "back")

        if front_path is None:
            print(f"Skipping '{album_folder.name}' because no Front image was found.")
            continue

        albums.append(
            AlbumArtwork(
                album_folder=album_folder,
                front_path=front_path,
                back_path=back_path,
            )
        )

    return albums


def album_display_name(album: AlbumArtwork) -> str:
    """Return the user-facing album name from the album folder."""
    return album.album_folder.name


def filter_albums_by_name(
    albums: list[AlbumArtwork], selected_names: list[str] | None
) -> list[AlbumArtwork]:
    """Filter discovered albums by folder/display name, case-insensitively."""
    if not selected_names:
        return albums

    album_lookup = {album_display_name(album).casefold(): album for album in albums}
    selected_albums = []
    missing_names = []

    for selected_name in selected_names:
        album = album_lookup.get(selected_name.casefold())

        if album is None:
            missing_names.append(selected_name)
        else:
            selected_albums.append(album)

    if missing_names:
        print("Album name(s) not found:")
        for missing_name in missing_names:
            print(f" - {missing_name}")

        print("\nAvailable albums:")
        for album in albums:
            print(f" - {album_display_name(album)}")

        raise SystemExit(1)

    return selected_albums


def conservative_auto_trim(
    image: Image.Image, tolerance: int = 12, max_trim_percent: float = 5.0
) -> Image.Image:
    """
    Conservative border trim.

    This only trims when the detected border appears small. It is intentionally cautious
    because some album covers have deliberate borders.
    """
    rgb_image = image.convert("RGB")
    background_colour = rgb_image.getpixel((0, 0))
    background = Image.new("RGB", rgb_image.size, background_colour)

    diff = ImageChops.difference(rgb_image, background)
    diff = diff.convert("L").point(lambda value: 255 if value > tolerance else 0)

    bbox = diff.getbbox()
    if bbox is None:
        return image

    left, top, right, bottom = bbox
    width, height = image.size

    trim_left = left
    trim_top = top
    trim_right = width - right
    trim_bottom = height - bottom

    max_trim_x = width * (max_trim_percent / 100.0)
    max_trim_y = height * (max_trim_percent / 100.0)

    if (
        trim_left > max_trim_x
        or trim_right > max_trim_x
        or trim_top > max_trim_y
        or trim_bottom > max_trim_y
    ):
        return image

    if trim_left == 0 and trim_right == 0 and trim_top == 0 and trim_bottom == 0:
        return image

    return image.crop(bbox)


def make_side_flap_mask(width: int, height: int, inset: int) -> Image.Image:
    """
    Create a mask for a side sealing flap.

    The flap is full-height where it joins the front cover, with angled
    top/bottom corners on the outer edge.
    """
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    polygon = [
        (0, 0),
        (width, inset),
        (width, height - inset),
        (0, height),
    ]

    draw.polygon(polygon, fill=255)
    return mask


def make_flap_mask(width: int, height: int, inset: int, position: str) -> Image.Image:
    """
    Create a mask for a trapezium flap.

    position:
      - "top": narrower outer edge at the top
      - "bottom": narrower outer edge at the bottom
    """
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    if position == "top":
        polygon = [
            (inset, 0),
            (width - inset, 0),
            (width, height),
            (0, height),
        ]
    elif position == "bottom":
        polygon = [
            (0, 0),
            (width, 0),
            (width - inset, height),
            (inset, height),
        ]
    else:
        raise ValueError(f"Unknown flap mask position: {position}")

    draw.polygon(polygon, fill=255)
    return mask


def prepare_square_artwork(
    image_path: Path,
    target_px: int,
    mode: str,
    auto_trim: bool,
) -> Image.Image:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image).convert("RGB")

    if auto_trim:
        image = conservative_auto_trim(image)

    if mode == "crop":
        width, height = image.size
        square_size = min(width, height)

        left = (width - square_size) // 2
        top = (height - square_size) // 2

        image = image.crop((left, top, left + square_size, top + square_size))

    elif mode == "fit":
        fitted = Image.new("RGB", (target_px, target_px), "white")
        image.thumbnail((target_px, target_px), Image.Resampling.LANCZOS)

        left = (target_px - image.width) // 2
        top = (target_px - image.height) // 2
        fitted.paste(image, (left, top))

        return fitted

    else:
        raise ValueError(f"Unknown artwork mode: {mode}")

    return image.resize((target_px, target_px), Image.Resampling.LANCZOS)


def make_placeholder_back(target_px: int, album_name: str) -> Image.Image:
    image = Image.new("RGB", (target_px, target_px), (235, 235, 235))
    draw = ImageDraw.Draw(image)

    text = f"{album_name}\n\nBACK COVER\nMISSING"
    draw.multiline_text(
        (target_px // 2, target_px // 2),
        text,
        fill=(80, 80, 80),
        anchor="mm",
        align="center",
        spacing=8,
    )

    return image


def resize_strip(strip: Image.Image, size: tuple[int, int]) -> Image.Image:
    return strip.resize(size, Image.Resampling.BICUBIC)


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: tuple[int, int, int],
    width: int,
    dash_px: int,
    gap_px: int,
) -> None:
    x1, y1 = start
    x2, y2 = end

    dx = x2 - x1
    dy = y2 - y1
    distance = math.hypot(dx, dy)

    if distance == 0:
        return

    dash_count = int(distance // (dash_px + gap_px)) + 1

    for i in range(dash_count):
        start_distance = i * (dash_px + gap_px)
        end_distance = min(start_distance + dash_px, distance)

        if start_distance >= distance:
            break

        sx = x1 + dx * (start_distance / distance)
        sy = y1 + dy * (start_distance / distance)
        ex = x1 + dx * (end_distance / distance)
        ey = y1 + dy * (end_distance / distance)

        draw.line((sx, sy, ex, ey), fill=fill, width=width)


def draw_template_guides(
    draw: ImageDraw.ImageDraw,
    origin_x: int,
    origin_y: int,
    cover_px: int,
    flap_px: int,
    seal_px: int,
    line_px: int,
    dpi: int,
) -> None:
    """
    Draw solid cut guides and dashed fold guides to match the mini-LP template.

    Rules:
    - Solid marks indicate true cut edges.
    - Dashed marks indicate folds.
    - Where a location could be interpreted as both, prefer the fold mark.
    """
    cut_colour = (0, 0, 0)
    fold_colour = (120, 120, 120)

    mark_len_px = mm_to_px(4.0, dpi)
    mark_gap_px = mm_to_px(0.8, dpi)
    dash_px = mm_to_px(1.5, dpi)
    gap_px = mm_to_px(1.0, dpi)

    x = origin_x
    y = origin_y

    inset = flap_px
    panel_top = y + flap_px
    panel_bottom = panel_top + cover_px
    total_width = cover_px * 2 + seal_px
    total_height = cover_px + flap_px * 2

    back_left = x
    back_right = x + cover_px
    front_left = x + cover_px
    front_right = x + total_width

    seal_inset = min(flap_px, cover_px // 4)
    seal_fold_x = x + cover_px * 2

    # ---------------------------------------------------------------
    # Solid cut edges for the trapezium flaps
    # ---------------------------------------------------------------

    draw.line(
        [
            (back_left, panel_top),
            (back_left + inset, y),
            (back_right - inset, y),
            (back_right, panel_top),
        ],
        fill=cut_colour,
        width=line_px,
    )

    draw.line(
        [
            (back_left, panel_bottom),
            (back_left + inset, y + total_height),
            (back_right - inset, y + total_height),
            (back_right, panel_bottom),
        ],
        fill=cut_colour,
        width=line_px,
    )

    # ---------------------------------------------------------------
    # External solid cut ticks
    # ---------------------------------------------------------------

    def hmark_right(cx: int, cy: int) -> None:
        draw.line(
            (
                cx + mark_gap_px,
                cy,
                cx + mark_gap_px + mark_len_px,
                cy,
            ),
            fill=cut_colour,
            width=line_px,
        )

    def vmark_up(cx: int, cy: int) -> None:
        draw.line(
            (
                cx,
                cy - mark_gap_px - mark_len_px,
                cx,
                cy - mark_gap_px,
            ),
            fill=cut_colour,
            width=line_px,
        )

    def vmark_down(cx: int, cy: int) -> None:
        draw.line(
            (
                cx,
                cy + mark_gap_px,
                cx,
                cy + mark_gap_px + mark_len_px,
            ),
            fill=cut_colour,
            width=line_px,
        )

    # Left-hand cut edge of the back cover body.
    # Only vertical cut ticks are used here, because horizontal cut ticks
    # would visually clash with the top/bottom flap fold marks.
    vmark_up(back_left, panel_top)
    vmark_down(back_left, panel_bottom)

    if seal_px > 0:
        # Sealed mode: draw the trapezium seal flap cut edge.
        # The front-cover side is a fold, so avoid vertical solid cut ticks there.
        seal_outer_top = panel_top + seal_inset
        seal_outer_bottom = panel_bottom - seal_inset

        draw.line(
            [
                (seal_fold_x, panel_top),
                (front_right, seal_outer_top),
                (front_right, seal_outer_bottom),
                (seal_fold_x, panel_bottom),
            ],
            fill=cut_colour,
            width=line_px,
        )

        # These are the front-cover top/bottom edge cut marks.
        # Horizontal only, so they do not make the seal flap fold look like a cut.
        hmark_right(seal_fold_x, panel_top)
        hmark_right(seal_fold_x, panel_bottom)

    else:
        # Open mode: right-hand open edge of the front cover.
        # This is a true cut edge, so show the full L-style external marks.
        hmark_right(front_right, panel_top)
        vmark_up(front_right, panel_top)

        hmark_right(front_right, panel_bottom)
        vmark_down(front_right, panel_bottom)

    # ---------------------------------------------------------------
    # External dashed fold ticks
    # ---------------------------------------------------------------

    def dashed_hmark_left(cx: int, cy: int) -> None:
        draw_dashed_line(
            draw,
            (cx - mark_gap_px - mark_len_px, cy),
            (cx - mark_gap_px, cy),
            fold_colour,
            line_px,
            dash_px,
            gap_px,
        )

    def dashed_vmark_up(cx: int, cy: int) -> None:
        draw_dashed_line(
            draw,
            (cx, cy - mark_gap_px - mark_len_px),
            (cx, cy - mark_gap_px),
            fold_colour,
            line_px,
            dash_px,
            gap_px,
        )

    def dashed_vmark_down(cx: int, cy: int) -> None:
        draw_dashed_line(
            draw,
            (cx, cy + mark_gap_px),
            (cx, cy + mark_gap_px + mark_len_px),
            fold_colour,
            line_px,
            dash_px,
            gap_px,
        )

    # Fold between back and front covers.
    dashed_vmark_up(front_left, panel_top)
    dashed_vmark_down(front_left, panel_bottom)

    # Top and bottom flap folds.
    # These replace the previous cut ticks on the left side of the back cover.
    dashed_hmark_left(back_left, panel_top)
    dashed_hmark_left(back_left, panel_bottom)

    # Optional seal flap fold.
    if seal_px > 0:
        dashed_vmark_up(seal_fold_x, panel_top)
        dashed_vmark_down(seal_fold_x, panel_bottom)


def draw_calibration_marks(pdf: canvas.Canvas) -> None:
    page_width, _ = A4

    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(0.5)
    pdf.setFont("Helvetica", 7)

    # 50 mm calibration line in the top margin.
    x = mm_to_points(103)
    y = mm_to_points(284)

    pdf.line(x, y, x + mm_to_points(50), y)
    pdf.line(x, y - mm_to_points(1.5), x, y + mm_to_points(1.5))
    pdf.line(
        x + mm_to_points(50),
        y - mm_to_points(1.5),
        x + mm_to_points(50),
        y + mm_to_points(1.5),
    )
    pdf.drawCentredString(
        x + mm_to_points(25),
        y + mm_to_points(2),
        "50 mm calibration line",
    )

    # Small 10 mm calibration square in the top-right margin.
    square_x = page_width - mm_to_points(18)
    square_y = mm_to_points(282)

    pdf.rect(square_x, square_y, mm_to_points(10), mm_to_points(10), stroke=1, fill=0)
    pdf.drawCentredString(
        square_x + mm_to_points(5),
        square_y + mm_to_points(11.5),
        "10 mm",
    )


def create_sleeve_image(album: AlbumArtwork, config: SleeveConfig) -> Image.Image:
    cover_px = mm_to_px(config.cover_size_mm, config.dpi)
    flap_px = mm_to_px(config.flap_size_mm, config.dpi)
    guide_margin_px = mm_to_px(config.guide_margin_mm, config.dpi)

    seal_px = (
        mm_to_px(config.seal_flap_size_mm, config.dpi)
        if config.pocket_mode == "sealed"
        else 0
    )

    template_width = cover_px * 2 + seal_px
    template_height = cover_px + flap_px * 2

    total_width = template_width + guide_margin_px * 2
    total_height = template_height + guide_margin_px * 2

    origin_x = guide_margin_px
    origin_y = guide_margin_px

    front = prepare_square_artwork(
        album.front_path,
        target_px=cover_px,
        mode=config.front_mode,
        auto_trim=config.auto_trim,
    )

    if album.back_path is not None:
        back = prepare_square_artwork(
            album.back_path,
            target_px=cover_px,
            mode=config.back_mode,
            auto_trim=config.auto_trim,
        )
    else:
        back = make_placeholder_back(cover_px, album.album_folder.name)

    sleeve = Image.new("RGB", (total_width, total_height), "white")

    back_x = origin_x
    panel_y = origin_y + flap_px

    # Back panel
    sleeve.paste(back, (back_x, panel_y))

    # Trapezium top/bottom flaps using edge-extension from the back cover
    strip_height = max(1, cover_px // 40)
    top_strip = back.crop((0, 0, cover_px, strip_height))
    bottom_strip = back.crop((0, cover_px - strip_height, cover_px, cover_px))

    top_flap = resize_strip(top_strip, (cover_px, flap_px))
    bottom_flap = resize_strip(bottom_strip, (cover_px, flap_px))

    inset = flap_px
    top_mask = make_flap_mask(cover_px, flap_px, inset, "top")
    bottom_mask = make_flap_mask(cover_px, flap_px, inset, "bottom")

    sleeve.paste(top_flap, (origin_x, origin_y), top_mask)
    sleeve.paste(bottom_flap, (origin_x, origin_y + flap_px + cover_px), bottom_mask)

    # Front panel
    front_x = origin_x + cover_px
    sleeve.paste(front, (front_x, panel_y))

    # Optional seal flap, shaped as a side trapezium.
    if seal_px > 0:
        right_strip_width = max(1, cover_px // 40)
        right_strip = front.crop((cover_px - right_strip_width, 0, cover_px, cover_px))
        seal_flap = resize_strip(right_strip, (seal_px, cover_px))

        seal_inset = min(flap_px, cover_px // 4)
        seal_mask = make_side_flap_mask(seal_px, cover_px, seal_inset)

        sleeve.paste(
            seal_flap,
            (origin_x + cover_px * 2, panel_y),
            seal_mask,
        )

    draw = ImageDraw.Draw(sleeve)
    line_px = max(1, mm_to_px(0.18, config.dpi))

    draw_template_guides(
        draw,
        origin_x,
        origin_y,
        cover_px,
        flap_px,
        seal_px,
        line_px,
        config.dpi,
    )

    return sleeve


def image_to_reader(image: Image.Image) -> ImageReader:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def chunked(items: list[AlbumArtwork], size: int) -> Iterable[list[AlbumArtwork]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def create_pdf(
    albums: list[AlbumArtwork], output_path: Path, config: SleeveConfig
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    page_width, page_height = A4

    seal_mm = config.seal_flap_size_mm if config.pocket_mode == "sealed" else 0.0

    sleeve_width_mm = config.cover_size_mm * 2 + seal_mm
    sleeve_height_mm = config.cover_size_mm + config.flap_size_mm * 2

    # The rendered sleeve image includes a guide margin around the physical template.
    rendered_width_mm = sleeve_width_mm + config.guide_margin_mm * 2
    rendered_height_mm = sleeve_height_mm + config.guide_margin_mm * 2

    # Sleeves are rotated 90 degrees on the A4 page.
    placed_width_mm = rendered_height_mm
    placed_height_mm = rendered_width_mm

    placed_width_pt = mm_to_points(placed_width_mm)
    placed_height_pt = mm_to_points(placed_height_mm)

    columns = 2
    rows = 2
    sleeves_per_page = columns * rows

    side_margin_pt = mm_to_points(13)
    top_margin_pt = mm_to_points(18)
    bottom_margin_pt = mm_to_points(6)

    available_width = page_width - side_margin_pt * 2
    available_height = page_height - top_margin_pt - bottom_margin_pt

    x_gap = (available_width - columns * placed_width_pt) / (columns - 1)
    y_gap = (available_height - rows * placed_height_pt) / (rows - 1)

    if x_gap < 0 or y_gap < 0:
        raise ValueError("Sleeve layout does not fit on A4 with the current settings.")

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    pdf.setTitle("Mini LP NFC Sleeves")

    for page_albums in chunked(albums, sleeves_per_page):
        # One-line header to preserve page space.
        pdf.setFont("Helvetica", 7)
        pdf.drawString(
            mm_to_points(8),
            mm_to_points(291),
            (
                "Print at 100% / Actual Size - Do not Fit to Page | "
                f"Sleeve: {config.cover_size_mm:g} mm | "
                f"Pocket: {config.pocket_mode} | "
                f"Flaps: {config.flap_size_mm:g} mm"
            ),
        )

        draw_calibration_marks(pdf)

        for slot_index, album in enumerate(page_albums):
            column = slot_index % columns
            row = slot_index // columns

            x = side_margin_pt + column * (placed_width_pt + x_gap)

            # Row 0 is the top row.
            y = bottom_margin_pt + (rows - 1 - row) * (placed_height_pt + y_gap)

            sleeve_image = create_sleeve_image(album, config)
            rotated = sleeve_image.rotate(90, expand=True)

            pdf.drawImage(
                image_to_reader(rotated),
                x,
                y,
                width=placed_width_pt,
                height=placed_height_pt,
                preserveAspectRatio=False,
                mask="auto",
            )

            pdf.setFont("Helvetica", 6)
            pdf.drawString(x, y - mm_to_points(3), album.album_folder.name[:60])

        pdf.showPage()

    pdf.save()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate A4 printable mini LP-style NFC sleeve PDFs."
    )

    parser.add_argument(
        "--covers",
        type=Path,
        default=Path("Covers"),
        help="Folder containing album subfolders with Front.* and Back.* images.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output") / "mini_lp_sleeves.pdf",
        help="Output PDF path.",
    )
    parser.add_argument(
        "--pocket",
        choices=["open", "sealed"],
        default="open",
        help="Pocket style: open or sealed.",
    )
    parser.add_argument(
        "--cover-size",
        type=float,
        default=60.0,
        help="Finished square cover size in mm.",
    )
    parser.add_argument(
        "--guide-margin",
        type=float,
        default=3.0,
        help="Extra white margin around each sleeve for external cut/fold guide marks.",
    )
    parser.add_argument(
        "--flap-size",
        type=float,
        default=8.0,
        help="Top/bottom glue flap size in mm.",
    )
    parser.add_argument(
        "--seal-flap-size",
        type=float,
        default=6.0,
        help="Opening-edge seal flap size in mm, only used for sealed pocket mode.",
    )
    parser.add_argument(
        "--front-mode",
        choices=["crop", "fit"],
        default="crop",
        help="How to square the front artwork.",
    )
    parser.add_argument(
        "--back-mode",
        choices=["crop", "fit"],
        default="crop",
        help="How to square the back artwork.",
    )
    parser.add_argument(
        "--auto-trim",
        action="store_true",
        help="Conservatively auto-trim small uniform borders before cropping/fitting.",
    )
    parser.add_argument(
        "--max-albums",
        type=int,
        default=None,
        help="Only process the first N albums, useful for testing.",
    )
    parser.add_argument(
        "--album",
        action="append",
        help=(
            "Only generate the named album. "
            "Use the album folder name. Can be used more than once."
        ),
    )
    parser.add_argument(
        "--list-albums",
        action="store_true",
        help="List discovered albums and exit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = SleeveConfig(
        cover_size_mm=args.cover_size,
        flap_size_mm=args.flap_size,
        seal_flap_size_mm=args.seal_flap_size,
        guide_margin_mm=args.guide_margin,
        pocket_mode=args.pocket,
        front_mode=args.front_mode,
        back_mode=args.back_mode,
        auto_trim=args.auto_trim,
    )

    albums = discover_albums(args.covers)

    if args.list_albums:
        print(f"Found {len(albums)} album(s).")
        for album in albums:
            print(f" - {album_display_name(album)}")
        return

    albums = filter_albums_by_name(albums, args.album)

    if args.max_albums is not None:
        albums = albums[: args.max_albums]

    if not albums:
        raise SystemExit(f"No albums found in {args.covers}")

    print(f"Found {len(albums)} album(s).")
    for album in albums:
        print(f" - {album.album_folder.name}")

    create_pdf(albums, args.output, config)

    print(f"\nCreated PDF: {args.output}")


if __name__ == "__main__":
    main()
