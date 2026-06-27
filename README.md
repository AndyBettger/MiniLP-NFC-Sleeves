# MiniLP NFC Sleeves

A Python tool for generating printable mini LP-style album sleeves designed to hold small NFC cards/tags.

This project was created as a companion to a Plexamp NFC setup, where physical mini album sleeves can be tapped on an NFC reader to trigger playback in Plexamp.

The current version generates A4 PDF sheets containing mini album sleeves that can be printed, cut, folded, and glued into small pockets.

## Current Status

This is an early working prototype.

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

Not implemented yet:

* GUI
* MusicBrainz / Cover Art Archive search
* Image URL downloading
* CSV import
* Manual crop/rotation preview
* Custom sleeve sizes
* Automatic page packing

## Intended Use

The generated PDFs are intended for personal use only.

The app does not include or distribute album artwork. Any album covers used with the tool should be provided locally by the user. Generated PDFs may contain copyrighted album artwork and should not be shared or published.

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
│   └── Album 3
│       ├── Front.jpg
│       └── Back.jpg
├── output
├── src
│   └── mini_lp_sleeve_generator.py
├── README.md
├── requirements.txt
└── .gitignore
```

Each album should currently be placed in its own folder under `Covers`.

The script looks for:

```text
Front.*
Back.*
```

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

The folder name is currently used only as a label underneath the sleeve on the generated PDF.

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

The prototype has been tested with Python 3.13.

## Requirements

```text
Pillow
reportlab
black
ruff
```

## Usage

Generate an open-pocket test PDF:

```powershell
python .\src\mini_lp_sleeve_generator.py --covers ".\Covers" --output ".\output\mini_lp_test_open.pdf" --pocket open --max-albums 4
```

Generate a sealed-pocket test PDF:

```powershell
python .\src\mini_lp_sleeve_generator.py --covers ".\Covers" --output ".\output\mini_lp_test_sealed.pdf" --pocket sealed --max-albums 4
```

Generate all albums found in the `Covers` folder:

```powershell
python .\src\mini_lp_sleeve_generator.py --covers ".\Covers" --output ".\output\mini_lp_sleeves.pdf" --pocket open
```

## Command-Line Options

```text
--covers
    Folder containing album subfolders with Front.* and Back.* images.
    Default: Covers

--output
    Output PDF path.
    Default: output/mini_lp_sleeves.pdf

--pocket
    Pocket style.
    Options: open, sealed
    Default: open

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
    Default: 5

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

For final versions, a local print shop could print on approximately 200–220 gsm silk/satin card. Gloss or lamination should be tested carefully because folding may crack the finish.

## Sleeve Design

The current sleeve model is based on a standard LP-style sleeve:

* Back cover on the left
* Front cover on the right
* Fold between back and front covers
* Opening on the right-hand side of the front cover
* Top and bottom glue flaps attached to the back cover
* Optional sealing flap attached to the opening edge

The whole sleeve is rotated on the A4 page to allow four sleeves per sheet.

## Development Notes

Format the code with Black:

```powershell
python -m black .\src\mini_lp_sleeve_generator.py
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

## Roadmap

Planned future features:

### GUI

* Sleeve library
* Print sheet builder
* Finished sleeve preview
* Front/back image adjustment panels
* Crop/fill options
* Manual trim controls
* Fine rotation controls
* Open/sealed pocket selection

### Artwork Tools

* Search by artist and album
* MusicBrainz release ID lookup
* Cover Art Archive integration
* Download front/back artwork
* Paste image URL and download locally
* Choose local replacement image

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
