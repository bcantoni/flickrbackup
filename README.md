# Flickr Photo Backup Script

A Python script to download your entire Flickr photo collection with metadata, organized into album folders.

## Features

- ✅ OAuth authentication flow
- ✅ Downloads original quality photos and videos
- ✅ Organizes photos by album into folders
- ✅ Embeds metadata (title, description, tags, date) into EXIF data
- ✅ Saves detailed metadata as JSON files
- ✅ Resume capability - skips already downloaded files
- ✅ Automatic retry on failed downloads (once)
- ✅ Comprehensive logging
- ✅ Handles photos not in any album (Unsorted folder)

## Prerequisites

- Python 3.7 or higher
- A Flickr account with photos
- Flickr API credentials (see setup below)

## Setup

### 1. Get Flickr API Credentials

1. Go to https://www.flickr.com/services/apps/create/
2. Click "Request an API Key"
3. Choose "Apply for a Non-Commercial Key"
4. Fill out the form with your app details
5. You'll receive an **API Key** and **API Secret** - keep these handy!

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install Pillow piexif requests
```

### 3. Run the Script

```bash
python flickr_backup.py
```

## Usage

When you run the script, you'll be prompted for:

1. **API Key** - from step 1 above
2. **API Secret** - from step 1 above
3. **Backup directory** - where to save photos (default: `./flickr_backup`)

### First Run - Authentication

On first run, the script will:
1. Open your browser to Flickr's authorization page
2. Ask you to authorize the application
3. Prompt you to enter the verification code shown on the page
4. Save the authentication tokens for future runs

### Subsequent Runs

The script saves authentication tokens, so you won't need to authorize again unless the tokens expire.

## What Gets Downloaded

- **Original quality** photos (highest resolution available)
- **Videos** (if you have any)
- **Metadata** embedded in EXIF:
  - Title
  - Description
  - Tags
  - Date taken
- **JSON metadata files** with complete photo information

## Folder Structure

```
flickr_backup/
├── Album Name 1/
│   ├── 12345678.jpg
│   ├── 12345678.jpg.json
│   ├── 12345679.jpg
│   └── 12345679.jpg.json
├── Album Name 2/
│   └── ...
├── Unsorted/          # Photos not in any album
│   └── ...
├── .flickr_tokens.json     # Auth tokens (keep private!)
├── .download_tracker.json  # Resume tracking
└── flickr_backup_20241103_143022.log  # Log file
```

## Resume Capability

The script tracks downloaded files in `.download_tracker.json`. If the backup is interrupted:

1. Simply run the script again
2. It will skip files that were already successfully downloaded
3. Continue from where it left off

## Logging

Each run creates a timestamped log file with:
- Progress updates
- Download status for each photo
- Any errors or warnings
- Summary statistics

Logs are saved in the backup directory.

## Troubleshooting

### "No original URL for photo"
Some photos may not have original quality available due to Flickr settings. These will be skipped.

### Download failures
The script automatically retries failed downloads once. If downloads continue to fail, check your internet connection.

### Authentication errors
If you see authentication errors on subsequent runs, delete `.flickr_tokens.json` and re-authenticate.

### Rate limiting
Flickr API has rate limits. The script handles this gracefully, but very large collections may take time.

## Privacy & Security

- **Keep your API credentials private** - don't share them
- **`.flickr_tokens.json` contains access tokens** - don't share this file
- The script only requests **read** permissions
- All processing happens locally on your machine

## Notes

- Photos in multiple albums will be downloaded once per album (duplicates created)
- The script uses the Flickr API's original quality URL when available
- Videos are downloaded but metadata is saved as JSON only (no EXIF embedding for videos)
- EXIF embedding only works with JPEG files

## License

This script is provided as-is for personal use. Respect Flickr's Terms of Service and API usage guidelines.

## Support

For issues or questions about the Flickr API, see: https://www.flickr.com/services/api/
