from __future__ import annotations

import argparse
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

IMAGE_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "TIFF": ".tif",
}


def safe_folder_name(name: str) -> str:
    """Create a Windows-friendly folder name."""
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]', "-", name)
    name = re.sub(r"\s+", " ", name)
    name = name.strip(" .")
    return name or "Unknown Album"


def download_url(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "MiniLP-NFC-Sleeves/0.4 " "(personal artwork downloader; Python urllib)"
            )
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP error {exc.code} while downloading {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not download {url}: {exc.reason}") from exc
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid URL {url!r}. Use a full http:// or https:// image URL."
        ) from exc

    if not data:
        raise RuntimeError(f"No data downloaded from {url}")

    if content_type and not content_type.lower().startswith("image/"):
        print(
            f"Warning: Content-Type was {content_type!r}, "
            "but the file will still be checked as an image.",
            file=sys.stderr,
        )

    return data


def validate_image_url_arg(
    parser: argparse.ArgumentParser, value: str | None, option_name: str
) -> None:
    """Validate that a command-line image URL looks like a real HTTP/HTTPS URL."""
    if not value:
        return

    parsed = urllib.parse.urlparse(value)

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        parser.error(
            f"{option_name} must be a full http:// or https:// image URL. "
            f"Got: {value!r}"
        )


def validate_and_save_image(data: bytes, output_stem: Path) -> Path:
    """
    Validate downloaded bytes as an image and save using an extension
    based on the detected image format.
    """
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(data)
        temp_path = Path(temp_file.name)

    try:
        with Image.open(temp_path) as image:
            image.verify()

        with Image.open(temp_path) as image:
            image_format = image.format
            extension = IMAGE_EXTENSIONS.get(image_format or "")

            if extension is None:
                raise RuntimeError(
                    f"Unsupported image format: {image_format!r}. "
                    "Try JPG, PNG, WEBP, BMP, or TIFF."
                )

            output_path = output_stem.with_suffix(extension)

            if image.mode in {"RGBA", "LA"} and extension in {".jpg", ".jpeg"}:
                image = image.convert("RGB")

            image.save(output_path)
    finally:
        temp_path.unlink(missing_ok=True)

    return output_path


def download_album_art(
    album_name: str,
    front_url: str | None,
    back_url: str | None,
    covers_dir: Path,
    overwrite: bool,
) -> None:
    album_folder = covers_dir / safe_folder_name(album_name)
    album_folder.mkdir(parents=True, exist_ok=True)

    downloads = [
        ("Front", front_url),
        ("Back", back_url),
    ]

    for label, url in downloads:
        if not url:
            continue

        existing_files = list(album_folder.glob(f"{label}.*"))

        if existing_files and not overwrite:
            existing_list = ", ".join(path.name for path in existing_files)
            print(
                f"Skipping {label}: existing file found "
                f"({existing_list}). Use --overwrite to replace it."
            )
            continue

        print(f"Downloading {label}: {url}")
        data = download_url(url)
        saved_path = validate_and_save_image(data, album_folder / label)

        for existing_file in existing_files:
            if existing_file.resolve() != saved_path.resolve():
                existing_file.unlink()

        print(f"Saved {label}: {saved_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download front/back album artwork into a Covers folder."
    )

    parser.add_argument(
        "--album",
        required=True,
        help="Album folder name to create under Covers.",
    )
    parser.add_argument(
        "--front-url",
        help="URL for the front cover image.",
    )
    parser.add_argument(
        "--back-url",
        help="URL for the back cover image.",
    )
    parser.add_argument(
        "--covers",
        type=Path,
        default=Path("Covers"),
        help="Covers folder. Default: Covers",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing Front.* or Back.* files for this album.",
    )

    args = parser.parse_args()

    if not args.front_url and not args.back_url:
        parser.error("At least one of --front-url or --back-url is required.")

    validate_image_url_arg(parser, args.front_url, "--front-url")
    validate_image_url_arg(parser, args.back_url, "--back-url")

    return args


def main() -> None:
    args = parse_args()

    try:
        download_album_art(
            album_name=args.album,
            front_url=args.front_url,
            back_url=args.back_url,
            covers_dir=args.covers,
            overwrite=args.overwrite,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
