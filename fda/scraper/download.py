from pathlib import Path
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = BASE_DIR / "data" / "raw"

FDA_LOGS_PAGE = (
    "https://www.fda.gov/regulatory-information/"
    "freedom-information/fda-foia-logs"
)

OUTPUT_FILE = RAW_DATA_DIR / "fda_foia_closed_log_latest.xlsx"


# ---------------------------------------------------------
# BROWSER SETUP
# ---------------------------------------------------------

def create_browser():
    """
    Create a Microsoft Edge browser configured to
    automatically download Excel files into data/raw.
    """

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    options = Options()

    # Automatically download files without asking.
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(RAW_DATA_DIR.resolve()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )

    # Keep the browser visible so we can see what happens.
    options.add_argument("--start-maximized")

    driver = webdriver.Edge(options=options)

    return driver


# ---------------------------------------------------------
# FIND LATEST CLOSED LOG
# ---------------------------------------------------------

def find_latest_closed_log(driver):
    """
    Open the FDA FOIA Logs page and find the newest
    FDA FOIA Closed Log link.

    The FDA page lists the newest log first.
    """

    print("Opening FDA FOIA Logs page...")

    driver.get(FDA_LOGS_PAGE)

    wait = WebDriverWait(driver, 30)

    # Wait until the page has loaded.
    wait.until(
        lambda d: d.execute_script("return document.readyState")
        == "complete"
    )

    print("FDA page loaded.")
    print("Page title:", driver.title)

    time.sleep(3)

    # Find links containing "FDA FOIA Closed Log".
    links = driver.find_elements(
        By.XPATH,
        "//a[contains("
        "translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
        "'abcdefghijklmnopqrstuvwxyz'), "
        "'fda foia closed log'"
        ")]",
    )

    if not links:
        raise RuntimeError(
            "Could not find an FDA FOIA Closed Log link on the page."
        )

    print(f"Found {len(links)} closed-log link(s).")

    # The FDA page lists the newest closed log first.
    latest_link = links[0]

    title = latest_link.text.strip()
    href = latest_link.get_attribute("href")

    print("Latest closed log found:")
    print("Title:", title)
    print("URL:", href)

    return latest_link


# ---------------------------------------------------------
# DOWNLOAD FILE
# ---------------------------------------------------------

def download_latest_log(driver):
    """
    Click the newest closed-log link and wait for
    the Excel file to finish downloading.
    """

    # Remove the previous stable output if it exists.
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()
        print("Removed previous downloaded file.")

    # Remove leftover temporary download files.
    for file in RAW_DATA_DIR.glob("*.crdownload"):
        try:
            file.unlink()
        except OSError:
            pass

    for file in RAW_DATA_DIR.glob("*.tmp"):
        try:
            file.unlink()
        except OSError:
            pass

    latest_link = find_latest_closed_log(driver)

    print()
    print("Starting download...")
    print("Clicking the latest closed log link...")

    latest_link.click()

    print("Download started.")
    print("Waiting for Excel file...")

    # Wait up to 60 seconds for the download.
    timeout = 60
    start_time = time.time()

    downloaded_file = None

    while time.time() - start_time < timeout:

        # Look for Excel files.
        excel_files = list(RAW_DATA_DIR.glob("*.xlsx"))

        # Ignore our final filename because it was deleted above.
        excel_files = [
            file
            for file in excel_files
            if file.name != OUTPUT_FILE.name
        ]

        # Check whether a download is still in progress.
        temporary_files = list(
            RAW_DATA_DIR.glob("*.crdownload")
        )

        if excel_files and not temporary_files:

            # Pick the newest Excel file.
            downloaded_file = max(
                excel_files,
                key=lambda file: file.stat().st_mtime,
            )

            break

        time.sleep(1)

    if downloaded_file is None:
        raise RuntimeError(
            "The Excel file was not downloaded within 60 seconds."
        )

    # Rename it to our predictable project filename.
    downloaded_file.rename(OUTPUT_FILE)

    print()
    print("Download completed successfully.")
    print("Saved file:")
    print(OUTPUT_FILE)

    return OUTPUT_FILE


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("FDA FOIA CLOSED LOG DOWNLOADER")
    print("=" * 60)

    driver = None

    try:
        driver = create_browser()

        download_latest_log(driver)

        print()
        print("=" * 60)
        print("SUCCESS")
        print("=" * 60)
        print()
        print("FDA FOIA Closed Log downloaded successfully.")
        print()
        print("File location:")
        print(OUTPUT_FILE)

    except Exception as error:

        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print()
        print(error)

        raise

    finally:

        if driver is not None:
            print()
            print("Closing browser...")
            driver.quit()


if __name__ == "__main__":
    main()