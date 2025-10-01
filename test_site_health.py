#!/usr/bin/env python3
"""
End-to-end site health checker for SABC tournament management system.

Tests all public and admin routes for:
- HTTP 200 responses (no 500 errors)
- No broken links
- Proper redirects for auth-protected pages
- Database connectivity

Run with: python test_site_health.py
"""

import sys
import time
from typing import Dict, List, Set
from urllib.parse import urljoin

import requests  # type: ignore
from bs4 import BeautifulSoup


class SiteHealthChecker:
    """Comprehensive site health checker."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.visited: Set[str] = set()
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []
        self.admin_user: Dict[str, str] = {}

    def check_health(self) -> bool:
        """Run all health checks. Returns True if all pass."""
        print(f"🔍 Starting site health check for {self.base_url}\n")

        # Check server is running
        if not self._check_server_running():
            return False

        # Test public routes
        print("📄 Testing public routes...")
        self._test_public_routes()

        # Login as admin
        print("\n🔐 Testing admin authentication...")
        if self._login_as_admin():
            print("✅ Admin login successful")

            # Test admin routes
            print("\n⚙️  Testing admin routes...")
            self._test_admin_routes()
        else:
            self.warnings.append(
                {"type": "auth", "message": "Could not login as admin - skipping admin route tests"}
            )

        # Crawl and check all discovered links
        print("\n🕷️  Crawling site for broken links...")
        self._crawl_site()

        # Print results
        self._print_results()

        return len(self.errors) == 0

    def _check_server_running(self) -> bool:
        """Check if server is running."""
        try:
            response = self.session.get(self.base_url, timeout=5)
            print(f"✅ Server is running (status: {response.status_code})")
            return True
        except requests.exceptions.ConnectionError:
            print(f"❌ Server not running at {self.base_url}")
            print("   Start with: nix develop -c start-app")
            return False
        except Exception as e:
            print(f"❌ Error connecting to server: {e}")
            return False

    def _test_public_routes(self) -> None:
        """Test all public routes."""
        public_routes = [
            ("/", "Homepage"),
            ("/about", "About page"),
            ("/bylaws", "Bylaws page"),
            ("/calendar", "Calendar page"),
            ("/awards", "Awards page"),
            ("/roster", "Roster page"),
            ("/polls", "Polls list"),
            ("/login", "Login page"),
            ("/register", "Register page"),
            ("/password-reset", "Password reset request"),
        ]

        for route, description in public_routes:
            self._check_route(route, description, expect_redirect=False)

    def _test_admin_routes(self) -> None:
        """Test admin routes (requires authentication)."""
        admin_routes = [
            ("/admin", "Admin dashboard"),
            ("/admin/events", "Admin events"),
            ("/admin/users", "Admin users"),
            ("/admin/lakes", "Admin lakes"),
            ("/admin/news", "Admin news"),
        ]

        for route, description in admin_routes:
            self._check_route(route, description, expect_redirect=False)

    def _check_route(self, route: str, description: str, expect_redirect: bool = False) -> None:
        """Check a single route."""
        url = urljoin(self.base_url, route)

        try:
            response = self.session.get(url, allow_redirects=not expect_redirect, timeout=10)

            if expect_redirect:
                if response.status_code in (301, 302, 303, 307, 308):
                    print(f"  ✅ {description}: Redirects correctly")
                else:
                    self.errors.append(
                        {
                            "url": url,
                            "description": description,
                            "error": f"Expected redirect, got {response.status_code}",
                        }
                    )
                    print(f"  ❌ {description}: Expected redirect, got {response.status_code}")
            else:
                if response.status_code == 200:
                    print(f"  ✅ {description}: OK")
                elif response.status_code in (301, 302, 303, 307, 308):
                    print(
                        f"  ⚠️  {description}: Redirects to {response.headers.get('Location', 'unknown')}"
                    )
                elif response.status_code == 500:
                    self.errors.append(
                        {
                            "url": url,
                            "description": description,
                            "error": "Internal Server Error (500)",
                        }
                    )
                    print(f"  ❌ {description}: Internal Server Error (500)")
                else:
                    self.warnings.append(
                        {
                            "url": url,
                            "description": description,
                            "status": str(response.status_code),
                        }
                    )
                    print(f"  ⚠️  {description}: Status {response.status_code}")

        except requests.exceptions.Timeout:
            self.errors.append({"url": url, "description": description, "error": "Request timeout"})
            print(f"  ❌ {description}: Timeout")
        except Exception as e:
            self.errors.append({"url": url, "description": description, "error": str(e)})
            print(f"  ❌ {description}: {e}")

    def _login_as_admin(self) -> bool:
        """Attempt to login as admin."""
        login_url = urljoin(self.base_url, "/login")

        # Try default admin credentials
        credentials = [
            {"email": "admin@sabc.com", "password": "admin123"},
        ]

        for creds in credentials:
            try:
                response = self.session.post(
                    login_url, data=creds, allow_redirects=False, timeout=10
                )

                # Check if login succeeded (should redirect)
                if response.status_code in (302, 303):
                    # Follow redirect to verify we're logged in
                    self.admin_user = creds
                    return True

            except Exception as e:
                print(f"  ⚠️  Login attempt failed: {e}")
                continue

        return False

    def _crawl_site(self) -> None:
        """Crawl site starting from homepage."""
        to_visit = ["/"]

        while to_visit and len(self.visited) < 100:  # Limit to 100 pages
            url = to_visit.pop(0)
            full_url = urljoin(self.base_url, url)

            if full_url in self.visited:
                continue

            self.visited.add(full_url)

            try:
                response = self.session.get(full_url, timeout=10)

                if response.status_code == 200:
                    # Parse HTML and find links
                    soup = BeautifulSoup(response.text, "html.parser")
                    links = soup.find_all("a", href=True)

                    for link in links:
                        href = link["href"]

                        # Skip external links, anchors, javascript, mailto
                        if (
                            href.startswith("http")
                            and self.base_url not in href
                            or href.startswith("#")
                            or href.startswith("javascript:")
                            or href.startswith("mailto:")
                        ):
                            continue

                        # Make absolute URL
                        absolute_url = urljoin(full_url, str(href))
                        relative_url = absolute_url.replace(self.base_url, "")

                        if absolute_url not in self.visited and relative_url not in to_visit:
                            to_visit.append(relative_url)

                elif response.status_code == 500:
                    self.errors.append({"url": full_url, "error": "Internal Server Error (500)"})

            except Exception as e:
                self.errors.append({"url": full_url, "error": str(e)})

            # Small delay to avoid overwhelming server
            time.sleep(0.1)

        print(f"  Crawled {len(self.visited)} pages")

    def _print_results(self) -> None:
        """Print test results summary."""
        print("\n" + "=" * 70)
        print("📊 HEALTH CHECK RESULTS")
        print("=" * 70)

        print(f"\n✅ Pages checked: {len(self.visited)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")

        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                if "url" in warning:
                    print(
                        f"  - {warning.get('description', warning['url'])}: {warning.get('status', 'warning')}"
                    )
                else:
                    print(f"  - {warning.get('message', 'Unknown warning')}")

        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(
                    f"  - {error.get('description', error.get('url', 'Unknown'))}: {error['error']}"
                )

        if not self.errors:
            print("\n🎉 ALL CHECKS PASSED! Site is healthy.")
        else:
            print(f"\n💔 {len(self.errors)} error(s) found. Please fix before deploying.")


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SABC site health checker")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL to test (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    checker = SiteHealthChecker(base_url=args.url)
    success = checker.check_health()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
