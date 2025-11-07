# Flickr Photo Backup Script

A Python script to download your entire Flickr photo collection with metadata, organized into album folders.

## Features

- ✅ OAuth authentication flow with persistent token storage
- ✅ Downloads original quality photos and videos
- ✅ Organizes photos by album into folders
- ✅ Embeds metadata (title, description, tags, date) into EXIF data
- ✅ Saves detailed metadata as JSON files
- ✅ Resume capability - skips already downloaded files
- ✅ Automatic retry on failed downloads
- ✅ Comprehensive logging
- ✅ Handles photos not in any album (Unsorted folder)
- ✅ OAuth tokens persist across runs (no re-auth needed)
- ✅ Automatic token validation and refresh
- ✅ Secure token storage with proper file permissions
- ✅ Command-line interface with flexible options

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
pip install Pillow piexif requests requests-oauthlib
```

## Authentication & Token Persistence

The script uses OAuth 1.0a for authentication with robust token persistence:

### How Token Persistence Works

1. **First Run**: The script opens your browser for OAuth authorization and saves tokens to `~/.flickr_backup_tokens.json`
2. **Subsequent Runs**: Tokens are automatically loaded and validated - no browser authorization needed
3. **Token Validation**: Before each run, tokens are tested with the Flickr API
4. **Auto Re-auth**: If tokens are invalid or expired, the script automatically prompts for re-authentication
5. **Security**: Token file is stored in your home directory with restricted permissions (chmod 600)

### Token File Location

- **Default**: `~/.flickr_backup_tokens.json` (in your home directory)
- **Custom**: Use `-t` or `--token-file` to specify a different location
- **Security**: File permissions are automatically set to user-only (600)
- **Format**: JSON file containing access tokens, user ID, API key, and timestamp

### Token Management

**Automatic token validation**:

- Saved tokens are checked against your current API key
- API test call validates tokens before use
- Invalid/expired tokens trigger automatic re-authentication

**Force re-authentication**:

```bash
python flickr_backup.py -k YOUR_KEY -s YOUR_SECRET --reauth
```

**Use custom token file** (useful for multiple Flickr accounts):

```bash
python flickr_backup.py -k YOUR_KEY -s YOUR_SECRET -t /path/to/custom_tokens.json
```

### 3. Run the Script

Basic usage:

```bash
python flickr_backup.py --key YOUR_API_KEY --secret YOUR_API_SECRET
```

With custom backup directory:

```bash
python flickr_backup.py --key YOUR_API_KEY --secret YOUR_API_SECRET --dir /path/to/backup
```

Short form:

```bash
python flickr_backup.py -k YOUR_API_KEY -s YOUR_API_SECRET -d ./my_backup
```

Force re-authentication (ignore saved tokens):

```bash
python flickr_backup.py -k YOUR_API_KEY -s YOUR_API_SECRET --reauth
```

### Command Line Options

- `-k, --key` - Flickr API Key (required)
- `-s, --secret` - Flickr API Secret (required)
- `-d, --dir` - Backup directory path (default: `./flickr_backup`)
- `-t, --token-file` - Custom path for storing OAuth tokens (default: `~/.flickr_backup_tokens.json`)
- `--reauth` - Force re-authentication, ignoring any saved tokens

### Examples

**Basic usage** (uses default backup directory):

```bash
python flickr_backup.py -k YOUR_API_KEY -s YOUR_API_SECRET
```

**Custom backup directory**:

```bash
python flickr_backup.py -k YOUR_API_KEY -s YOUR_API_SECRET -d /path/to/backup
```

**Force re-authentication** (ignore saved tokens):

```bash
python flickr_backup.py -k YOUR_API_KEY -s YOUR_API_SECRET --reauth
```

**Multiple Flickr accounts** (use different token files):

```bash
# Account 1
python flickr_backup.py -k KEY1 -s SECRET1 -d ./account1 -t ~/.tokens_account1.json

# Account 2
python flickr_backup.py -k KEY2 -s SECRET2 -d ./account2 -t ~/.tokens_account2.json
```

## Usage

### First Run - Authentication

On first run, the script will:

1. Open your browser to Flickr's authorization page
2. Ask you to authorize the application
3. Prompt you to enter the verification code shown on the page
4. Save the authentication tokens to `~/.flickr_backup_tokens.json` for future runs

### Subsequent Runs

The script automatically loads and validates saved OAuth tokens from `~/.flickr_backup_tokens.json`, so you won't need to authorize again unless:

- The tokens expire (rare for Flickr OAuth tokens)
- You use the `--reauth` flag to force re-authentication
- You switch to a different API key

If saved tokens are invalid, the script will automatically prompt you to re-authenticate.

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
├── .download_tracker.json  # Resume tracking
└── flickr_backup_20241103_143022.log  # Log file

~/.flickr_backup_tokens.json    # OAuth tokens (stored in home directory, keep private!)
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

### Authentication Issues

**"No saved tokens found"**

- Normal on first run - the script will prompt for OAuth authorization
- Tokens will be saved for future runs

**"Saved tokens are for a different API key"**

- You're using different API credentials than the saved tokens
- Script will automatically prompt for new authorization with the current API key

**"Saved tokens are invalid or expired"**

- Tokens have become invalid (rare for Flickr)
- Script will automatically re-authenticate
- Or use `--reauth` to force fresh authentication

**"Could not load saved tokens"**

- Token file may be corrupted
- Use `--reauth` to create fresh tokens
- Or manually delete `~/.flickr_backup_tokens.json` and run again

### Download Issues

**"No original URL for photo"**
Some photos may not have original quality available due to Flickr settings. These will be skipped.

**Download failures**
The script automatically retries failed downloads once. If downloads continue to fail, check your internet connection.

### Performance

**Rate limiting**
Flickr API has rate limits. The script handles this gracefully, but very large collections may take time.

## Privacy & Security

- **Keep your API credentials private** - don't share them
- **`~/.flickr_backup_tokens.json` contains access tokens** - keep this file private and secure
- **Token file permissions** are automatically set to `600` (user read/write only)
- **Tokens stored outside backup directory** - won't be accidentally shared or backed up
- **API key verification** - tokens are validated against your current API key
- The script only requests **read** permissions from Flickr
- All processing happens locally on your machine
- No data is sent to third parties

## Benefits of Token Persistence

1. **Convenience** - Authorize once, use indefinitely (until tokens expire)
2. **Automation-Friendly** - Can be scheduled/scripted without manual intervention
3. **Faster** - Skip OAuth flow on subsequent runs
4. **Secure** - Tokens stored with proper permissions in home directory
5. **Flexible** - Support for multiple accounts via custom token files
6. **Reliable** - Automatic token validation and re-authentication when needed

## Notes

- Photos in multiple albums will be downloaded once per album (duplicates created)
- The script uses the Flickr API's original quality URL when available
- Videos are downloaded but metadata is saved as JSON only (no EXIF embedding for videos)
- EXIF embedding only works with JPEG files

## License

This script is provided as-is for personal use. Respect Flickr's Terms of Service and API usage guidelines.

## Support

For issues or questions about the Flickr API, see: https://www.flickr.com/services/api/
