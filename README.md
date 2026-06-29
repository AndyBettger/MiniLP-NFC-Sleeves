# MiniLP NFC Sleeves

A Python tool for generating printable mini LP-style album sleeves designed to hold small NFC cards or tags.

This project was created as a companion to a Plexamp NFC setup. The idea is to make small physical album sleeves that can be tapped on an NFC reader to trigger playback in Plexamp.

The app generates A4 PDF sheets containing mini album sleeves that can be printed, cut, folded, and glued into small pockets.

## Current Status

Current milestone: **v0.4.0 - GUI artwork previews and settings layout**.

This is still an early working prototype, but the physical layout has been printed and tested.

Initial physical tests worked well on **160gsm card**. Plain printer paper is useful for test fitting but feels flimsy. Sealed sleeves are recommended for NFC cards because they hold the card more securely.

Implemented:

* A4 PDF output
* 4 sleeves per A4 sheet
* 60 mm × 60 mm finished sleeve faces
* Open pocket mode
* Sealed pocket mode
* Trapezium glue flaps
* Optional sealing flap for sealed sleeves
* Cut and fold guide marks
* 50 mm and 10 mm print calibration guides
* Basic front/back image loading
* Basic crop/fit handling
* Optional conservative border trimming
* Local image-folder workflow
* Direct image URL downloader
* Album listing from the command line
* Single or multiple selected-album PDF generation
* Basic Tkinter GUI
* GUI settings dialog
* GUI artwork URL downloading
* GUI front/back artwork previews
* GUI image dimensions and basic quality notes
* Timestamped GUI PDF output filenames

Not implemented yet:

* MusicBrainz / Cover Art Archive search
* CSV import
* Local artwork replacement from the GUI
* Manual crop/rotation preview
* Finished sleeve preview in the GUI
* Custom sleeve sizes
* Automatic page packing

## Intended Use and Artwork

The generated PDFs are intended for personal use only.

This app does not include or distribute album artwork. Any album covers used with the tool should be provided locally by the user or downloaded from direct image URLs chosen by the user.

Generated PDFs may contain copyrighted album artwork and should not be shared or published.

The `Covers/`, `output/`, and generated PDF files should normally stay out of Git.

## Installation

Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install the requirements:

```powershell
python -m pip install -r requirements.txt
```

The prototype has been tested with Python 3.13 on Windows.

## Requirements

Runtime:

```text
Pillow
reportlab
```

Development tools:

```text
black
ruff
```

The GUI uses Tkinter, which is included with the standard Windows Python installation.

## Folder Structure

Example project layout:

```text
MiniLP-NFC-Sleeves
├── Covers
│   ├── Album 1
│   │   ├── Front.jpg
│   │   └── Back.jpg
│   ├── Album 2
│   │   ├── Front.jpg
│   │   └── Back.jpg
│   └── Elvis - Blue Hawaii
│       ├── Front.jpg
│       └── Back.jpg
├── output
├── src
│   ├── download_album_art.py
│   ├── mini_lp_sleeve_generator.py
│   └── mini_lp_sleeve_gui.py
├── README.md
├── requirements.txt
├── LICENSE
└── .gitignore
```

Each album should be placed in its own folder under `Covers`.

The generator looks for:

```text
Front.*
Back.*
```

`Front.*` is required. `Back.*` is optional; if it is missing, the generator creates a placeholder back cover.

Supported image formats include:

```text
.jpg
.jpeg
.png
.webp
.bmp
.tif
.tiff
```

The album folder name is used as the album label underneath the sleeve on the generated PDF.

## GUI Usage

Run the GUI with:

```powershell
python .\src\mini_lp_sleeve_gui.py
```

The GUI can:

* list valid album folders
* select one or more albums
* preview front and back artwork
* show image dimensions and basic quality notes
* download front/back artwork from direct image URLs
* refresh the album list after downloading artwork
* generate PDFs using the command-line generator
* open the output folder
* open the most recently generated PDF

### GUI Settings

The GUI has a **Settings** dialog for:

* Covers folder
* Output folder
* Default pocket style

The GUI stores settings in the user profile folder:

```text
.mini_lp_nfc_sleeves_settings.json
```

This settings file is not part of the Git repository.

### GUI Output Files

The GUI automatically creates timestamped PDF filenames in the configured output folder.

Example:

```text
mini_lp_sleeves_2026-06-28_220530.pdf
```

This avoids accidental overwrites and keeps the main GUI screen simpler.

## Command-Line Usage

### List available albums

```powershell
python .\src\mini_lp_sleeve_generator.py --covers ".\Covers" --list-albums
```

### Generate all albums

Generate all albums found in the `Covers` folder:

```powershell
python .\src\mini_lp_sleeve_generator.py --covers ".\Covers" --output ".\output\mini_lp_sleeves.pdf" --pocket sealed
```

### Generate an open-pocket test PDF

```powershell
python .\src\mini_lp_sleeve_generator.py --covers ".\Covers" --output ".\output\mini_lp_test_open.pdf" --pocket open --max-albums 4
```

### Generate a sealed-pocket test PDF

```powershell
python .\src\mini_lp_sleeve_generator.py --covers ".\Covers" --output ".\output\mini_lp_test_sealed.pdf" --pocket sealed --max-albums 4
```

### Generate one named album

```powershell
python .\src\mini_lp_sleeve_generator.py --covers ".\Covers" --output ".\output\elvis_blue_hawaii.pdf" --pocket sealed --album "Elvis - Blue Hawaii"
```

### Generate multiple selected albums

`--album` can be used more than once:

