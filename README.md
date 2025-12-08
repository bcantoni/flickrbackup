# Flickr Backup & Stats Tools

A collection of Python scripts to backup your Flickr photo collection and analyze your photo statistics.

## Scripts Overview

| Script | Purpose |
|--------|---------|
| `flickr_backup.py` | Download your entire Flickr photo collection with metadata |
| `flickr_stats.py` | View your most popular photos and view statistics |
| `flickr_stats_csv.py` | Export all photos with comprehensive metadata to CSV |

## Features

### flickr_backup.py - Photo Backup
- OAuth authentication with persistent token storage
- Downloads original quality photos and videos
- Organizes photos by album into folders
- Embeds metadata (title, description, tags, date) into EXIF data
- Saves detailed metadata as JSON files
- Resume capability - skips already downloaded files
- Automatic retry on failed downloads

### flickr_stats.py - View Statistics
- Displays your most viewed photos
- Shows total view counts (photostream, photos, sets, collections)
- Uses Flickr Stats API for Pro accounts, falls back to view counts for free accounts
- Optional JSON output

### flickr_stats_csv.py - CSV Export
- Exports all photos to a comprehensive CSV file
- Includes album membership, location, tags, privacy settings
- Optional EXIF data (camera model, lens, aperture, ISO, etc.)
- Great for analyzing your photo library in spreadsheet software

## Prerequisites

- Python 3.7 or higher
- A Flickr account with photos
- Flickr API credentials

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
pip install Pillow piexif requests requests-oauthlib
```

## Authentication & Token Persistence

All scripts use OAuth 1.0a for authentication with shared token persistence:

### How It Works

1. **First Run**: Opens your browser for OAuth authorization and saves tokens to `~/.flickr_backup_tokens.json`
2. **Subsequent Runs**: Tokens are automatically loaded and validated - no browser needed
3. **Token Validation**: Tokens are tested with the Flickr API before each run
4. **Auto Re-auth**: Invalid/expired tokens trigger automatic re-authentication
5. **Security**: Token file has restricted permissions (chmod 600)

### Token File Location

- **Default**: `~/.flickr_backup_tokens.json`
- **Custom**: Use `-t` or `--token-file` to specify a different location

### Force Re-authentication

```bash
python flickr_backup.py -k YOUR_KEY -s YOUR_SECRET --reauth
```

---

## flickr_backup.py - Photo Backup

Downloads your entire Flickr photo collection organized by album.

### Usage

```bash
# Basic usage (downloads to ./flickr_backup)
python flickr_backup.py -k YOUR_API_KEY -s YOUR_API_SECRET

# Custom backup directory
python flickr_backup.py -k YOUR_API_KEY -s YOUR_API_SECRET -d /path/to/backup

# Force re-authentication
python flickr_backup.py -k YOUR_API_KEY -s YOUR_API_SECRET --reauth
```

### Options

| Option | Description |
|--------|-------------|
| `-k, --key` | Flickr API Key (required) |
| `-s, --secret` | Flickr API Secret (required) |
| `-d, --dir` | Backup directory (default: `./flickr_backup`) |
| `-t, --token-file` | Custom token file path |
| `--reauth` | Force re-authentication |

### What Gets Downloaded

- **Original quality** photos (highest resolution available)
- **Videos** (if you have any)
- **Metadata** embedded in EXIF (title, description, tags, date taken)
- **JSON metadata files** with complete photo information

### Folder Structure

```
flickr_backup/
├── Album Name 1/
│   ├── 12345678.jpg
│   ├── 12345678.jpg.json
│   └── ...
├── Album Name 2/
│   └── ...
├── Unsorted/              # Photos not in any album
├── .download_tracker.json # Resume tracking
└── flickr_backup_*.log    # Log file

~/.flickr_backup_tokens.json  # OAuth tokens (keep private!)
```

### Resume Capability

The script tracks downloads in `.download_tracker.json`. If interrupted, just run again - it will skip already downloaded files.

---

## flickr_stats.py - View Statistics

Displays your most popular photos by view count.

### Usage

```bash
# Show top 20 most viewed photos
python flickr_stats.py -k YOUR_API_KEY -s YOUR_API_SECRET

# Show top 50 photos
python flickr_stats.py -k YOUR_API_KEY -s YOUR_API_SECRET --top 50

# Save results to JSON
python flickr_stats.py -k YOUR_API_KEY -s YOUR_API_SECRET -o stats.json
```

### Options

| Option | Description |
|--------|-------------|
| `-k, --key` | Flickr API Key (required) |
| `-s, --secret` | Flickr API Secret (required) |
| `--top` | Number of top photos to display (default: 20) |
| `-o, --output` | Output JSON file path |
| `-t, --token-file` | Custom token file path |
| `--reauth` | Force re-authentication |

### Output Example

```
Total Views Summary
----------------------------------------------------------------------
  Photostream: 125,432
  Photos: 98,234
  Sets: 27,198
  Collections: 0
