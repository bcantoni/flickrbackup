#!/usr/bin/env python3
"""
Flickr Stats CSV Export Script
Exports metadata for all photos to a CSV file.
"""

import os
import sys
import json
import logging
import time
import argparse
import csv
from pathlib import Path
from datetime import datetime
from requests_oauthlib import OAuth1Session


class FlickrStatsCSV:
    def __init__(self, api_key, api_secret, token_file=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.flickr.com/services/rest/"

        self.access_token = None
        self.access_token_secret = None
        self.user_id = None

        self.setup_logging()

        if token_file:
            self.token_file = Path(token_file)
        else:
            self.token_file = Path.home() / ".flickr_backup_tokens.json"

    def setup_logging(self):
        """Setup logging to console"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger(__name__)

    def oauth_authenticate(self):
        """Perform OAuth authentication flow using OAuth 1.0a"""
        import webbrowser

        self.logger.info("Starting OAuth authentication...")

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
        self.save_tokens()

    def save_tokens(self):
        """Save OAuth tokens to persistent storage"""
        try:
            tokens = {
                "access_token": self.access_token,
                "access_token_secret": self.access_token_secret,
                "user_id": self.user_id,
                "api_key": self.api_key,
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.token_file, "w") as f:
                json.dump(tokens, f, indent=2)
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

    def ensure_authenticated(self):
        """Ensure we have valid OAuth tokens, performing authentication if needed"""
        if self.load_tokens():
            if self.verify_tokens():
                self.logger.info("Using saved authentication")
                return
            else:
                self.logger.info("Re-authenticating...")
                self.oauth_authenticate()
        else:
            self.oauth_authenticate()

    def api_call(self, method, params=None, retry=True):
        """Make an authenticated API call using OAuth"""
        if params is None:
            params = {}

        params.update({"method": method, "format": "json", "nojsoncallback": "1"})

        oauth = OAuth1Session(
            self.api_key,
            client_secret=self.api_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        try:
            response = oauth.get(self.base_url, params=params, timeout=30)

            if response.status_code == 429:
                self.logger.error("=" * 70)
                self.logger.error("Rate limit exceeded (HTTP 429)")
                self.logger.error(
                    "Flickr API has rejected the request due to too many requests."
                )
                self.logger.error("Please wait and try again later.")
                self.logger.error("=" * 70)
                sys.exit(1)

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

    def get_all_photosets(self):
        """Get all albums/photosets and build a mapping of photo_id -> album name"""
        self.logger.info("Fetching all albums...")
        photo_to_album = {}
        page = 1
        pages = 1

        while page <= pages:
            data = self.api_call(
                "flickr.photosets.getList",
                {
                    "user_id": self.user_id,
                    "page": page,
                    "per_page": 500,
                },
            )

            photosets_data = data.get("photosets", {})
            photosets = photosets_data.get("photoset", [])
            pages = photosets_data.get("pages", 1)

            for photoset in photosets:
                album_id = photoset.get("id")
                album_title = photoset.get("title", {}).get(
                    "_content", "Untitled Album"
                )

                # Get photos in this album
                album_photos = self.get_photoset_photos(album_id)
                for photo_id in album_photos:
                    if photo_id in photo_to_album:
                        photo_to_album[photo_id] += f"; {album_title}"
                    else:
                        photo_to_album[photo_id] = album_title

            self.logger.info(f"Fetched albums page {page}/{pages}")
            page += 1

        self.logger.info(f"Found {len(photo_to_album)} photos in albums")
        return photo_to_album

    def get_photoset_photos(self, photoset_id):
        """Get all photo IDs in a photoset"""
        photo_ids = []
        page = 1
        pages = 1

        while page <= pages:
            data = self.api_call(
                "flickr.photosets.getPhotos",
                {
                    "photoset_id": photoset_id,
                    "user_id": self.user_id,
                    "page": page,
                    "per_page": 500,
                },
            )

            photoset_data = data.get("photoset", {})
            photos = photoset_data.get("photo", [])
            pages = photoset_data.get("pages", 1)

            for photo in photos:
                photo_ids.append(photo.get("id"))

            page += 1

        return photo_ids

    def get_all_photos_with_details(self):
        """Get all photos with extended metadata"""
        self.logger.info("Fetching all photos with details...")
        photos = []
        page = 1
        pages = 1

        # Request extensive extras for each photo
        extras = ",".join(
            [
                "description",
                "date_taken",
                "date_upload",
                "views",
                "tags",
                "machine_tags",
                "geo",
                "media",
                "original_format",
                "owner_name",
                "url_o",
                "url_sq",
            ]
        )

        while page <= pages:
            data = self.api_call(
                "flickr.people.getPhotos",
                {
                    "user_id": self.user_id,
                    "extras": extras,
                    "page": page,
                    "per_page": 500,
                },
            )

            photos_data = data.get("photos", {})
            photos.extend(photos_data.get("photo", []))
            pages = photos_data.get("pages", 1)
            self.logger.info(
                f"Fetched photos page {page}/{pages} ({len(photos)} total)"
            )
            page += 1

        self.logger.info(f"Found {len(photos)} total photos")
        return photos

    def get_photo_info(self, photo_id):
        """Get detailed info for a single photo (for privacy settings, EXIF, location details)"""
        try:
            data = self.api_call(
                "flickr.photos.getInfo",
                {"photo_id": photo_id},
            )
            return data.get("photo", {})
        except Exception as e:
            self.logger.debug(f"Could not get info for photo {photo_id}: {e}")
            return {}

    def get_photo_exif(self, photo_id):
        """Get EXIF data for a photo"""
        try:
            data = self.api_call(
                "flickr.photos.getExif",
                {"photo_id": photo_id},
            )
            return data.get("photo", {}).get("exif", [])
        except Exception as e:
            self.logger.debug(f"Could not get EXIF for photo {photo_id}: {e}")
            return []

    def extract_exif_value(self, exif_data, tag_label):
        """Extract a specific value from EXIF data"""
        for item in exif_data:
            if item.get("label") == tag_label:
                return item.get("raw", {}).get("_content", "")
        return ""

    def format_privacy(self, visibility):
        """Format privacy settings into a readable string"""
        if not visibility:
            return "unknown"

        is_public = visibility.get("ispublic", 0)
        is_friend = visibility.get("isfriend", 0)
        is_family = visibility.get("isfamily", 0)

        if is_public:
            return "public"
        elif is_friend and is_family:
            return "friends+family"
        elif is_friend:
            return "friends"
        elif is_family:
            return "family"
        else:
            return "private"

    def format_location(self, photo_info):
        """Format location from photo info"""
        location = photo_info.get("location", {})
        if not location:
            return ""

        parts = []
        for key in ["locality", "county", "region", "country"]:
            if key in location and location[key].get("_content"):
                parts.append(location[key]["_content"])

        if parts:
            return ", ".join(parts)

        # Fallback to coordinates
        lat = location.get("latitude", "")
        lon = location.get("longitude", "")
        if lat and lon:
            return f"{lat}, {lon}"

        return ""

    def run(self, output_file="flickr_photos.csv", fetch_exif=False):
        """Main export process"""
        self.logger.info("=" * 70)
        self.logger.info("Flickr Photo Stats CSV Export")
        self.logger.info("=" * 70)

        self.ensure_authenticated()

        # Get album mappings
        photo_to_album = self.get_all_photosets()

        # Get all photos with basic details
        photos = self.get_all_photos_with_details()

        # Prepare CSV data
        csv_rows = []
        total = len(photos)

        self.logger.info(f"Processing {total} photos for detailed info...")

        for i, photo in enumerate(photos, 1):
            photo_id = photo.get("id")

            # Get detailed info (for privacy, location details)
            photo_info = self.get_photo_info(photo_id)

            # Get EXIF if requested
            camera_model = ""
            lens = ""
            aperture = ""
            shutter_speed = ""
            iso = ""
            focal_length = ""

            if fetch_exif:
                exif_data = self.get_photo_exif(photo_id)
                camera_model = self.extract_exif_value(exif_data, "Model")
                lens = self.extract_exif_value(exif_data, "Lens")
                aperture = self.extract_exif_value(exif_data, "Aperture")
                shutter_speed = self.extract_exif_value(exif_data, "Exposure")
                iso = self.extract_exif_value(exif_data, "ISO Speed")
                focal_length = self.extract_exif_value(exif_data, "Focal Length")

            # Build row data
            row = {
                "photo_id": photo_id,
                "title": photo.get("title", ""),
                "description": photo_info.get("description", {}).get("_content", ""),
                "filename": photo_info.get(
                    "originalformat", photo.get("originalformat", "")
                ),
                "album": photo_to_album.get(photo_id, ""),
                "date_taken": photo.get("datetaken", ""),
                "date_uploaded": (
                    datetime.fromtimestamp(
                        int(photo_info.get("dateuploaded", photo.get("dateupload", 0)))
                    ).isoformat()
                    if photo_info.get("dateuploaded") or photo.get("dateupload")
                    else ""
                ),
                "location": self.format_location(photo_info),
                "latitude": photo_info.get("location", {}).get("latitude", ""),
                "longitude": photo_info.get("location", {}).get("longitude", ""),
                "tags": photo.get("tags", ""),
                "machine_tags": photo.get("machine_tags", ""),
                "privacy": self.format_privacy(photo_info.get("visibility", {})),
                "views": photo.get("views", 0),
                "comments": photo_info.get("comments", {}).get("_content", 0),
                "faves": photo_info.get("faves", 0) if "faves" in photo_info else "",
                "camera_model": camera_model,
                "lens": lens,
                "aperture": aperture,
                "shutter_speed": shutter_speed,
                "iso": iso,
                "focal_length": focal_length,
                "media_type": photo.get("media", "photo"),
                "url": f"https://www.flickr.com/photos/{self.user_id}/{photo_id}",
            }

            csv_rows.append(row)

            if i % 50 == 0 or i == total:
                self.logger.info(f"Processed {i}/{total} photos")

            # Small delay to be nice to the API
            if i % 100 == 0:
                time.sleep(0.5)

        # Write CSV
        output_path = Path(output_file)
        fieldnames = [
            "photo_id",
            "title",
            "description",
            "filename",
            "album",
            "date_taken",
            "date_uploaded",
            "location",
            "latitude",
            "longitude",
            "tags",
            "machine_tags",
            "privacy",
            "views",
            "comments",
            "faves",
            "camera_model",
            "lens",
            "aperture",
            "shutter_speed",
            "iso",
            "focal_length",
            "media_type",
            "url",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

        self.logger.info("=" * 70)
        self.logger.info(
            f"Export complete! {len(csv_rows)} photos exported to: {output_path}"
        )
        self.logger.info("=" * 70)

        # Print summary
        print(f"\nSummary:")
        print(f"  Total photos: {len(csv_rows)}")
        print(f"  Photos in albums: {sum(1 for r in csv_rows if r['album'])}")
        print(f"  Photos with location: {sum(1 for r in csv_rows if r['location'])}")
        print(
            f"  Public photos: {sum(1 for r in csv_rows if r['privacy'] == 'public')}"
        )
        print(
            f"  Private photos: {sum(1 for r in csv_rows if r['privacy'] == 'private')}"
        )
        print(f"  Total views: {sum(int(r['views']) for r in csv_rows):,}")
        print(f"  Output file: {output_path}")

        return csv_rows


def main():
    parser = argparse.ArgumentParser(
        description="Export all Flickr photo stats to CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --key YOUR_API_KEY --secret YOUR_API_SECRET
  %(prog)s --key YOUR_API_KEY --secret YOUR_API_SECRET -o my_photos.csv
  %(prog)s -k YOUR_API_KEY -s YOUR_API_SECRET --exif
        """,
    )

    parser.add_argument("-k", "--key", required=True, help="Flickr API Key (required)")
    parser.add_argument(
        "-s", "--secret", required=True, help="Flickr API Secret (required)"
    )
    parser.add_argument(
        "-t",
        "--token-file",
        default=None,
        help="Path to token file for storing OAuth credentials (default: ~/.flickr_backup_tokens.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="flickr_photos.csv",
        help="Output CSV file path (default: flickr_photos.csv)",
    )
    parser.add_argument(
        "--exif",
        action="store_true",
        help="Fetch EXIF data for each photo (slower, makes additional API calls)",
    )
    parser.add_argument(
        "--reauth",
        action="store_true",
        help="Force re-authentication (ignore saved tokens)",
    )

    args = parser.parse_args()

    print("Flickr Photo Stats CSV Export")
    print("=" * 70)
    print(f"API Key: {args.key[:10]}...")
    if args.token_file:
        print(f"Token File: {args.token_file}")
    else:
        print(f"Token File: ~/.flickr_backup_tokens.json")
    print(f"Output: {args.output}")
    print(f"Fetch EXIF: {args.exif}")
    if args.reauth:
        print("Mode: Force Re-authentication")
    print("=" * 70)

    exporter = FlickrStatsCSV(args.key, args.secret, args.token_file)

    if args.reauth and exporter.token_file.exists():
        print(f"Removing saved tokens: {exporter.token_file}")
        exporter.token_file.unlink()

    try:
        exporter.run(output_file=args.output, fetch_exif=args.exif)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        exporter.logger.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
