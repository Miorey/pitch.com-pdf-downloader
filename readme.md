# Download PDF from Pitch.com
Simple python script to download a presentations as searchable PDF. 

## Supported platforms
- Pitch.com 
- Google Slides' "Publish to Web" mode
- Figma Slides

Previously had support for Canva, but now blocked by bot detection.

## Usage
Install the requirements and run the script via:
```bash
python main.py url [-r resolution] [--skip-ocr] [--skip-border-removal] [--disable-headless]
```

Valid resolutions are HD, 4K and 8K. Default resolution is 4K.
Border removal removes black borders around the slide, if present, and is by default on.
By default, run in headless mode.