======================================================================

Top 20 Most Popular Photos (from Stats API)
----------------------------------------------------------------------
  1.    12543 views - Beautiful Sunset at the Beach
       https://www.flickr.com/photos/12345678@N00/51234567890
  2.     8932 views - Mountain Landscape
       https://www.flickr.com/photos/12345678@N00/51234567891
...
```

---

## flickr_stats_csv.py - CSV Export

Exports all your photos with comprehensive metadata to a CSV file.

### Usage

```bash
# Basic export
python flickr_stats_csv.py -k YOUR_API_KEY -s YOUR_API_SECRET

# Custom output file
python flickr_stats_csv.py -k YOUR_API_KEY -s YOUR_API_SECRET -o my_photos.csv

# Include EXIF data (slower - extra API call per photo)
python flickr_stats_csv.py -k YOUR_API_KEY -s YOUR_API_SECRET --exif
```

### Options

| Option | Description |
|--------|-------------|
| `-k, --key` | Flickr API Key (required) |
| `-s, --secret` | Flickr API Secret (required) |
| `-o, --output` | Output CSV file (default: `flickr_photos.csv`) |
| `--exif` | Fetch EXIF data (camera, lens, settings) |
| `-t, --token-file` | Custom token file path |
| `--reauth` | Force re-authentication |

### CSV Columns

| Column | Description |
|--------|-------------|
| `photo_id` | Flickr photo ID |
| `title` | Photo title |
| `description` | Photo description |
| `filename` | Original format |
| `album` | Album name(s) - semicolon-separated if in multiple |
| `date_taken` | When the photo was taken |
| `date_uploaded` | When uploaded to Flickr |
| `location` | Human-readable location (city, region, country) |
| `latitude` | GPS latitude |
| `longitude` | GPS longitude |
| `tags` | User tags |
| `machine_tags` | Machine-readable tags |
| `privacy` | public/private/friends/family/friends+family |
| `views` | Lifetime view count |
| `comments` | Number of comments |
| `faves` | Number of favorites |
| `camera_model` | Camera model (with `--exif`) |
| `lens` | Lens used (with `--exif`) |
| `aperture` | Aperture setting (with `--exif`) |
| `shutter_speed` | Shutter speed (with `--exif`) |
| `iso` | ISO setting (with `--exif`) |
| `focal_length` | Focal length (with `--exif`) |
| `media_type` | photo or video |
| `url` | Direct link to photo page |

### Output Summary

After export, displays a summary:
```
Summary:
  Total photos: 2,847
  Photos in albums: 2,341
  Photos with location: 1,892
  Public photos: 2,102
  Private photos: 745
  Total views: 156,234
  Output file: flickr_photos.csv
```

---

## Multiple Flickr Accounts

Use different token files for multiple accounts:

```bash
# Account 1
python flickr_backup.py -k KEY1 -s SECRET1 -d ./account1 -t ~/.tokens_account1.json

# Account 2
python flickr_backup.py -k KEY2 -s SECRET2 -d ./account2 -t ~/.tokens_account2.json
```

---

## Troubleshooting

### Authentication Issues

| Message | Solution |
|---------|----------|
| "No saved tokens found" | Normal on first run - authorize when prompted |
| "Saved tokens are for a different API key" | Using different credentials - will re-authenticate |
| "Saved tokens are invalid or expired" | Will automatically re-authenticate |
| "Could not load saved tokens" | Use `--reauth` or delete `~/.flickr_backup_tokens.json` |

### Download Issues

| Issue | Solution |
|-------|----------|
| "No original URL for photo" | Photo doesn't have original quality available - skipped |
| Download failures | Script auto-retries once; check internet connection |
| Rate limiting | Script handles this; large collections just take time |

### CSV Export Issues

| Issue | Solution |
|-------|----------|
| Slow export with `--exif` | EXIF requires extra API call per photo - expected |
| Missing location data | Not all photos have GPS coordinates |
| Empty album column | Photo isn't in any album |

---

## Privacy & Security

- **Keep API credentials private** - don't share or commit them
- **Token file (`~/.flickr_backup_tokens.json`)** contains access tokens - keep private
- **Token file permissions** are automatically set to `600` (user-only)
- All scripts only request **read** permissions from Flickr
- All processing happens locally - no data sent to third parties

---

## Notes

- Photos in multiple albums are downloaded once per album (creates duplicates)
- Videos are downloaded but EXIF embedding only works with JPEG files
- Flickr Pro accounts get richer stats data via the Stats API
- The `--exif` flag significantly increases export time due to per-photo API calls

## License

These scripts are provided as-is for personal use. Respect Flickr's Terms of Service and API usage guidelines.

## Support

For Flickr API documentation: https://www.flickr.com/services/api/
