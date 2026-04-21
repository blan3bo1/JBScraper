#!/usr/bin/env python3
"""
JBScrape - iOS Jailbreak Device Finder
Find iPhones with specific iOS versions on eBay and Swappa

Usage:
    python JBScrape.py                           # Interactive mode (eBay ~10 min, default)
    python JBScrape.py --sites swappa            # Swappa only (slow ~20 min)
    python JBScrape.py --sites ebay swappa       # Both sites (slow ~30 min)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import json
import time
import re
import os
import subprocess
from datetime import datetime
from urllib.parse import quote_plus
from collections import OrderedDict
import argparse


class JBScraper:
    """Unified scraper for finding iPhones with specific iOS versions"""

    def __init__(self, delay=1.5, headless=True, browser='chrome'):
        self.delay = delay
        self.headless = headless
        self.browser = browser.lower()
        self.driver = None
        self.all_listings = []

    def _fix_chromedriver_macos(self, driver_path):
        """No-op on Windows"""
        return False

    def _init_browser(self):
        """Initialize browser on demand"""
        if self.driver:
            return

        print(f"Initializing browser ({self.browser})...")

        if self.browser == 'firefox':
            opts = FirefoxOptions()
            if self.headless:
                opts.add_argument('--headless')
            try:
                self.driver = webdriver.Firefox(
                    service=FirefoxService(GeckoDriverManager().install()),
                    options=opts)
            except Exception as e:
                raise RuntimeError(f"Failed to start Firefox: {e}\n"
                                   "Make sure Firefox is installed.")

        elif self.browser == 'edge':
            opts = EdgeOptions()
            if self.headless:
                opts.add_argument('--headless=new')
            opts.add_argument('--no-sandbox')
            opts.add_argument('--disable-dev-shm-usage')
            try:
                self.driver = webdriver.Edge(
                    service=EdgeService(EdgeChromiumDriverManager().install()),
                    options=opts)
            except Exception as e:
                raise RuntimeError(f"Failed to start Edge: {e}")

        else:  # chrome (default)
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
            try:
                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to start Chrome: {e}\n"
                    "Make sure Google Chrome is installed."
                )

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        self.close()

    # ==================== iOS Version Utilities ====================

    # Jailbreakable iOS versions
    JAILBREAKABLE = {
        16: ['16', '16.0', '16.0.1', '16.0.2', '16.0.3',
             '16.1', '16.1.1', '16.1.2',
             '16.2', '16.2.1',
             '16.3', '16.3.1',
             '16.4', '16.4.1',
             '16.5', '16.5.1',
             '16.6', '16.6.1'],  # 16.6.1 is max jailbreakable
        17: ['17', '17.0'],  # Only 17.0 is jailbreakable
    }

    def generate_version_queries(self, major_versions):
        """Generate queries for jailbreakable iOS/iPadOS versions only"""
        queries = []
        devices = ['iPhone', 'iPad']

        for major in major_versions:
            major = int(major)
            for device in devices:
                if major in self.JAILBREAKABLE:
                    for ver in self.JAILBREAKABLE[major]:
                        queries.append(f'{device} "iOS {ver}"')
                        if ver == str(major):
                            queries.append(f'{device} iOS {ver}')
                else:
                    queries.append(f'{device} "iOS {major}"')
                    queries.append(f'{device} iOS {major}')

        return queries

    def extract_ios_version(self, text):
        """Extract iOS version from text"""
        if not text:
            return None
        text_lower = text.lower()
        match = re.search(r'\bios\s*(\d+(?:\.\d+)?(?:\.\d+)?)\b', text_lower)
        if match:
            return f"iOS {match.group(1)}"
        return None

    def is_device_compatible(self, title, ios_major):
        """
        Check if device can actually run the claimed iOS version.
        Filters out impossible combinations like iPhone 4 with iOS 16.
        """
        title_lower = title.lower()
        ios_major = int(ios_major)

        # iOS 16 requires iPhone 8 or later (A11 chip)
        # iOS 17 requires iPhone XS or later (A12 chip)

        # Devices that CANNOT run iOS 16+
        ios16_incompatible = [
            'iphone 4', 'iphone 5', 'iphone 6', 'iphone 7',
            'iphone se ' # Original SE (but not SE 2nd/3rd gen)
        ]

        # Devices that CANNOT run iOS 17+
        ios17_incompatible = ios16_incompatible + [
            'iphone 8', 'iphone x '  # Note: XS/XR CAN run iOS 17
        ]

        # Check for false positives
        if ios_major >= 16:
            for old_device in ios16_incompatible:
                if old_device in title_lower:
                    # Make sure it's not a newer device (e.g., "iPhone 14" contains no old device pattern)
                    # Check for false matches like "iPhone 4" in "iPhone 14"
                    if 'iphone 4' in title_lower and 'iphone 14' not in title_lower:
                        return False
                    if 'iphone 5' in title_lower and 'iphone 15' not in title_lower:
                        return False
                    if 'iphone 6' in title_lower and 'iphone 16' not in title_lower and '6s' not in title_lower:
                        return False
                    if 'iphone 7' in title_lower and '7 plus' not in title_lower:
                        # iPhone 7/7 Plus cannot run iOS 16
                        return False
                    if 'iphone se ' in title_lower and ('2nd' not in title_lower and '3rd' not in title_lower and '2020' not in title_lower and '2022' not in title_lower):
                        return False

        if ios_major >= 17:
            # iPhone 8/8 Plus and iPhone X cannot run iOS 17
            if 'iphone 8' in title_lower and 'iphone 18' not in title_lower:
                return False
            if 'iphone x ' in title_lower or title_lower.endswith('iphone x'):
                # But XS, XR, XS Max CAN run iOS 17
                if 'xs' not in title_lower and 'xr' not in title_lower:
                    return False

        return True

    def matches_target_versions(self, text, target_majors):
        """Check if text contains iOS version matching target majors (16, 17, etc.)"""
        if not text or '?' in text:
            return False
        text_lower = text.lower()
        for major in target_majors:
            pattern = rf'\bios\s*{major}(?:\.\d+)?(?:\.\d+)?\b'
            if re.search(pattern, text_lower):
                return True
        return False

    def is_jailbreakable_version(self, ios_version):
        """Check if the iOS version is actually jailbreakable"""
        if not ios_version:
            return False

        # Extract version number (e.g., "iOS 16.5.1" -> "16.5.1")
        ver = ios_version.replace('iOS ', '').strip()

        # Check against known jailbreakable versions
        for major, versions in self.JAILBREAKABLE.items():
            if ver in versions:
                return True

        # Special case: "iOS 16" or "iOS 17" without minor version
        # Accept base versions as potentially jailbreakable
        if ver in ['16', '17']:
            return True

        return False

    # ==================== eBay Scraper ====================

    def search_ebay(self, major_versions, max_pages=2, verbose=True):
        """Search eBay for iPhones with specific iOS versions"""
        self._init_browser()

        queries = self.generate_version_queries(major_versions)
        seen_ids = set()
        listings = []

        if verbose:
            print(f"\n{'='*60}")
            print("SEARCHING EBAY")
            print(f"{'='*60}")
            print(f"Target iOS versions: {', '.join(str(v) for v in major_versions)}")
            print(f"Total queries to run: {len(queries)}")

        for i, query in enumerate(queries, 1):
            if verbose:
                print(f"\n[{i}/{len(queries)}] {query}")

            encoded_query = quote_plus(query)
            new_count = 0

            for page in range(1, max_pages + 1):
                # eBay search URL with Cell Phones category and Used condition
                url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&_sacat=9355&LH_ItemCondition=3000&_pgn={page}"

                try:
                    self.driver.get(url)
                    time.sleep(2)

                    # Find listings - try multiple selectors
                    items = self.driver.find_elements(By.CSS_SELECTOR, 'li[data-listingid]')
                    if not items:
                        items = self.driver.find_elements(By.CSS_SELECTOR, '.srp-list > li.s-card')

                    if not items:
                        break

                    for item in items:
                        try:
                            listing = self._parse_ebay_item(item)
                            if not listing or not listing.get('title'):
                                continue

                            item_id = listing.get('item_id', '')
                            title = listing.get('title', '')

                            # Skip duplicates
                            if item_id in seen_ids:
                                continue

                            # Extract and validate iOS version
                            ios_ver = self.extract_ios_version(title)
                            if not ios_ver:
                                continue

                            if not self.matches_target_versions(title, major_versions):
                                continue

                            # Check device compatibility (filter impossible combos like iPhone 4 + iOS 16)
                            ios_major = ios_ver.replace('iOS ', '').split('.')[0]
                            if not self.is_device_compatible(title, ios_major):
                                continue

                            # Check if version is actually jailbreakable
                            if not self.is_jailbreakable_version(ios_ver):
                                continue

                            seen_ids.add(item_id)
                            listing['ios_version'] = ios_ver
                            listing['source'] = 'ebay'
                            listings.append(listing)
                            new_count += 1

                        except Exception:
                            continue

                    time.sleep(self.delay)

                except Exception as e:
                    if verbose:
                        print(f"  Error: {e}")
                    break

            if verbose:
                if new_count > 0:
                    print(f"  Found {new_count} new listings")

        if verbose:
            print(f"\n{'='*60}")
            print(f"eBay Total: {len(listings)} unique listings")
            print(f"{'='*60}")

        return listings

    def _parse_ebay_item(self, item):
        """Parse a single eBay listing element"""
        listing = {'scraped_at': datetime.now().isoformat()}

        try:
            # Item ID
            item_id = item.get_attribute('data-listingid')
            if item_id:
                listing['item_id'] = item_id

            # URL
            for selector in ['a[href*="/itm/"]', 'a.s-card__link', 'a']:
                try:
                    link_elem = item.find_element(By.CSS_SELECTOR, selector)
                    href = link_elem.get_attribute('href')
                    if href and '/itm/' in href:
                        listing['url'] = href
                        if not listing.get('item_id'):
                            match = re.search(r'/itm/(\d+)', href)
                            if match:
                                listing['item_id'] = match.group(1)
                        break
                except:
                    continue

            # Title
            for selector in ['.s-card__title', '.s-item__title', '[class*="title"]', 'h3', 'span']:
                try:
                    title_elem = item.find_element(By.CSS_SELECTOR, selector)
                    text = title_elem.text.strip()
                    if text and len(text) > 5:
                        listing['title'] = text
                        break
                except:
                    continue

            # Price
            for selector in ['.s-card__price', '.s-item__price', '[class*="price"]']:
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, selector)
                    text = price_elem.text.strip()
                    if text and '$' in text:
                        listing['price'] = text.split('\n')[0]  # First line only
                        break
                except:
                    continue

            return listing

        except Exception:
            return None

    # ==================== Swappa Scraper ====================

    def search_swappa(self, major_versions, max_listings_per_model=20, verbose=True):
        """
        Search Swappa for iPhones with specific iOS versions.
        Visits each listing page and checks ONLY seller description (not comments).
        """
        self._init_browser()

        # iPhone models to search
        models = [
            'apple-iphone-15-pro-max', 'apple-iphone-15-pro', 'apple-iphone-15-plus', 'apple-iphone-15',
            'apple-iphone-14-pro-max', 'apple-iphone-14-pro', 'apple-iphone-14-plus', 'apple-iphone-14',
            'apple-iphone-13-pro-max', 'apple-iphone-13-pro', 'apple-iphone-13-mini', 'apple-iphone-13',
            'apple-iphone-12-pro-max', 'apple-iphone-12-pro', 'apple-iphone-12-mini', 'apple-iphone-12',
            'apple-iphone-11-pro-max', 'apple-iphone-11-pro', 'apple-iphone-11',
            'apple-iphone-xs-max', 'apple-iphone-xs', 'apple-iphone-xr', 'apple-iphone-x',
            'apple-iphone-se-3rd-gen', 'apple-iphone-se-2nd-gen',
            'apple-iphone-8-plus', 'apple-iphone-8',
        ]

        seen_ids = set()
        listings = []

        if verbose:
            print(f"\n{'='*60}")
            print("SEARCHING SWAPPA")
            print(f"{'='*60}")
            print(f"Target iOS versions: {', '.join(str(v) for v in major_versions)}")
            print(f"Models to search: {len(models)}")
            print("(Checking seller descriptions only, not comments)")

        for i, model in enumerate(models, 1):
            if verbose:
                print(f"\n[{i}/{len(models)}] {model}")

            url = f"https://swappa.com/listings/{model}"

            try:
                self.driver.get(url)
                time.sleep(2)

                # Get listing URLs
                listing_links = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'a[href*="/listing/view/"]'
                )

                # Get unique listing URLs
                listing_urls = []
                for link in listing_links:
                    href = link.get_attribute('href')
                    if href:
                        listing_id = href.split('/')[-1]
                        if listing_id not in seen_ids:
                            seen_ids.add(listing_id)
                            listing_urls.append((listing_id, href))
                            if len(listing_urls) >= max_listings_per_model:
                                break

                # Visit each listing and check seller description
                model_found = 0
                for listing_id, listing_url in listing_urls:
                    result = self._check_swappa_listing(listing_id, listing_url, major_versions)
                    if result:
                        listings.append(result)
                        model_found += 1
                        if verbose:
                            print(f"  FOUND: {result['ios_version']} - {listing_id}")
                    time.sleep(0.5)

                if verbose and model_found == 0:
                    print(f"  No iOS listings found")

            except Exception as e:
                if verbose:
                    print(f"  Error: {e}")
                continue

        if verbose:
            print(f"\n{'='*60}")
            print(f"Swappa Total: {len(listings)} listings")
            print(f"{'='*60}")

        return listings

    def _check_swappa_listing(self, listing_id, listing_url, major_versions):
        """
        Check a single Swappa listing for iOS version in SELLER DESCRIPTION ONLY.
        Extracts from JSON-LD and Damage Description, NOT from comments.
        """
        try:
            self.driver.get(listing_url)
            time.sleep(1.5)

            seller_text = ""

            # 1. Extract from JSON-LD schema (most reliable - seller's description)
            try:
                scripts = self.driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
                for script in scripts:
                    content = script.get_attribute('innerHTML')
                    if '"description"' in content:
                        # Extract description field from JSON
                        match = re.search(r'"description"\s*:\s*"([^"]+)"', content)
                        if match:
                            seller_text += match.group(1) + " "
            except:
                pass

            # 2. Get the Damage Description section (seller-provided)
            try:
                # Find "Damage Description" header and get next sibling
                damage_desc = self.driver.find_element(By.XPATH,
                    "//h3[contains(text(),'Damage Description')]/following-sibling::div[1]")
                seller_text += damage_desc.text + " "
            except:
                pass

            # 3. Get page title (h1)
            try:
                h1 = self.driver.find_element(By.TAG_NAME, 'h1')
                seller_text += h1.text + " "
            except:
                pass

            # 4. Get price
            price = ""
            try:
                price_elem = self.driver.find_element(By.CSS_SELECTOR, '[itemprop="price"]')
                price = f"${price_elem.get_attribute('content') or price_elem.text}"
            except:
                pass

            # Check if iOS version in seller text
            ios_ver = self.extract_ios_version(seller_text)
            if not ios_ver:
                return None

            if not self.matches_target_versions(seller_text, major_versions):
                return None

            # Check if jailbreakable
            if not self.is_jailbreakable_version(ios_ver):
                return None

            # Check device compatibility
            ios_major = ios_ver.replace('iOS ', '').split('.')[0]
            if not self.is_device_compatible(seller_text, ios_major):
                return None

            return {
                'item_id': listing_id,
                'url': listing_url,
                'title': seller_text[:100].strip(),
                'ios_version': ios_ver,
                'price': price,
                'source': 'swappa',
                'scraped_at': datetime.now().isoformat()
            }

        except Exception:
            return None

    # ==================== Results Processing ====================

    def get_device_info(self, title):
        """Extract device model from title and return (model_name, sort_order)"""
        title_lower = title.lower()

        device_map = [
            # ── iPhones ──────────────────────────────────────────────────────
            ('15 pro max', 'iPhone 15 Pro Max', 1),
            ('15 pro', 'iPhone 15 Pro', 2),
            ('15 plus', 'iPhone 15 Plus', 3),
            ('iphone 15', 'iPhone 15', 4),
            ('14 pro max', 'iPhone 14 Pro Max', 5),
            ('14 pro', 'iPhone 14 Pro', 6),
            ('14 plus', 'iPhone 14 Plus', 7),
            ('iphone 14', 'iPhone 14', 8),
            ('13 pro max', 'iPhone 13 Pro Max', 9),
            ('13 pro', 'iPhone 13 Pro', 10),
            ('13 mini', 'iPhone 13 Mini', 11),
            ('iphone 13', 'iPhone 13', 12),
            ('12 pro max', 'iPhone 12 Pro Max', 13),
            ('12 pro', 'iPhone 12 Pro', 14),
            ('12 mini', 'iPhone 12 Mini', 15),
            ('iphone 12', 'iPhone 12', 16),
            ('11 pro max', 'iPhone 11 Pro Max', 17),
            ('11 pro', 'iPhone 11 Pro', 18),
            ('iphone 11', 'iPhone 11', 19),
            ('xs max', 'iPhone XS Max', 20),
            ('iphone xs', 'iPhone XS', 21),
            ('iphone xr', 'iPhone XR', 22),
            ('iphone x', 'iPhone X', 23),
            ('se 3', 'iPhone SE 3rd Gen', 24),
            ('se 2022', 'iPhone SE 3rd Gen', 24),
            ('3rd gen', 'iPhone SE 3rd Gen', 24),
            ('se 2', 'iPhone SE 2nd Gen', 25),
            ('se 2020', 'iPhone SE 2nd Gen', 25),
            ('2nd gen', 'iPhone SE 2nd Gen', 25),
            ('iphone se', 'iPhone SE', 26),
            ('8 plus', 'iPhone 8 Plus', 27),
            ('iphone 8', 'iPhone 8', 28),
            ('iphone 7', 'iPhone 7', 29),
            # ── iPad Pro ─────────────────────────────────────────────────────
            ('ipad pro 12.9', 'iPad Pro 12.9"', 100),
            ('ipad pro 11', 'iPad Pro 11"', 101),
            ('ipad pro 10.5', 'iPad Pro 10.5"', 102),
            ('ipad pro 9.7', 'iPad Pro 9.7"', 103),
            ('ipad pro', 'iPad Pro', 104),
            # ── iPad Air ─────────────────────────────────────────────────────
            ('ipad air 5', 'iPad Air (5th gen)', 110),
            ('ipad air 4', 'iPad Air (4th gen)', 111),
            ('ipad air 3', 'iPad Air (3rd gen)', 112),
            ('ipad air 2', 'iPad Air 2', 113),
            ('ipad air', 'iPad Air', 114),
            # ── iPad mini ────────────────────────────────────────────────────
            ('ipad mini 6', 'iPad mini (6th gen)', 120),
            ('ipad mini 5', 'iPad mini (5th gen)', 121),
            ('ipad mini 4', 'iPad mini 4', 122),
            ('ipad mini 3', 'iPad mini 3', 123),
            ('ipad mini 2', 'iPad mini 2', 124),
            ('ipad mini', 'iPad mini', 125),
            # ── iPad (standard) ──────────────────────────────────────────────
            ('ipad 10th', 'iPad (10th gen)', 130),
            ('ipad 9th', 'iPad (9th gen)', 131),
            ('ipad 8th', 'iPad (8th gen)', 132),
            ('ipad 7th', 'iPad (7th gen)', 133),
            ('ipad 6th', 'iPad (6th gen)', 134),
            ('ipad 5th', 'iPad (5th gen)', 135),
            ('ipad', 'iPad', 139),
        ]

        for pattern, name, order in device_map:
            if pattern in title_lower:
                return name, order

        return 'Other Device', 50

    def parse_price(self, price_str):
        """Parse price string to float"""
        if not price_str:
            return 999999
        price_str = price_str.replace('$', '').replace(',', '').strip()
        try:
            return float(price_str.split()[0])
        except:
            return 999999

    def process_results(self, listings):
        """Process and enrich listings with device info and price parsing"""
        for listing in listings:
            title = listing.get('title', '')
            device, order = self.get_device_info(title)
            listing['device'] = device
            listing['device_order'] = order
            listing['price_num'] = self.parse_price(listing.get('price', ''))
            listing['is_jailbroken'] = 'jailbr' in title.lower()

            # Extract storage
            storage_match = re.search(r'(\d+)\s*[GT]B', title, re.I)
            if storage_match:
                listing['storage'] = storage_match.group(0)

        # Sort by device order, then by price
        listings.sort(key=lambda x: (x['device_order'], x['price_num']))

        return listings

    def group_by_device(self, listings):
        """Group listings by device model"""
        grouped = OrderedDict()
        for listing in listings:
            device = listing.get('device', 'Other')
            if device not in grouped:
                grouped[device] = []
            grouped[device].append(listing)
        return grouped

    # ==================== Output ====================

    def save_json(self, listings, filename):
        """Save results to JSON file"""
        results = {
            'searched_at': datetime.now().isoformat(),
            'total_count': len(listings),
            'listings': listings
        }
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Saved {len(listings)} listings to {filename}")

    def open_in_notepad(self, listings, title="JBScrape Results"):
        """Write results to a temp .txt file and open it in Notepad"""
        processed = self.process_results(listings)
        grouped = self.group_by_device(processed)

        lines = []
        lines.append(f"JBScrape Results — {datetime.now().strftime('%B %d, %Y %H:%M')}")
        lines.append(f"Total listings: {len(listings)}")
        lines.append("=" * 70)

        for device, items in grouped.items():
            lines.append(f"\n{device} ({len(items)} listing{'s' if len(items) != 1 else ''})")
            lines.append("-" * 40)
            for item in items:
                price   = item.get('price', 'N/A')
                ios     = item.get('ios_version', '?')
                storage = item.get('storage', '')
                jb      = ' [JB]' if item.get('is_jailbroken') else ''
                source  = item.get('source', 'unknown')
                if source == 'ebay':
                    url = f"https://www.ebay.com/itm/{item.get('item_id', '')}"
                else:
                    url = item.get('url', '')
                lines.append(f"  {price:12} | {storage:6} | {ios}{jb} | {source}")
                lines.append(f"  {url}")
                lines.append("")

        lines.append("=" * 70)
        lines.append("JB = Jailbroken | Generated by JBScrape")

        # Write to temp file and open in Notepad
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt',
            prefix='jbscrape_', delete=False,
            encoding='utf-8'
        )
        tmp.write('\n'.join(lines))
        tmp.close()

        print(f"Opening results in Notepad: {tmp.name}")
        subprocess.Popen(['notepad.exe', tmp.name])

    def display_results(self, listings, limit=30):
        """Display results in terminal"""
        processed = self.process_results(listings)
        grouped = self.group_by_device(processed)

        print(f"\n{'='*70}")
        print(f"RESULTS: {len(listings)} listings")
        print(f"{'='*70}")

        count = 0
        for device, items in grouped.items():
            if count >= limit:
                break
            print(f"\n{device} ({len(items)})")
            print("-" * 40)
            for item in items[:5]:  # Show max 5 per device
                if count >= limit:
                    break
                price = item.get('price', 'N/A')
                ios = item.get('ios_version', '?')
                storage = item.get('storage', '')
                jb = ' [JB]' if item.get('is_jailbroken') else ''
                source = item.get('source', '')
                print(f"  {price:12} | {storage:6} | {ios:12} | {source}{jb}")
                count += 1


def interactive_mode():
    """Run in interactive mode with user prompts"""
    print("\n" + "="*60)
    print("  JBScrape - iOS Jailbreak Device Finder")
    print("="*60)
    print("\nSearching for jailbreakable versions:")
    print("  iOS 16.0 - 16.6.1")
    print("  iOS 17.0")

    # Fixed to jailbreakable versions only
    major_versions = [16, 17]

    # Get sites
    print("\nWhich sites do you want to search?")
    print("  1. eBay only (~10 min) (default)")
    print("  2. Swappa only (SLOW - ~20 minutes)")
    print("  3. Both (SLOW - ~30 minutes)")
    sites_input = input("Enter choice (1/2/3): ").strip() or "1"

    sites = []
    if sites_input == "1":
        sites = ['ebay']
    elif sites_input == "2":
        print("\n  WARNING: Swappa search is slow (~20 minutes)")
        print("  It visits each listing page individually to check iOS version.")
        confirm = input("  Continue? (y/N): ").strip().lower()
        if confirm != 'y':
            print("  Falling back to eBay only.")
            sites = ['ebay']
        else:
            sites = ['swappa']
    else:
        print("\n  WARNING: Searching both sites is slow (~30 minutes)")
        print("  Swappa visits each listing page individually to check iOS version.")
        confirm = input("  Continue with both? (y/N): ").strip().lower()
        if confirm != 'y':
            print("  Falling back to eBay only.")
            sites = ['ebay']
        else:
            sites = ['ebay', 'swappa']

    # Headless?
    print("\nShow browser window? (y/N): ", end="")
    show_browser = input().strip().lower() == 'y'

    # Create note?
    print("Open results in Notepad? (Y/n): ", end="")
    create_note = input().strip().lower() != 'n'

    return major_versions, sites, show_browser, create_note


def main():
    parser = argparse.ArgumentParser(
        description='JBScrape - Find jailbreakable iPhones (iOS 16.0-16.6.1, iOS 17.0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python JBScrape.py                    # Search eBay (~10 min, default)
  python JBScrape.py --sites swappa     # Swappa only (slow ~20 min)
  python JBScrape.py --sites ebay swappa  # Both sites (slow ~30 min)
  python JBScrape.py --no-headless      # Show browser
  python JBScrape.py --note             # Create Notes app entry
        """
    )

    parser.add_argument('--sites', nargs='+', choices=['ebay', 'swappa'],
                        default=['ebay'],
                        help='Sites to search (default: ebay). Note: swappa is slow (~20 min)')
    parser.add_argument('--pages', type=int, default=2,
                        help='Pages to search per eBay query (default: 2)')
    parser.add_argument('--delay', type=float, default=1.5,
                        help='Delay between requests (default: 1.5)')
    parser.add_argument('--no-headless', action='store_true',
                        help='Show browser window')
    parser.add_argument('--note', action='store_true',
                        help='Open results in Notepad when done')
    parser.add_argument('--output', '-o', type=str,
                        help='Output JSON filename')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Run in interactive mode')
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'edge'],
                        default='chrome',
                        help='Browser to use (default: chrome)')

    args = parser.parse_args()

    # Fixed to jailbreakable versions only
    major_versions = [16, 17]

    # Interactive mode is default unless specific args are passed
    has_args = args.sites != ['ebay'] or args.no_headless or args.note or args.output

    if args.interactive or not has_args:
        major_versions, sites, show_browser, create_note = interactive_mode()
        headless = not show_browser
    else:
        sites = args.sites
        headless = not args.no_headless
        create_note = args.note

    # Create scraper
    scraper = JBScraper(delay=args.delay, headless=headless, browser=args.browser)

    all_listings = []

    try:
        # Search eBay
        if 'ebay' in sites:
            ebay_listings = scraper.search_ebay(major_versions, max_pages=args.pages)
            all_listings.extend(ebay_listings)

        # Search Swappa
        if 'swappa' in sites:
            swappa_listings = scraper.search_swappa(major_versions)
            all_listings.extend(swappa_listings)

    except KeyboardInterrupt:
        print("\n\nStopped early — showing results collected so far...")

    finally:
        scraper.close()

    if not all_listings:
        print("\nNo listings found!")
        return

    # Process and display results
    processed = scraper.process_results(all_listings)
    scraper.display_results(processed)

    # Save JSON to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = args.output or os.path.join(script_dir, "jbscrape_results.json")
    scraper.save_json(processed, output_file)

    # Open in Notepad
    if create_note:
        title = "Jailbreakable Devices"
        scraper.open_in_notepad(processed, title)

    print(f"\nDone! Found {len(all_listings)} total listings.")


if __name__ == "__main__":
    main()
