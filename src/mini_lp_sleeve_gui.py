from __future__ import annotations

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
        self.geometry("760x560")
        self.minsize(700, 500)

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

        self.album_listbox = tk.Listbox(
            albums_frame,
            selectmode=tk.EXTENDED,
            exportselection=False,
        )
        self.album_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            albums_frame,
            orient=tk.VERTICAL,
            command=self.album_listbox.yview,
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.album_listbox.configure(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            button_frame,
            text="Refresh Albums",
            command=self.refresh_albums,
        ).pack(side=tk.LEFT)

        ttk.Button(
            button_frame,
            text="Select All",
            command=self.select_all_albums,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(
            button_frame,
            text="Clear Selection",
            command=self.clear_album_selection,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(
            button_frame,
            text="Generate PDF",
            command=self.generate_pdf,
        ).pack(side=tk.RIGHT)

        open_frame = ttk.Frame(main_frame)
        open_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            open_frame,
            text="Open Output PDF",
            command=self.open_output_pdf,
        ).pack(side=tk.RIGHT)

        ttk.Button(
            open_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            anchor="w",
        )
        status_label.pack(fill=tk.X, pady=(10, 0))

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
        for path in album_folder.iterdir():
            if not path.is_file():
                continue

            if (
                path.stem.casefold() == "front"
                and path.suffix.lower() in IMAGE_SUFFIXES
            ):
                return True

        return False

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

    def select_all_albums(self) -> None:
        self.album_listbox.select_set(0, tk.END)

    def clear_album_selection(self) -> None:
        self.album_listbox.select_clear(0, tk.END)

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
                return

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
