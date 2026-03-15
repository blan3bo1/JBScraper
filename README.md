# JBScrape

A scraper that finds iPhones and iPads listed on eBay and Swappa running jailbreakable iOS versions (iOS 16.0–16.6.1 and iOS 17.0).

Includes a graphical UI that works on both macOS and Windows.

Original script by [zeroxjf](https://github.com/zeroxjf/JBScrape). This fork adds browser selection, iPad support, a cross-platform GUI, and a Windows port.

---

## What's in this repo

| File | Platform | Description |
|---|---|---|
| `JBScrape.py` | macOS | Scraper — saves results to macOS Notes |
| `JBScrape_windows.py` | Windows | Scraper — opens results in Notepad |
| `jbscrape_ui.py` | macOS + Windows | Graphical UI wrapper for either script |
| `requirements.txt` | Both | Python dependencies |

---

## Jailbreakable iOS versions

| iOS version | Jailbreak tool |
|---|---|
| 16.0 – 16.5 | Dopamine |
| 16.5.1 – 16.6.1 | nathanlr |
| 17.0 | nathanlr (via TrollStore) |

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/blan3bo1/JBScraper.git
cd JBScraper
```

### 2. Install Python dependencies

**macOS:**
```bash
pip3 install -r requirements.txt --break-system-packages
```

**Windows:**
```bash
pip install -r requirements.txt
```

### 3. Install a browser WebDriver

The scraper drives a real browser. You need a WebDriver that matches your installed browser.

| Browser | macOS | Windows |
|---|---|---|
| Chrome | `brew install --cask chromedriver` | Auto-downloaded by `webdriver-manager` |
| Firefox | `brew install geckodriver` | Auto-downloaded by `webdriver-manager` |
| Edge | Auto-downloaded | Auto-downloaded |

> **macOS Chrome tip:** If chromedriver is blocked by Gatekeeper, run:
> ```bash
> xattr -cr /opt/homebrew/bin/chromedriver
> ```

> **macOS Firefox tip:** Firefox must be installed in `/Applications/Firefox.app`. The script finds it there automatically.

---

## Usage

### Graphical UI (recommended)

The UI works on both macOS and Windows. It automatically picks the right script for your platform.

```bash
# macOS
python3 jbscrape_ui.py

# Windows
python jbscrape_ui.py
```

#### UI controls

| Control | Description |
|---|---|
| **jbscrape.py field** | Path to the script — auto-detected on launch |
| **Python field** | Path to your Python interpreter |
| **--browser** | Choose Chrome, Firefox, or Edge |
| **--sites** | Toggle eBay and/or Swappa |
| **--pages** | eBay result pages per query (default: 3) |
| **--delay** | Seconds between requests (default: 2) |
| **--no-headless** | Show the browser window while scraping |
| **--interactive** | Use JBScrape's interactive prompt mode |
| **--note** | Open results in Notes (macOS) or Notepad (Windows) |
| **▶ RUN** | Start the scraper |
| **■ STOP** | Stop — results found so far are still saved and shown |
| **› input box** | Send a response to interactive menu prompts |
| **Ctrl+C** | Interrupt the current scan without killing the process (macOS only) |

---

### Command line

**macOS:**
```bash
# Interactive mode (default)
python3 JBScrape.py

# eBay only, Chrome, 3 pages
python3 JBScrape.py --sites ebay --browser chrome --pages 3

# Both sites, Firefox, show browser, save to Notes
python3 JBScrape.py --sites ebay swappa --browser firefox --no-headless --note

# Save results to a specific JSON file
python3 JBScrape.py --output ~/Desktop/results.json
```

**Windows:**
```bat
:: Interactive mode
python JBScrape_windows.py

:: Both sites, Edge, open in Notepad
python JBScrape_windows.py --sites ebay swappa --browser edge --note
```

#### All arguments

| Argument | Default | Description |
|---|---|---|
| `--sites` | `ebay` | Sites to search: `ebay`, `swappa`, or both |
| `--browser` | `chrome` | Browser: `chrome`, `firefox`, or `edge` |
| `--pages` | `2` | eBay result pages per query |
| `--delay` | `1.5` | Seconds between requests |
| `--no-headless` | off | Show the browser window |
| `--note` | off | Output results to Notes / Notepad |
| `--output` | auto | Custom path for JSON output |
| `--interactive` | off | Force interactive prompt mode |

---

## Output

Every run produces:

- **Terminal output** — results grouped by device, sorted by price
- **JSON file** — saved to the script folder as `jbscrape_results.json` (or `--output` path)
- **Notes / Notepad** — if `--note` is passed

Results are grouped by device model (iPhone 12, iPad Pro 11", etc.) and show price, storage, iOS version, source (eBay/Swappa), and a `[JB]` tag if the seller mentions jailbreak.

---

## Devices searched

Searches for both iPhones and iPads. Device compatibility is filtered automatically — listings claiming impossible combinations (e.g. iPhone 6 on iOS 16) are dropped.

**iPhones:** iPhone 7 through iPhone 15 Pro Max, all SE variants  
**iPads:** All iPad Pro, iPad Air, iPad mini, and standard iPad models that support iOS 16+

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'webdriver_manager'`**

Dependencies aren't installed for the Python version you're using. Run:
```bash
/path/to/your/python3 -m pip install -r requirements.txt --break-system-packages
```

**`SessionNotCreatedException: unable to find binary`** (Firefox, macOS)

Firefox must be installed in `/Applications/Firefox.app`.

**`chromedriver` killed immediately on macOS (exit code -9)**

```bash
xattr -cr /opt/homebrew/bin/chromedriver
```

**UI input not registering on macOS**

The UI uses a pseudo-terminal (PTY) so JBScrape's interactive prompts work. If input still doesn't work, try running the script directly in Terminal first to confirm it works outside the UI.

**Swappa is very slow**

Swappa requires visiting every listing page individually to find the iOS version. Expect ~20 minutes. eBay takes ~10 minutes. Using both takes ~30 minutes.

---

## Credits

- Original [JBScrape](https://github.com/zeroxjf/JBScrape) by zeroxjf
- Browser selection, iPad support, Windows port, stop-and-show-results, and GUI by Blan3bo1
