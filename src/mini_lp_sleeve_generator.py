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


def conservative_auto_trim(image: Image.Image, tolerance: int = 12, max_trim_percent: float = 5.0) -> Image.Image:
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


def draw_cut_outline(
    draw: ImageDraw.ImageDraw,
    cover_px: int,
    flap_px: int,
    seal_px: int,
    line_px: int,
) -> None:
    total_width = cover_px * 2 + seal_px
    total_height = cover_px + flap_px * 2

    points = [
        (0, 0),
        (cover_px, 0),
        (cover_px, flap_px),
        (total_width, flap_px),
        (total_width, flap_px + cover_px),
        (cover_px, flap_px + cover_px),
        (cover_px, total_height),
        (0, total_height),
        (0, 0),
    ]

    draw.line(points, fill=(0, 0, 0), width=line_px, joint="curve")


def draw_fold_guides(
    draw: ImageDraw.ImageDraw,
    cover_px: int,
    flap_px: int,
    seal_px: int,
    line_px: int,
    dpi: int,
) -> None:
    fold_colour = (120, 120, 120)
    dash_px = mm_to_px(2.5, dpi)
    gap_px = mm_to_px(1.5, dpi)

    # Fold between back and front covers
    draw_dashed_line(
        draw,
        (cover_px, flap_px),
        (cover_px, flap_px + cover_px),
        fold_colour,
        line_px,
        dash_px,
        gap_px,
    )

    # Back-cover top and bottom glue flap folds
    draw_dashed_line(
        draw,
        (0, flap_px),
        (cover_px, flap_px),
        fold_colour,
        line_px,
        dash_px,
        gap_px,
    )
    draw_dashed_line(
        draw,
        (0, flap_px + cover_px),
        (cover_px, flap_px + cover_px),
        fold_colour,
        line_px,
        dash_px,
        gap_px,
    )

    # Optional sealed-pocket flap fold
    if seal_px > 0:
        draw_dashed_line(
            draw,
            (cover_px * 2, flap_px),
            (cover_px * 2, flap_px + cover_px),
            fold_colour,
            line_px,
            dash_px,
            gap_px,
        )


def create_sleeve_image(album: AlbumArtwork, config: SleeveConfig) -> Image.Image:
    cover_px = mm_to_px(config.cover_size_mm, config.dpi)
    flap_px = mm_to_px(config.flap_size_mm, config.dpi)
    seal_px = (
        mm_to_px(config.seal_flap_size_mm, config.dpi)
        if config.pocket_mode == "sealed"
        else 0
    )

    total_width = cover_px * 2 + seal_px
    total_height = cover_px + flap_px * 2

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

    # Back cover panel
    back_x = 0
    panel_y = flap_px
    sleeve.paste(back, (back_x, panel_y))

    # Back-cover glue flaps use edge-extension from the back cover.
    top_strip = back.crop((0, 0, cover_px, max(1, cover_px // 40)))
    bottom_strip = back.crop((0, cover_px - max(1, cover_px // 40), cover_px, cover_px))

    sleeve.paste(resize_strip(top_strip, (cover_px, flap_px)), (0, 0))
    sleeve.paste(resize_strip(bottom_strip, (cover_px, flap_px)), (0, flap_px + cover_px))

    # Front cover panel
    front_x = cover_px
    sleeve.paste(front, (front_x, panel_y))

    # Optional sealed flap uses edge-extension from the front cover's right edge.
    if seal_px > 0:
        right_strip_width = max(1, cover_px // 40)
        right_strip = front.crop((cover_px - right_strip_width, 0, cover_px, cover_px))
        sleeve.paste(
            resize_strip(right_strip, (seal_px, cover_px)),
            (cover_px * 2, panel_y),
        )

    draw = ImageDraw.Draw(sleeve)

    line_px = max(1, mm_to_px(0.18, config.dpi))

    draw_cut_outline(draw, cover_px, flap_px, seal_px, line_px)
    draw_fold_guides(draw, cover_px, flap_px, seal_px, line_px, config.dpi)

    return sleeve


def image_to_reader(image: Image.Image) -> ImageReader:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def chunked(items: list[AlbumArtwork], size: int) -> Iterable[list[AlbumArtwork]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def draw_calibration_marks(pdf: canvas.Canvas) -> None:
    page_width, _ = A4

    x = mm_to_points(80)
    y = mm_to_points(8)

    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(0.5)

    # 50 mm calibration line
    pdf.line(x, y, x + mm_to_points(50), y)
    pdf.line(x, y - mm_to_points(1.5), x, y + mm_to_points(1.5))
    pdf.line(
        x + mm_to_points(50),
        y - mm_to_points(1.5),
        x + mm_to_points(50),
        y + mm_to_points(1.5),
    )

    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(x + mm_to_points(25), y + mm_to_points(2.5), "50 mm calibration line")

    # Small 10 mm calibration square
    square_x = page_width - mm_to_points(25)
    square_y = mm_to_points(5)
    pdf.rect(square_x, square_y, mm_to_points(10), mm_to_points(10), stroke=1, fill=0)
    pdf.drawCentredString(square_x + mm_to_points(5), square_y + mm_to_points(11.5), "10 mm")


def create_pdf(albums: list[AlbumArtwork], output_path: Path, config: SleeveConfig) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    page_width, page_height = A4

    seal_mm = config.seal_flap_size_mm if config.pocket_mode == "sealed" else 0.0
    sleeve_width_mm = config.cover_size_mm * 2 + seal_mm
    sleeve_height_mm = config.cover_size_mm + config.flap_size_mm * 2

    # Sleeves are rotated 90 degrees on the A4 page.
    placed_width_mm = sleeve_height_mm
    placed_height_mm = sleeve_width_mm

    placed_width_pt = mm_to_points(placed_width_mm)
    placed_height_pt = mm_to_points(placed_height_mm)

    columns = 2
    rows = 2
    sleeves_per_page = columns * rows

    x_gap = (page_width - (columns * placed_width_pt)) / (columns + 1)
    y_gap = (page_height - (rows * placed_height_pt)) / (rows + 1)

    if x_gap < 0 or y_gap < 0:
        raise ValueError("Sleeve layout does not fit on A4 with the current settings.")

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    pdf.setTitle("Mini LP NFC Sleeves")

    for page_albums in chunked(albums, sleeves_per_page):
        for slot_index, album in enumerate(page_albums):
            column = slot_index % columns
            row = slot_index // columns

            x = x_gap + column * (placed_width_pt + x_gap)
            y = page_height - y_gap - placed_height_pt - row * (placed_height_pt + y_gap)

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

        draw_calibration_marks(pdf)

        pdf.setFont("Helvetica", 7)
        pdf.drawString(
            mm_to_points(8),
            mm_to_points(287),
            "Print at 100% / Actual Size. Do not use Fit to Page.",
        )
        pdf.drawString(
            mm_to_points(8),
            mm_to_points(283),
            f"Sleeve: {config.cover_size_mm:g} mm | Pocket: {config.pocket_mode} | Flaps: {config.flap_size_mm:g} mm",
        )

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

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = SleeveConfig(
        cover_size_mm=args.cover_size,
        flap_size_mm=args.flap_size,
        seal_flap_size_mm=args.seal_flap_size,
        pocket_mode=args.pocket,
        front_mode=args.front_mode,
        back_mode=args.back_mode,
        auto_trim=args.auto_trim,
    )

    albums = discover_albums(args.covers)

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