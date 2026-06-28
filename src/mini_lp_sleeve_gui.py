from __future__ import annotations
from PIL import Image, ImageTk, UnidentifiedImageError

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter import ttk

IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

PREVIEW_PANEL_WIDTH = 490
PREVIEW_TITLE_HEIGHT = 48
PREVIEW_CARD_WIDTH = 230
PREVIEW_CARD_HEIGHT = 305
PREVIEW_IMAGE_BOX_SIZE = 205
PREVIEW_IMAGE_SIZE = 180
PREVIEW_INFO_HEIGHT = 56

class MiniLPSleeveGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.project_root = Path(__file__).resolve().parents[1]
        self.generator_script = (
            Path(__file__).resolve().with_name("mini_lp_sleeve_generator.py")
        )

        self.downloader_script = (
            Path(__file__).resolve().with_name("download_album_art.py")
        )

        self.title("MiniLP NFC Sleeve Generator")
        self.geometry("1150x760")
        self.minsize(950, 650)

        self.covers_var = tk.StringVar(value=str(self.project_root / "Covers"))
        self.output_var = tk.StringVar(
            value=str(self.project_root / "output" / "gui_selected_sleeves.pdf")
        )
        self.pocket_var = tk.StringVar(value="sealed")
        self.status_var = tk.StringVar(value="Ready.")

        self.download_album_var = tk.StringVar()
        self.download_front_url_var = tk.StringVar()
        self.download_back_url_var = tk.StringVar()
        self.download_overwrite_var = tk.BooleanVar(value=False)

        self.preview_title_var = tk.StringVar(value="Select an album to preview.")
        self.front_info_var = tk.StringVar(value="Front: -")
        self.back_info_var = tk.StringVar(value="Back: -")

        self.front_preview_image: ImageTk.PhotoImage | None = None
        self.back_preview_image: ImageTk.PhotoImage | None = None

        self.front_preview_label: ttk.Label
        self.back_preview_label: ttk.Label
        self.front_info_label: ttk.Label
        self.back_info_label: ttk.Label

        self.album_listbox: tk.Listbox

        self.build_ui()
        self.refresh_albums()

    def build_ui(self) -> None:
        main_frame = ttk.Frame(self, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        path_frame = ttk.LabelFrame(main_frame, text="Folders", padding=10)
        path_frame.pack(fill=tk.X)

        ttk.Label(path_frame, text="Covers folder:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ttk.Entry(path_frame, textvariable=self.covers_var).grid(
            row=0, column=1, sticky="ew", pady=4
        )
        ttk.Button(
            path_frame,
            text="Browse...",
            command=self.browse_covers_folder,
        ).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(path_frame, text="Output PDF:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ttk.Entry(path_frame, textvariable=self.output_var).grid(
            row=1, column=1, sticky="ew", pady=4
        )
        ttk.Button(
            path_frame,
            text="Browse...",
            command=self.browse_output_file,
        ).grid(row=1, column=2, padx=(8, 0), pady=4)

        path_frame.columnconfigure(1, weight=1)

        options_frame = ttk.LabelFrame(main_frame, text="Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(options_frame, text="Pocket style:").pack(side=tk.LEFT)

        ttk.Radiobutton(
            options_frame,
            text="Sealed",
            variable=self.pocket_var,
            value="sealed",
        ).pack(side=tk.LEFT, padx=(10, 0))

        ttk.Radiobutton(
            options_frame,
            text="Open",
            variable=self.pocket_var,
            value="open",
        ).pack(side=tk.LEFT, padx=(10, 0))

        download_frame = ttk.LabelFrame(
            main_frame,
            text="Download Artwork from URLs",
            padding=10,
        )
        download_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(download_frame, text="Album folder name:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ttk.Entry(download_frame, textvariable=self.download_album_var).grid(
            row=0, column=1, sticky="ew", pady=4
        )

        ttk.Label(download_frame, text="Front image URL:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ttk.Entry(download_frame, textvariable=self.download_front_url_var).grid(
            row=1, column=1, sticky="ew", pady=4
        )

        ttk.Label(download_frame, text="Back image URL:").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ttk.Entry(download_frame, textvariable=self.download_back_url_var).grid(
            row=2, column=1, sticky="ew", pady=4
        )

        download_button_frame = ttk.Frame(download_frame)
        download_button_frame.grid(row=3, column=1, sticky="e", pady=(6, 0))

        ttk.Checkbutton(
            download_button_frame,
            text="Overwrite existing artwork",
            variable=self.download_overwrite_var,
        ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Button(
            download_button_frame,
            text="Clear",
            command=self.clear_download_fields,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            download_button_frame,
            text="Download Artwork",
            command=self.download_artwork,
        ).pack(side=tk.LEFT)

        download_frame.columnconfigure(1, weight=1)

        albums_frame = ttk.LabelFrame(main_frame, text="Albums", padding=10)
        albums_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        album_list_frame = ttk.Frame(albums_frame)
        album_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.album_listbox = tk.Listbox(
            album_list_frame,
            selectmode=tk.EXTENDED,
            exportselection=False,
        )
        self.album_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.album_listbox.bind("<<ListboxSelect>>", self.update_preview_from_selection)

        scrollbar = ttk.Scrollbar(
            album_list_frame,
            orient=tk.VERTICAL,
            command=self.album_listbox.yview,
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.album_listbox.configure(yscrollcommand=scrollbar.set)

        preview_frame = ttk.Frame(
            albums_frame,
            width=PREVIEW_PANEL_WIDTH,
            padding=(10, 0, 0, 0),
        )
        preview_frame.pack(side=tk.RIGHT, fill=tk.Y)
        preview_frame.pack_propagate(False)

        preview_title_frame = ttk.Frame(
            preview_frame,
            width=PREVIEW_PANEL_WIDTH,
            height=PREVIEW_TITLE_HEIGHT,
        )
        preview_title_frame.pack(fill=tk.X, pady=(0, 8))
        preview_title_frame.pack_propagate(False)

        ttk.Label(
            preview_title_frame,
            textvariable=self.preview_title_var,
            wraplength=PREVIEW_PANEL_WIDTH - 20,
            anchor="nw",
            justify=tk.LEFT,
        ).pack(fill=tk.BOTH, expand=True)

        preview_cards_frame = ttk.Frame(preview_frame)
        preview_cards_frame.pack(fill=tk.X)

        front_frame = ttk.LabelFrame(
            preview_cards_frame,
            text="Front",
            padding=6,
            width=PREVIEW_CARD_WIDTH,
            height=PREVIEW_CARD_HEIGHT,
        )
        front_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        front_frame.pack_propagate(False)

        front_frame.columnconfigure(0, weight=1)
        front_frame.rowconfigure(0, minsize=PREVIEW_IMAGE_BOX_SIZE)
        front_frame.rowconfigure(1, minsize=PREVIEW_INFO_HEIGHT)

        front_image_frame = ttk.Frame(
            front_frame,
            width=PREVIEW_CARD_WIDTH - 12,
            height=PREVIEW_IMAGE_BOX_SIZE,
        )
        front_image_frame.grid(row=0, column=0, sticky="nsew")
        front_image_frame.grid_propagate(False)

        self.front_preview_label = ttk.Label(
            front_image_frame,
            text="No front preview",
            anchor="center",
            justify=tk.CENTER,
        )
        self.front_preview_label.pack(fill=tk.BOTH, expand=True)

        self.front_info_label = ttk.Label(
            front_frame,
            textvariable=self.front_info_var,
            anchor="center",
            justify=tk.CENTER,
            wraplength=PREVIEW_CARD_WIDTH - 20,
        )
        self.front_info_label.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

        back_frame = ttk.LabelFrame(
            preview_cards_frame,
            text="Back",
            padding=6,
            width=PREVIEW_CARD_WIDTH,
            height=PREVIEW_CARD_HEIGHT,
        )
        back_frame.pack(side=tk.LEFT, fill=tk.Y)
        back_frame.pack_propagate(False)

        back_frame.columnconfigure(0, weight=1)
        back_frame.rowconfigure(0, minsize=PREVIEW_IMAGE_BOX_SIZE)
        back_frame.rowconfigure(1, minsize=PREVIEW_INFO_HEIGHT)

        back_image_frame = ttk.Frame(
            back_frame,
            width=PREVIEW_CARD_WIDTH - 12,
            height=PREVIEW_IMAGE_BOX_SIZE,
        )
        back_image_frame.grid(row=0, column=0, sticky="nsew")
        back_image_frame.grid_propagate(False)

        self.back_preview_label = ttk.Label(
            back_image_frame,
            text="No back preview",
            anchor="center",
            justify=tk.CENTER,
        )
        self.back_preview_label.pack(fill=tk.BOTH, expand=True)

        self.back_info_label = ttk.Label(
            back_frame,
            textvariable=self.back_info_var,
            anchor="center",
            justify=tk.CENTER,
            wraplength=PREVIEW_CARD_WIDTH - 20,
        )
        self.back_info_label.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            action_frame,
            text="Refresh Albums",
            command=self.refresh_albums,
        ).pack(side=tk.LEFT)

        ttk.Button(
            action_frame,
            text="Select All",
            command=self.select_all_albums,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(
            action_frame,
            text="Clear Selection",
            command=self.clear_album_selection,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(
            action_frame,
            text="Generate PDF",
            command=self.generate_pdf,
        ).pack(side=tk.RIGHT)

        ttk.Button(
            action_frame,
            text="Open Output PDF",
            command=self.open_output_pdf,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        ttk.Button(
            action_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            anchor="w",
        )
        status_label.pack(fill=tk.X, pady=(8, 0))

    def resolve_path(self, value: str) -> Path:
        path = Path(value).expanduser()

        if path.is_absolute():
            return path

        return self.project_root / path

    def browse_covers_folder(self) -> None:
        folder = filedialog.askdirectory(
            title="Choose Covers folder",
            initialdir=self.resolve_path(self.covers_var.get()),
        )

        if folder:
            self.covers_var.set(folder)
            self.refresh_albums()

    def browse_output_file(self) -> None:
        output_path = filedialog.asksaveasfilename(
            title="Choose output PDF",
            initialdir=self.resolve_path(self.output_var.get()).parent,
            initialfile=self.resolve_path(self.output_var.get()).name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )

        if output_path:
            self.output_var.set(output_path)

    def has_front_image(self, album_folder: Path) -> bool:
        return self.find_album_image(album_folder, "front") is not None

    def discover_album_names(self) -> list[str]:
        covers_folder = self.resolve_path(self.covers_var.get())

        if not covers_folder.exists():
            raise FileNotFoundError(f"Covers folder does not exist: {covers_folder}")

        if not covers_folder.is_dir():
            raise NotADirectoryError(f"Covers path is not a folder: {covers_folder}")

        album_names = []

        for album_folder in sorted(covers_folder.iterdir()):
            if album_folder.is_dir() and self.has_front_image(album_folder):
                album_names.append(album_folder.name)

        return album_names

    def find_album_image(self, album_folder: Path, image_name: str) -> Path | None:
        """Find Front.* or Back.* image in an album folder."""
        for path in album_folder.iterdir():
            if not path.is_file():
                continue

            if (
                path.stem.casefold() == image_name.casefold()
                and path.suffix.lower() in IMAGE_SUFFIXES
            ):
                return path

        return None

    def album_folder_for_name(self, album_name: str) -> Path:
        """Return the folder path for an album name."""
        return self.resolve_path(self.covers_var.get()) / album_name

    def image_quality_note(self, width: int, height: int) -> str:
        """Return a small quality note based on image dimensions."""
        shortest_side = min(width, height)

        if shortest_side < 300:
            return "very small"
        if shortest_side < 500:
            return "low resolution"
        if shortest_side < 800:
            return "usable"

        return "good"

    def load_preview_image(
            self,
            image_path: Path,
            max_size: tuple[int, int] = (PREVIEW_IMAGE_SIZE, PREVIEW_IMAGE_SIZE),
    ) -> tuple[ImageTk.PhotoImage, str]:
        """Load an image as a Tkinter thumbnail and return info text."""
        with Image.open(image_path) as image:
            width, height = image.size
            preview = image.convert("RGB")
            preview.thumbnail(max_size, Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(preview)
        quality_note = self.image_quality_note(width, height)
        info = f"{width} × {height} px ({quality_note})"

        return photo, info

    def update_single_preview(
        self,
        preview_label: ttk.Label,
        preview_attr_name: str,
        info_var: tk.StringVar,
        image_path: Path | None,
        label_text: str,
    ) -> None:
        """Update one preview panel."""
        if image_path is None:
            setattr(self, preview_attr_name, None)
            preview_label.configure(
                image="",
                text=f"{label_text} image missing",
            )
            info_var.set(f"{label_text}: missing")
            return
        try:
            photo, info = self.load_preview_image(image_path)
        except (OSError, UnidentifiedImageError) as exc:
            setattr(self, preview_attr_name, None)
            preview_label.configure(
                image="", text=f"Could not load {label_text.lower()}"
            )
            info_var.set(f"{label_text}: error - {exc}")
            return

        setattr(self, preview_attr_name, photo)
        preview_label.configure(image=photo, text="")
        info_var.set(f"{label_text}: {info}")

    def clear_previews(self) -> None:
        """Clear front/back preview panels."""
        self.front_preview_image = None
        self.back_preview_image = None

        self.front_preview_label.configure(image="", text="No front preview")
        self.back_preview_label.configure(image="", text="No back preview")
        self.front_info_var.set("Front: -")
        self.back_info_var.set("Back: -")

    def update_preview_from_selection(self, _event: tk.Event | None = None) -> None:
        """Update the preview panel based on the first selected album."""
        selected_albums = self.selected_album_names()

        if not selected_albums:
            self.preview_title_var.set("Select an album to preview.")
            self.clear_previews()
            return

        album_name = selected_albums[0]

        if len(selected_albums) > 1:
            self.preview_title_var.set(
                f"Preview: {album_name} (+ {len(selected_albums) - 1} more selected)"
            )
        else:
            self.preview_title_var.set(f"Preview: {album_name}")

        album_folder = self.album_folder_for_name(album_name)

        front_path = self.find_album_image(album_folder, "front")
        back_path = self.find_album_image(album_folder, "back")

        self.update_single_preview(
            self.front_preview_label,
            "front_preview_image",
            self.front_info_var,
            front_path,
            "Front",
        )

        self.update_single_preview(
            self.back_preview_label,
            "back_preview_image",
            self.back_info_var,
            back_path,
            "Back",
        )

    def refresh_albums(self) -> None:
        self.album_listbox.delete(0, tk.END)

        try:
            album_names = self.discover_album_names()
        except OSError as exc:
            self.status_var.set("Could not load albums.")
            messagebox.showerror("Album Load Error", str(exc))
            return

        for album_name in album_names:
            self.album_listbox.insert(tk.END, album_name)

        self.status_var.set(f"Found {len(album_names)} album(s).")
        self.update_preview_from_selection()

    def select_all_albums(self) -> None:
        self.album_listbox.select_set(0, tk.END)
        self.update_preview_from_selection()

    def clear_album_selection(self) -> None:
        self.album_listbox.select_clear(0, tk.END)
        self.update_preview_from_selection()

    def selected_album_names(self) -> list[str]:
        return [
            self.album_listbox.get(index) for index in self.album_listbox.curselection()
        ]

    def clear_download_fields(self) -> None:
        self.download_album_var.set("")
        self.download_front_url_var.set("")
        self.download_back_url_var.set("")
        self.download_overwrite_var.set(False)

    def select_album_by_name(self, album_name: str) -> None:
        self.album_listbox.select_clear(0, tk.END)

        for index in range(self.album_listbox.size()):
            if self.album_listbox.get(index) == album_name:
                self.album_listbox.select_set(index)
                self.album_listbox.see(index)
                self.update_preview_from_selection()
                return

        self.update_preview_from_selection()

    def download_artwork(self) -> None:
        album_name = self.download_album_var.get().strip()
        front_url = self.download_front_url_var.get().strip()
        back_url = self.download_back_url_var.get().strip()

        if not album_name:
            messagebox.showwarning(
                "Album Name Required",
                "Enter an album folder name before downloading artwork.",
            )
            return

        if not front_url and not back_url:
            messagebox.showwarning(
                "Image URL Required",
                "Enter at least one front or back image URL.",
            )
            return

        covers_folder = self.resolve_path(self.covers_var.get())

        command = [
            sys.executable,
            str(self.downloader_script),
            "--album",
            album_name,
            "--covers",
            str(covers_folder),
        ]

        if front_url:
            command.extend(["--front-url", front_url])

        if back_url:
            command.extend(["--back-url", back_url])

        if self.download_overwrite_var.get():
            command.append("--overwrite")

        self.status_var.set("Downloading artwork...")
        self.update_idletasks()

        result = subprocess.run(
            command,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            messagebox.showerror(
                "Artwork Download Failed",
                result.stderr or result.stdout or "Unknown error.",
            )
            self.status_var.set("Artwork download failed.")
            return

        self.refresh_albums()
        self.select_album_by_name(album_name)

        self.status_var.set(f"Downloaded artwork for: {album_name}")
        messagebox.showinfo(
            "Artwork Downloaded",
            f"Downloaded artwork for:\n{album_name}",
        )

    def generate_pdf(self) -> None:
        selected_albums = self.selected_album_names()

        if not selected_albums:
            generate_all = messagebox.askyesno(
                "Generate All Albums?",
                "No albums are selected. Generate all discovered albums?",
            )

            if not generate_all:
                return

        covers_folder = self.resolve_path(self.covers_var.get())
        output_path = self.resolve_path(self.output_var.get())
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            sys.executable,
            str(self.generator_script),
            "--covers",
            str(covers_folder),
            "--output",
            str(output_path),
            "--pocket",
            self.pocket_var.get(),
        ]

        for album_name in selected_albums:
            command.extend(["--album", album_name])

        self.status_var.set("Generating PDF...")
        self.update_idletasks()

        result = subprocess.run(
            command,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            messagebox.showerror(
                "PDF Generation Failed",
                result.stderr or result.stdout or "Unknown error.",
            )
            self.status_var.set("PDF generation failed.")
            return

        self.status_var.set(f"Created PDF: {output_path}")
        messagebox.showinfo("PDF Created", f"Created PDF:\n{output_path}")

    def open_output_pdf(self) -> None:
        output_path = self.resolve_path(self.output_var.get())

        if not output_path.exists():
            messagebox.showwarning("PDF Not Found", f"PDF not found:\n{output_path}")
            return

        os.startfile(output_path)

    def open_output_folder(self) -> None:
        output_folder = self.resolve_path(self.output_var.get()).parent

        if not output_folder.exists():
            messagebox.showwarning(
                "Folder Not Found",
                f"Output folder not found:\n{output_folder}",
            )
            return

        os.startfile(output_folder)


def main() -> None:
    app = MiniLPSleeveGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