```powershell
python .\src\mini_lp_sleeve_generator.py --covers ".\Covers" --output ".\output\selected_albums.pdf" --pocket sealed --album "Album 1" --album "Elvis - Blue Hawaii"
```

## Artwork URL Downloader

A helper script can download front and/or back artwork from direct image URLs into the folder structure expected by the generator.

Download a front cover:

```powershell
python .\src\download_album_art.py --album "Example Album" --front-url "https://example.com/front.jpg"
```

Download front and back covers:

```powershell
python .\src\download_album_art.py --album "Example Album" --front-url "https://example.com/front.jpg" --back-url "https://example.com/back.jpg"
```

Replace existing artwork for that album:

```powershell
python .\src\download_album_art.py --album "Example Album" --front-url "https://example.com/front.jpg" --back-url "https://example.com/back.jpg" --overwrite
```

The URL options must be direct `http://` or `https://` image URLs, not search terms or ordinary album-page URLs.

Downloaded files are saved under:

```text
Covers/<Album Name>/Front.*
Covers/<Album Name>/Back.*
```

The same download functionality is also available in the GUI.

## PDF Generator Options

```text
--covers
    Folder containing album subfolders with Front.* and optional Back.* images.
    Default: Covers

--output
    Output PDF path.
    Default: output/mini_lp_sleeves.pdf

--pocket
    Pocket style.
    Options: open, sealed
    Default: open

--album
    Only generate the named album.
    Use the album folder name.
    Can be used more than once.

--list-albums
    List discovered albums and exit.

--cover-size
    Finished square cover size in millimetres.
    Default: 60

--flap-size
    Top/bottom glue flap size in millimetres.
    Default: 8

--seal-flap-size
    Opening-edge seal flap size in millimetres.
    Used only in sealed pocket mode.
    Default: 6

--guide-margin
    Extra white margin around each sleeve for external cut/fold guide marks.
    Default: 3

--front-mode
    How to square the front artwork.
    Options: crop, fit
    Default: crop

--back-mode
    How to square the back artwork.
    Options: crop, fit
    Default: crop

--auto-trim
    Conservatively auto-trim small uniform borders before cropping/fitting.

--max-albums
    Only process the first N albums. Useful for testing.
```

## Artwork Downloader Options

```text
--album
    Album folder name to create or update under Covers.
    Required.

--front-url
    Direct image URL for the front cover.

--back-url
    Direct image URL for the back cover.

--covers
    Covers folder.
    Default: Covers

--overwrite
    Replace existing Front.* or Back.* files for the selected album.
```

At least one of `--front-url` or `--back-url` is required.

## Printing Notes

Print the generated PDF at:

```text
Actual Size / 100%
```

Do not use:

```text
Fit to Page
Shrink to Printable Area
Scale to Fit
```

The PDF includes calibration marks:

* 50 mm calibration line
* 10 mm calibration square

Measure these after printing to confirm the printer has not scaled the page.

Suggested first physical test:

1. Print on ordinary paper.
2. Check the 50 mm calibration line.
3. Cut out one sleeve.
4. Fold along the dashed fold marks.
5. Confirm a 50 mm × 30 mm NFC card fits.
6. Adjust print/card stock/flap settings if needed.

Physical testing so far:

* ordinary printer paper works for test fitting but feels flimsy
* 160gsm card feels and looks good for home testing
* flap angles and flap sizes work well with double-sided tape
* scoring is easy
* sealed sleeves are more practical for NFC cards because they hold the card securely
* open sleeves look more like real LP sleeves, but the card can fall out more easily

For final versions, a local print shop could print on approximately **200-220gsm silk/satin card**. Gloss or lamination should be tested carefully because folding may crack the finish.

## Sleeve Design

The current sleeve model is based on a standard LP-style sleeve:

* back cover on the left
* front cover on the right
* fold between back and front covers
* opening on the right-hand side of the front cover
* top and bottom glue flaps attached to the back cover
* optional sealing flap attached to the opening edge

The whole sleeve is rotated on the A4 page to allow four sleeves per sheet.

## Development

Format the code with Black:

```powershell
python -m black .\src\mini_lp_sleeve_generator.py .\src\download_album_art.py .\src\mini_lp_sleeve_gui.py
```

Run Ruff checks:

```powershell
python -m ruff check .\src
```

Check Git status:

```powershell
git status
```

Suggested files/folders to avoid committing:

```text
Covers/
output/
*.pdf
```

This avoids committing generated PDFs or copyrighted album artwork.

## Version Milestones

```text
v0.1.0
    Working command-line sleeve layout engine.
    Open and sealed sleeve modes.
    Physical print/cut/fold test passed.

v0.2.0
    Basic GUI added.
    Album selection added.

v0.3.0
    Direct artwork URL downloader added to the GUI.

v0.4.0
    GUI artwork previews added.
    Image dimensions and quality notes added.
    Settings dialog added.
    Timestamped GUI output filenames added.
```

## Roadmap

Planned future features:

### GUI Improvements

* Choose local replacement image for front/back artwork
* Finished sleeve preview
* Sleeve library
* Print sheet builder
* Front/back image adjustment panels
* Crop/fill options
* Manual trim controls
* Fine rotation controls

### Artwork Sources

* Search by artist and album
* MusicBrainz release ID lookup
* Cover Art Archive integration

### Batch Tools

* CSV import
* Batch approval workflow
* Generate one sheet or multi-page batch PDF
* Reprint selected sleeves

### Layout Improvements

* Custom sleeve size
* Automatic A4 page packing
* Alternative flap sizes
* Print-shop friendly output mode

## Licence

This project is licensed under the MIT Licence. See [LICENSE](LICENSE) for details.
