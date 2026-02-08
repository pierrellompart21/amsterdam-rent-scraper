"""Stealth browser utilities for bypassing bot detection.

This module provides a StealthBrowser class that wraps undetected-chromedriver
and implements human-like behavior to help bypass anti-bot measures.

Usage:
    with StealthBrowser() as browser:
        browser.get("https://example.com")
        html = browser.page_source
"""

import random
import time
from typing import Optional

try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    uc = None

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from rich.console import Console

console = Console()


# User agents that look realistic
REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Realistic viewport sizes
VIEWPORT_SIZES = [
    (1920, 1080),
    (1680, 1050),
    (1440, 900),
    (1536, 864),
    (2560, 1440),
]


def _find_chrome() -> str | None:
    """Find Chrome executable path."""
    if not UNDETECTED_AVAILABLE:
        return None
    try:
        from undetected_chromedriver import find_chrome_executable
        return find_chrome_executable()
    except Exception:
        return None


def is_chrome_installed() -> bool:
    """Check if Chrome browser is installed and can be found."""
    return _find_chrome() is not None


def is_stealth_available() -> bool:
    """Check if stealth packages are installed."""
    return UNDETECTED_AVAILABLE and SELENIUM_AVAILABLE


class StealthBrowser:
    """A stealth browser using undetected-chromedriver with human-like behavior.

    This browser attempts to bypass bot detection by:
    - Using undetected-chromedriver to avoid automation detection
    - Randomizing viewport size and user agent
    - Adding human-like delays and scrolling behavior
    - Simulating mouse movements
    """

    def __init__(
        self,
        headless: bool = True,
        locale: str = "en-US",
        random_delays: bool = True,
    ):
        """Initialize the stealth browser.

        Args:
            headless: Run browser in headless mode (default True)
            locale: Browser locale (default "en-US")
            random_delays: Add random delays for human-like behavior
        """
        if not is_stealth_available():
            raise ImportError(
                "Stealth browser requires 'undetected-chromedriver' and 'selenium'. "
                "Install with: pip install undetected-chromedriver selenium"
            )

        self.headless = headless
        self.locale = locale
        self.random_delays = random_delays
        self.driver = None

        # Random viewport and user agent
        self.viewport = random.choice(VIEWPORT_SIZES)
        self.user_agent = random.choice(REALISTIC_USER_AGENTS)

    def __enter__(self):
        """Start the browser."""
        self._start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the browser."""
        self.close()

    def _start(self):
        """Start the undetected Chrome browser."""
        # Check if Chrome is installed before attempting to start
        chrome_path = _find_chrome()
        if chrome_path is None:
            raise RuntimeError(
                "Chrome browser not found. Stealth mode requires Google Chrome to be installed.\n"
                "On macOS: brew install --cask google-chrome\n"
                "On Ubuntu: sudo apt install google-chrome-stable\n"
                "On Windows: Download from https://www.google.com/chrome/"
            )

        options = uc.ChromeOptions()

        # Set viewport size
        width, height = self.viewport
        options.add_argument(f"--window-size={width},{height}")

        # Set language/locale
        options.add_argument(f"--lang={self.locale}")

        # Additional stealth settings
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")

        # Headless mode (use new headless if available)
        if self.headless:
            options.add_argument("--headless=new")

        # Start undetected Chrome
        # Note: headless is set via options argument (--headless=new), not the headless parameter
        # Passing headless=True to uc.Chrome in newer versions can cause "Binary Location Must be a String" errors
        self.driver = uc.Chrome(
            options=options,
            use_subprocess=True,
        )

        # Set realistic viewport
        self.driver.set_window_size(width, height)

        # Execute CDP commands for extra stealth
        self._apply_stealth_patches()

    def _apply_stealth_patches(self):
        """Apply additional stealth patches via CDP."""
        if not self.driver:
            return

        # Override navigator.webdriver
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    // Override plugins
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });

                    // Override languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });

                    // Remove automation indicators
                    window.chrome = { runtime: {} };

                    // Override permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """
            }
        )

    def get(self, url: str, wait_for_selector: Optional[str] = None, timeout: int = 30):
        """Navigate to a URL with human-like behavior.

        Args:
            url: The URL to navigate to
            wait_for_selector: Optional CSS selector to wait for
            timeout: Timeout in seconds
        """
        if not self.driver:
            raise RuntimeError("Browser not started. Use 'with StealthBrowser() as browser:'")

        # Random delay before navigation (like a human reading/thinking)
        if self.random_delays:
            time.sleep(random.uniform(0.5, 2.0))

        self.driver.get(url)

        # Wait for selector if specified
        if wait_for_selector:
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                )
            except Exception:
                pass  # Continue even if selector not found

        # Human-like behavior after page load
        if self.random_delays:
            time.sleep(random.uniform(1.0, 3.0))

    def human_scroll(self, scroll_count: int = 3, scroll_pause: float = 1.5):
        """Perform human-like scrolling behavior.

        Args:
            scroll_count: Number of scroll actions
            scroll_pause: Base pause between scrolls (randomized)
        """
        if not self.driver:
            return

        for i in range(scroll_count):
            # Random scroll distance
            scroll_amount = random.randint(300, 800)

            # Sometimes scroll up slightly (like a human overshooting)
            if random.random() < 0.2:
                self.driver.execute_script(f"window.scrollBy(0, -{random.randint(50, 150)})")
                time.sleep(random.uniform(0.3, 0.7))

            # Scroll down
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount})")

            # Random pause with some variation
            time.sleep(random.uniform(scroll_pause * 0.5, scroll_pause * 1.5))

    def random_mouse_movement(self):
        """Simulate random mouse movements (helps avoid detection)."""
        if not self.driver:
            return

        try:
            actions = ActionChains(self.driver)

            # Get viewport size
            viewport_width = self.driver.execute_script("return window.innerWidth")
            viewport_height = self.driver.execute_script("return window.innerHeight")

            # Move to a few random positions
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, viewport_width - 100)
                y = random.randint(100, viewport_height - 100)

                # Move with a slight pause
                actions.move_by_offset(x // 10, y // 10)
                actions.pause(random.uniform(0.1, 0.3))

            actions.perform()
        except Exception:
            pass  # Mouse movements are optional enhancements

    def human_type(self, element, text: str, delay_range: tuple = (0.05, 0.15)):
        """Type text with human-like delays between keystrokes.

        Args:
            element: The WebElement to type into
            text: The text to type
            delay_range: Tuple of (min_delay, max_delay) between keystrokes
        """
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(*delay_range))

    @property
    def page_source(self) -> str:
        """Get the current page HTML source."""
        if not self.driver:
            raise RuntimeError("Browser not started")
        return self.driver.page_source

    @property
    def current_url(self) -> str:
        """Get the current URL."""
        if not self.driver:
            raise RuntimeError("Browser not started")
        return self.driver.current_url

    def find_element(self, by: str, value: str):
        """Find a single element by selector.

        Args:
            by: Locator strategy (use selenium.webdriver.common.by.By constants)
            value: The locator value

        Returns:
            WebElement if found
        """
        if not self.driver:
            raise RuntimeError("Browser not started")
        return self.driver.find_element(by, value)

    def find_elements(self, by: str, value: str):
        """Find multiple elements by selector.

        Args:
            by: Locator strategy (use selenium.webdriver.common.by.By constants)
            value: The locator value

        Returns:
            List of WebElements
        """
        if not self.driver:
            raise RuntimeError("Browser not started")
        return self.driver.find_elements(by, value)

    def execute_script(self, script: str, *args):
        """Execute JavaScript in the browser.

        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script

        Returns:
            The script's return value
        """
        if not self.driver:
            raise RuntimeError("Browser not started")
        return self.driver.execute_script(script, *args)

    def wait_for_timeout(self, milliseconds: int):
        """Wait for a specified time (like Playwright's wait_for_timeout).

        Args:
            milliseconds: Time to wait in milliseconds
        """
        time.sleep(milliseconds / 1000)

    def close(self):
        """Close the browser and clean up."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
