#!/usr/bin/env python3
"""
Flickr Stats Script
Retrieves view statistics for your Flickr photos and displays the most popular ones.
"""

import os
import sys
import json
import logging
import time
import argparse
from pathlib import Path
from datetime import datetime
from requests_oauthlib import OAuth1Session


class FlickrStats:
    def __init__(self, api_key, api_secret, token_file=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.flickr.com/services/rest/"

        self.access_token = None
        self.access_token_secret = None
        self.user_id = None

        # Setup logging
        self.setup_logging()

        # Set token file location (default to user's home directory for persistence)
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
                    "extras": "views,date_taken,date_upload,url_sq,url_m",
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

    def get_popular_photos(self):
        """Get popular photos using flickr.stats.getPopularPhotos"""
        self.logger.info("Fetching popular photos from stats API...")

        try:
            data = self.api_call(
                "flickr.stats.getPopularPhotos",
                {
                    "per_page": 100,
                },
            )

            photos = data.get("photos", {}).get("photo", [])
            self.logger.info(f"Stats API returned {len(photos)} popular photos")
            return photos
        except Exception as e:
            self.logger.warning(f"flickr.stats.getPopularPhotos failed: {e}")
            self.logger.info(
                "This API may require Flickr Pro. Falling back to view counts from photo list."
            )
            return None

    def get_photo_stats(self, photo_id, date=None):
        """Get stats for a specific photo on a specific date"""
        params = {"photo_id": photo_id}
        if date:
            params["date"] = date

        try:
            data = self.api_call("flickr.stats.getPhotoStats", params)
            return data.get("stats", {})
        except Exception as e:
            self.logger.debug(f"Could not get stats for photo {photo_id}: {e}")
            return None

    def get_total_views(self):
        """Get total views for the user's photostream"""
        try:
            data = self.api_call("flickr.stats.getTotalViews")
            return data.get("stats", {})
        except Exception as e:
            self.logger.warning(f"Could not get total views: {e}")
            return None

    def run(self, top_n=20, output_file=None):
        """Main stats gathering process"""
        self.logger.info("=" * 70)
        self.logger.info("Flickr Photo Stats")
        self.logger.info("=" * 70)

        self.ensure_authenticated()

        # Try to get total views first
        total_views = self.get_total_views()
        if total_views:
            print("\n" + "=" * 70)
            print("Total Views Summary")
            print("-" * 70)
            print(f"  Photostream: {total_views.get('total', {}).get('views', 'N/A')}")
            print(f"  Photos: {total_views.get('photos', {}).get('views', 'N/A')}")
            print(f"  Sets: {total_views.get('sets', {}).get('views', 'N/A')}")
            print(
                f"  Collections: {total_views.get('collections', {}).get('views', 'N/A')}"
            )
            print("=" * 70)

        # Try popular photos API first
        popular_photos = self.get_popular_photos()

        if popular_photos:
            # Use stats API results
            print(
                f"\nTop {min(top_n, len(popular_photos))} Most Popular Photos (from Stats API)"
            )
            print("-" * 70)

            results = []
            for i, photo in enumerate(popular_photos[:top_n], 1):
                title = photo.get("title", "Untitled")
                views = photo.get("stats", {}).get("views", 0)
                photo_id = photo.get("id")
                url = f"https://www.flickr.com/photos/{self.user_id}/{photo_id}"

                results.append(
                    {
                        "rank": i,
                        "id": photo_id,
                        "title": title,
                        "views": views,
                        "url": url,
                    }
                )

                print(f"{i:3}. {views:>8} views - {title[:50]}")
                print(f"     {url}")
        else:
            # Fallback: use views from photo list
            all_photos = self.get_all_photos()

            # Sort by view count
            sorted_photos = sorted(
                all_photos, key=lambda p: int(p.get("views", 0)), reverse=True
            )

            print(f"\nTop {min(top_n, len(sorted_photos))} Most Viewed Photos")
            print("-" * 70)

            results = []
            for i, photo in enumerate(sorted_photos[:top_n], 1):
                title = photo.get("title", "Untitled")
                views = int(photo.get("views", 0))
                photo_id = photo.get("id")
                url = f"https://www.flickr.com/photos/{self.user_id}/{photo_id}"
                date_taken = photo.get("datetaken", "Unknown")

                results.append(
                    {
                        "rank": i,
                        "id": photo_id,
                        "title": title,
                        "views": views,
                        "url": url,
                        "date_taken": date_taken,
                    }
                )

                print(f"{i:3}. {views:>8} views - {title[:50]}")
                print(f"     {url}")

        # Summary stats
        if not popular_photos:
            all_photos = (
                self.get_all_photos() if "all_photos" not in dir() else all_photos
            )
            total_view_count = sum(int(p.get("views", 0)) for p in all_photos)
            avg_views = total_view_count / len(all_photos) if all_photos else 0

            print("\n" + "=" * 70)
            print("Summary")
            print("-" * 70)
            print(f"Total photos: {len(all_photos)}")
            print(f"Total views (from photo list): {total_view_count:,}")
            print(f"Average views per photo: {avg_views:.1f}")
            print("=" * 70)

        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, "w") as f:
                json.dump(
                    {
                        "generated_at": datetime.now().isoformat(),
                        "user_id": self.user_id,
                        "top_photos": results,
                        "total_views": total_views,
                    },
                    f,
                    indent=2,
                )
            self.logger.info(f"Results saved to: {output_path}")

        return results


def main():
    parser = argparse.ArgumentParser(
        description="Get view statistics for your Flickr photos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --key YOUR_API_KEY --secret YOUR_API_SECRET
  %(prog)s --key YOUR_API_KEY --secret YOUR_API_SECRET --top 50
  %(prog)s -k YOUR_API_KEY -s YOUR_API_SECRET -o stats.json
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
        "--top",
        type=int,
        default=20,
        help="Number of top photos to display (default: 20)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file path for JSON results (optional)",
    )
    parser.add_argument(
        "--reauth",
        action="store_true",
        help="Force re-authentication (ignore saved tokens)",
    )

    args = parser.parse_args()

    print("Flickr Photo Stats Script")
    print("=" * 70)
    print(f"API Key: {args.key[:10]}...")
    if args.token_file:
        print(f"Token File: {args.token_file}")
    else:
        print(f"Token File: ~/.flickr_backup_tokens.json")
    print(f"Top N: {args.top}")
    if args.output:
        print(f"Output: {args.output}")
    if args.reauth:
        print("Mode: Force Re-authentication")
    print("=" * 70)

    stats = FlickrStats(args.key, args.secret, args.token_file)

    # Remove saved tokens if re-authentication requested
    if args.reauth and stats.token_file.exists():
        print(f"Removing saved tokens: {stats.token_file}")
        stats.token_file.unlink()

    try:
        stats.run(top_n=args.top, output_file=args.output)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        stats.logger.error(f"Stats retrieval failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
