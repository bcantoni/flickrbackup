#!/usr/bin/env python3
"""
Flickr Photo Backup Script
Downloads your entire Flickr photo collection with metadata and album organization.
"""

import os
import sys
import json
import hashlib
import logging
import requests
import time
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode, parse_qs
import webbrowser
from requests_oauthlib import OAuth1Session

try:
    from PIL import Image
    import piexif
except ImportError:
    print("Error: Required packages not installed.")
    print("Please run: pip install Pillow piexif requests")
    sys.exit(1)


class FlickrBackup:
    def __init__(self, api_key, api_secret, backup_dir, token_file=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.backup_dir = Path(backup_dir)
        self.base_url = "https://api.flickr.com/services/rest/"
        self.auth_url = "https://www.flickr.com/services/oauth/authorize"
        self.request_token_url = "https://www.flickr.com/services/oauth/request_token"
        self.access_token_url = "https://www.flickr.com/services/oauth/access_token"

        self.access_token = None
        self.access_token_secret = None
        self.user_id = None

        # Create backup directory first (needed for logging)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.setup_logging()

        # Set token file location (default to user's home directory for persistence)
        if token_file:
            self.token_file = Path(token_file)
        else:
            self.token_file = Path.home() / ".flickr_backup_tokens.json"

        # Track downloaded files
        self.download_tracker_file = self.backup_dir / ".download_tracker.json"
        self.downloaded_files = self.load_download_tracker()

    def setup_logging(self):
        """Setup logging to both file and console"""
        log_file = (
            self.backup_dir
            / f"flickr_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging to: {log_file}")

    def load_download_tracker(self):
        """Load previously downloaded files"""
        if self.download_tracker_file.exists():
            try:
                with open(self.download_tracker_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load download tracker: {e}")
        return {}

    def save_download_tracker(self):
        """Save download tracker"""
        try:
            with open(self.download_tracker_file, "w") as f:
                json.dump(self.downloaded_files, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save download tracker: {e}")

    def generate_signature(self, params, secret):
        """Generate OAuth signature for non-OAuth API calls"""
        sorted_params = sorted(params.items())
        signature_base = secret + "".join([f"{k}{v}" for k, v in sorted_params])
        return hashlib.md5(signature_base.encode()).hexdigest()

    def oauth_authenticate(self):
        """Perform OAuth authentication flow using OAuth 1.0a"""
        self.logger.info("Starting OAuth authentication...")

        # Step 1: Get request token
        oauth = OAuth1Session(
            self.api_key, client_secret=self.api_secret, callback_uri="oob"
        )

        try:
            request_token_url = "https://www.flickr.com/services/oauth/request_token"
            fetch_response = oauth.fetch_request_token(request_token_url)
        except Exception as e:
            raise Exception(f"Failed to get request token: {e}")

        resource_owner_key = fetch_response.get("oauth_token")
        resource_owner_secret = fetch_response.get("oauth_token_secret")

        # Step 2: Direct user to authorize
        base_authorization_url = "https://www.flickr.com/services/oauth/authorize"
        authorization_url = oauth.authorization_url(
            base_authorization_url, perms="read"
        )

        print("\n" + "=" * 70)
        print("Please authorize this application:")
        print(authorization_url)
        print("=" * 70)

        try:
            webbrowser.open(authorization_url)
        except:
            pass

        verifier = input("\nEnter the verification code: ").strip()

        # Step 3: Exchange for access token
        oauth = OAuth1Session(
            self.api_key,
            client_secret=self.api_secret,
            resource_owner_key=resource_owner_key,
            resource_owner_secret=resource_owner_secret,
            verifier=verifier,
        )

        try:
            access_token_url = "https://www.flickr.com/services/oauth/access_token"
            oauth_tokens = oauth.fetch_access_token(access_token_url)
        except Exception as e:
            raise Exception(f"Failed to get access token: {e}")

        self.access_token = oauth_tokens.get("oauth_token")
        self.access_token_secret = oauth_tokens.get("oauth_token_secret")
        self.user_id = oauth_tokens.get("user_nsid")

        self.logger.info(f"Authentication successful! User ID: {self.user_id}")

        # Save tokens for future use
        self.save_tokens()

    def save_tokens(self):
        """Save OAuth tokens to persistent storage"""
        try:
            tokens = {
                "access_token": self.access_token,
                "access_token_secret": self.access_token_secret,
                "user_id": self.user_id,
                "api_key": self.api_key,  # Save to verify tokens match API key
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.token_file, "w") as f:
                json.dump(tokens, f, indent=2)
            # Set file permissions to user-only (0600)
            os.chmod(self.token_file, 0o600)
            self.logger.info(f"Tokens saved to: {self.token_file}")
        except Exception as e:
            self.logger.error(f"Failed to save tokens: {e}")

    def load_tokens(self):
        """Load saved OAuth tokens from persistent storage"""
        if not self.token_file.exists():
            self.logger.info("No saved tokens found")
            return False

        try:
            with open(self.token_file, "r") as f:
                tokens = json.load(f)

            # Verify tokens are for the current API key
            if tokens.get("api_key") != self.api_key:
                self.logger.warning(
                    "Saved tokens are for a different API key, ignoring"
                )
                return False

            self.access_token = tokens.get("access_token")
            self.access_token_secret = tokens.get("access_token_secret")
            self.user_id = tokens.get("user_id")

            if not all([self.access_token, self.access_token_secret, self.user_id]):
                self.logger.warning("Incomplete token data, re-authentication required")
                return False

            saved_at = tokens.get("saved_at", "unknown time")
            self.logger.info(f"Loaded saved authentication tokens from {saved_at}")
            return True
        except Exception as e:
            self.logger.warning(f"Could not load saved tokens: {e}")
            return False

    def verify_tokens(self):
        """Verify that saved tokens are still valid"""
        try:
            self.api_call("flickr.test.login")
            self.logger.info("Saved tokens are valid")
            return True
        except Exception as e:
            self.logger.warning(f"Saved tokens are invalid or expired: {e}")
            return False

    def api_call(self, method, params=None, retry=True):
        """Make an authenticated API call using OAuth"""
        if params is None:
            params = {}

        params.update({"method": method, "format": "json", "nojsoncallback": "1"})

        # Create OAuth session
        oauth = OAuth1Session(
            self.api_key,
            client_secret=self.api_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        try:
            response = oauth.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("stat") != "ok":
                raise Exception(f"API error: {data.get('message', 'Unknown error')}")

            return data
        except Exception as e:
            if retry:
                self.logger.warning(f"API call failed, retrying once: {e}")
                time.sleep(2)
                return self.api_call(method, params, retry=False)
            else:
                raise

    def get_photosets(self):
        """Get all photosets (albums)"""
        self.logger.info("Fetching photosets...")
        data = self.api_call("flickr.photosets.getList", {"user_id": self.user_id})
        photosets = data.get("photosets", {}).get("photoset", [])
        self.logger.info(f"Found {len(photosets)} photosets")
        return photosets

    def get_photoset_photos(self, photoset_id):
        """Get all photos in a photoset"""
        photos = []
        page = 1
        pages = 1

        while page <= pages:
            data = self.api_call(
                "flickr.photosets.getPhotos",
                {
                    "photoset_id": photoset_id,
                    "user_id": self.user_id,
                    "extras": "url_o,original_format,media",
                    "page": page,
                    "per_page": 500,
                },
            )

            photoset_data = data.get("photoset", {})
            photos.extend(photoset_data.get("photo", []))
            pages = photoset_data.get("pages", 1)
            page += 1

        return photos

    def get_all_photos(self):
        """Get all photos from the user's photostream"""
        self.logger.info("Fetching all photos...")
        photos = []
        page = 1
        pages = 1

        while page <= pages:
            data = self.api_call(
                "flickr.people.getPhotos",
                {
                    "user_id": self.user_id,
                    "extras": "url_o,original_format,media",
                    "page": page,
                    "per_page": 500,
                },
            )

            photos_data = data.get("photos", {})
            photos.extend(photos_data.get("photo", []))
            pages = photos_data.get("pages", 1)
            self.logger.info(f"Fetched page {page}/{pages}")
            page += 1

        self.logger.info(f"Found {len(photos)} total photos")
        return photos

    def get_photo_info(self, photo_id):
        """Get detailed photo information"""
        data = self.api_call("flickr.photos.getInfo", {"photo_id": photo_id})
        return data.get("photo", {})

    def download_file(self, url, filepath, retry=True):
        """Download a file with retry logic"""
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            if retry:
                self.logger.info("Retrying download once...")
                time.sleep(2)
                return self.download_file(url, filepath, retry=False)
            return False

    def embed_metadata(self, filepath, metadata):
        """Embed metadata into photo EXIF"""
        try:
            # Only process image files
            if filepath.suffix.lower() not in [".jpg", ".jpeg"]:
                return

            img = Image.open(filepath)

            # Load existing EXIF or create new
            try:
                exif_dict = piexif.load(filepath)
            except:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

            # Add metadata to EXIF
            if metadata.get("title"):
                exif_dict["0th"][piexif.ImageIFD.ImageDescription] = metadata[
                    "title"
                ].encode("utf-8")[:65535]

            if metadata.get("description"):
                exif_dict["0th"][piexif.ImageIFD.Copyright] = metadata[
                    "description"
                ].encode("utf-8")[:65535]

            if metadata.get("tags"):
                tags_str = ", ".join(metadata["tags"])
                exif_dict["0th"][piexif.ImageIFD.XPKeywords] = tags_str.encode(
                    "utf-16le"
                )[:65535]

            if metadata.get("date_taken"):
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = metadata[
                    "date_taken"
                ].encode("utf-8")

            # Save EXIF
            exif_bytes = piexif.dump(exif_dict)
            img.save(filepath, exif=exif_bytes, quality=100)

        except Exception as e:
            self.logger.warning(f"Could not embed metadata in {filepath.name}: {e}")

    def download_photo(self, photo, album_folder):
        """Download a single photo with metadata"""
        photo_id = photo["id"]

        # Check if already downloaded
        if photo_id in self.downloaded_files:
            self.logger.debug(f"Skipping already downloaded photo: {photo_id}")
            return True

        # Get original URL
        url = photo.get("url_o")
        if not url:
            self.logger.warning(f"No original URL for photo {photo_id}, skipping")
            return False

        # Determine file extension
        original_format = photo.get("originalformat", "jpg")
        filename = f"{photo_id}.{original_format}"
        filepath = album_folder / filename

        # Skip if file exists and is not empty
        if filepath.exists() and filepath.stat().st_size > 0:
            self.logger.info(f"File exists, skipping: {filename}")
            self.downloaded_files[photo_id] = str(filepath)
            return True

        self.logger.info(f"Downloading: {filename}")

        # Download file
        if not self.download_file(url, filepath):
            return False

        # Get detailed photo info for metadata
        try:
            photo_info = self.get_photo_info(photo_id)

            metadata = {
                "title": photo_info.get("title", {}).get("_content", ""),
                "description": photo_info.get("description", {}).get("_content", ""),
                "tags": [
                    tag.get("_content", "")
                    for tag in photo_info.get("tags", {}).get("tag", [])
                ],
                "date_taken": photo_info.get("dates", {}).get("taken", ""),
            }

            # Embed metadata
            self.embed_metadata(filepath, metadata)

            # Save metadata as JSON
            metadata_file = filepath.with_suffix(filepath.suffix + ".json")
            with open(metadata_file, "w") as f:
                json.dump(photo_info, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Could not save metadata for {filename}: {e}")

        # Mark as downloaded
        self.downloaded_files[photo_id] = str(filepath)
        self.save_download_tracker()

        return True

    def backup(self):
        """Main backup process"""
        self.logger.info("=" * 70)
        self.logger.info("Starting Flickr Backup")
        self.logger.info("=" * 70)

        # Try to load saved tokens first
        if self.load_tokens():
            # Verify tokens are still valid
            if self.verify_tokens():
                self.logger.info("Using saved authentication")
            else:
                # Tokens invalid, need to re-authenticate
                self.logger.info("Re-authenticating...")
                self.oauth_authenticate()
        else:
            # No saved tokens, need to authenticate
            self.oauth_authenticate()

        # Get all photos for tracking
        all_photos = self.get_all_photos()
        all_photo_ids = {p["id"] for p in all_photos}

        # Download photos by album
        photosets = self.get_photosets()
        photos_in_albums = set()

        for photoset in photosets:
            photoset_id = photoset["id"]
            title = photoset["title"]["_content"]

            # Clean album name for folder
            safe_title = "".join(
                c for c in title if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            album_folder = self.backup_dir / safe_title
            album_folder.mkdir(exist_ok=True)

            self.logger.info(f"\nProcessing album: {title}")

            photos = self.get_photoset_photos(photoset_id)
            self.logger.info(f"Album has {len(photos)} photos")

            for photo in photos:
                photos_in_albums.add(photo["id"])
                self.download_photo(photo, album_folder)

        # Download photos not in any album
        unsorted_photos = [p for p in all_photos if p["id"] not in photos_in_albums]

        if unsorted_photos:
            self.logger.info(f"\nProcessing {len(unsorted_photos)} unsorted photos")
            unsorted_folder = self.backup_dir / "Unsorted"
            unsorted_folder.mkdir(exist_ok=True)

            for photo in unsorted_photos:
                self.download_photo(photo, unsorted_folder)

        self.logger.info("\n" + "=" * 70)
        self.logger.info("Backup complete!")
        self.logger.info(f"Total photos processed: {len(all_photos)}")
        self.logger.info(f"Downloaded to: {self.backup_dir}")
        self.logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Backup your Flickr photo collection with metadata and album organization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --key YOUR_API_KEY --secret YOUR_API_SECRET
  %(prog)s --key YOUR_API_KEY --secret YOUR_API_SECRET --dir ./my_backup
  %(prog)s -k YOUR_API_KEY -s YOUR_API_SECRET -d /path/to/backup
  %(prog)s -k YOUR_API_KEY -s YOUR_API_SECRET --reauth  # Force re-authentication
        """,
    )

    parser.add_argument("-k", "--key", required=True, help="Flickr API Key (required)")

    parser.add_argument(
        "-s", "--secret", required=True, help="Flickr API Secret (required)"
    )

    parser.add_argument(
        "-d",
        "--dir",
        default="./flickr_backup",
        help="Backup directory path (default: ./flickr_backup)",
    )

    parser.add_argument(
        "-t",
        "--token-file",
        default=None,
        help="Path to token file for storing OAuth credentials (default: ~/.flickr_backup_tokens.json)",
    )

    parser.add_argument(
        "--reauth",
        action="store_true",
        help="Force re-authentication (ignore saved tokens)",
    )

    args = parser.parse_args()

    print("Flickr Photo Backup Script")
    print("=" * 70)
    print(f"API Key: {args.key[:10]}...")
    print(f"Backup Directory: {args.dir}")
    if args.token_file:
        print(f"Token File: {args.token_file}")
    else:
        print(f"Token File: ~/.flickr_backup_tokens.json")
    if args.reauth:
        print("Mode: Force Re-authentication")
    print("=" * 70)

    # Start backup
    backup = FlickrBackup(args.key, args.secret, args.dir, args.token_file)

    # Remove saved tokens if re-authentication requested
    if args.reauth and backup.token_file.exists():
        print(f"Removing saved tokens: {backup.token_file}")
        backup.token_file.unlink()

    try:
        backup.backup()
    except KeyboardInterrupt:
        print("\n\nBackup interrupted by user")
        sys.exit(0)
    except Exception as e:
        backup.logger.error(f"Backup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
