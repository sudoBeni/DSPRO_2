import json
import logging
import random
import time
from datetime import date
from pathlib import Path

import click
import requests
from dedpup_scraped_listings import dedup_raw_listings
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Logger set up
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


RAW_LISTINGS = Path("data/raw/apartements.jsonl")
IMAGE_FOLDER = Path("data/raw/images")


def safe_text(driver: webdriver, xpath: By.XPATH) -> str:
    try:
        return driver.find_element(By.XPATH, xpath).text.strip().replace("\n", " ")
    except NoSuchElementException:
        return None


def navigate_to_listing_overview(driver, actions) -> None:
    time.sleep(random.uniform(2.5, 7.5))
    # Catch popup if visible
    try:
        popup = driver.find_element(
            By.XPATH, "//button[normalize-space()='Akzeptieren']"
        )
        actions.move_to_element(popup).click().perform()
    except NoSuchElementException:
        log.info("Popup wasn't visible")

    time.sleep(random.uniform(2.5, 7.5))

    try:
        popup2 = driver.find_element(By.XPATH, "//button[contains(@class, 'close')]")
        popup2.click()
    except NoSuchElementException:
        log.info("Popup2 wasn't visible")

    time.sleep(random.uniform(2.5, 7.5))

    # Fake exploring
    dienstleistungen = driver.find_element(
        By.XPATH, "//h2[normalize-space()='Dienstleistungen von ImmoScout24']"
    )
    actions.move_to_element_with_offset(dienstleistungen, 5, 2).perform()
    time.sleep(random.uniform(2.5, 7.5))

    button = driver.find_element(By.XPATH, "//div[@class='filterButton']")
    actions.move_to_element_with_offset(button, 1, 4).perform()
    time.sleep(random.uniform(2.5, 7.5))

    wohnung_mieten_btn = driver.find_element(
        By.XPATH, "//a[normalize-space()='Wohnung zum Mieten']"
    )
    actions.move_to_element(wohnung_mieten_btn).perform()
    time.sleep(random.uniform(2.5, 7.5))
    wohnung_mieten_btn.click()
    time.sleep(random.uniform(2.5, 7.5))

    # Location Selection Page
    soli = driver.find_element(By.XPATH, "//h3[normalize-space()='Solothurn']")
    actions.move_to_element_with_offset(soli, 6, 0).perform()
    time.sleep(random.uniform(2.5, 7.5))

    actions.scroll_by_amount(0, 200).perform()
    time.sleep(random.uniform(2.5, 7.5))

    schweiz_btn = driver.find_element(By.XPATH, "//span[text()='Schweiz']")
    actions.move_to_element_with_offset(schweiz_btn, 2, 0).click().perform()
    time.sleep(random.uniform(2.5, 7.5))


def extract_listings(driver: webdriver, n_pages: int) -> None:

    for _ in range(n_pages):
        time.sleep(2)

        # Now we're on the listings Page
        listings = driver.find_elements(By.XPATH, "//div[@role='listitem']")
        # sizeoflistings = len(listings) DEBUG

        for i in range(len(listings)):
            for k in range(2):  # RETRY BLOCK FOR CLICKING LISTING
                try:
                    listings = driver.find_elements(By.XPATH, "//div[@role='listitem']")

                    # Click through listings
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", listings[i]
                    )
                    time.sleep(1)

                    unabletoextractflag = False
                    try:
                        line2 = listings[i].text.splitlines()
                        if line2[0] == "Neubau" or line2[0] == "Neu":
                            num_rooms = line2[2].split(",")[0].strip()
                            living_area_m2 = line2[2].split(",")[1].strip()
                            rent = line2[2].split(",")[2].strip()
                        else:
                            num_rooms = line2[1].split(",")[0].strip()
                            living_area_m2 = line2[1].split(",")[1].strip()
                            rent = line2[1].split(",")[2].strip()
                    except IndexError:
                        log.warning(
                            f"tried to extract line: {listings[i].text.splitlines()} but failed!"
                        )
                        time.sleep(1)
                        unabletoextractflag = True

                    ActionChains(driver).move_to_element_with_offset(
                        listings[i], xoffset=-1, yoffset=4
                    ).click().perform()
                    break

                except StaleElementReferenceException:
                    log.info(f"Listing {i} stale on attempt {k + 1}, retrying...")
                    time.sleep(1)

            # Detailview of listing
            # Extracting the hard facts of an apartement
            time.sleep(2)
            if unabletoextractflag:
                num_rooms = safe_text(
                    driver, "//div[normalize-space()='Zimmer']/following-sibling::div"
                )
                living_area_m2 = safe_text(
                    driver,
                    "//div[normalize-space()='Wohnfläche']/following-sibling::div",
                )
                rent = safe_text(
                    driver, "//div[normalize-space()='Miete']/following-sibling::div"
                )

            apartment_title = safe_text(
                driver, "//h1[contains(@class, 'ListingTitle_spotlightTitle')]"
            )
            apartment_description = safe_text(
                driver, "//div[contains(@class,'Description_descriptionBody')]"
            )
            renovation_year = safe_text(
                driver,
                "//dt[normalize-space()='Letztes Renovationsjahr:']/following-sibling::dd[1]",
            )
            year_of_construction = safe_text(
                driver, "//dt[normalize-space()='Baujahr:']/following-sibling::dd[1]"
            )

            try:
                address_text = driver.find_element(
                    By.XPATH, "//address[contains(@class, 'AddressDetails_address')]"
                ).text.strip()
                street = address_text.split(",")[0].strip().replace("\n", " ")

                try:
                    postal_code = address_text.split(",")[1].strip().replace("\n", " ")
                except IndexError:
                    postal_code = None

            except NoSuchElementException:
                street = None
                postal_code = None

            try:
                apartment_id = (
                    driver.find_element(
                        By.XPATH,
                        "//dl[contains(@class, 'ListingTechReferences_techReferencesList')]//dd[1]",
                    )
                    .text.strip()
                    .replace("\n", " ")
                )
            except NoSuchElementException:
                apartment_id = random.randint(123456000, 123456999)

            current_url = driver.current_url
            scrape_timestamp = str(date.today())

            apartment_listing = {
                "n_rooms": num_rooms,
                "living_area_m2": living_area_m2,
                "rent_chf": rent,
                "short_description": apartment_title,
                "street": street,
                "postal_code": postal_code,
                "last_renovation_year": renovation_year,
                "year_of_construction": year_of_construction,
                "description": apartment_description,
                "object_id": apartment_id,
                "source_url": current_url,
                "scraped_at": scrape_timestamp,
            }

            # Saving the dict
            with open(RAW_LISTINGS, "a", encoding="utf-8") as f:
                f.write(json.dumps(apartment_listing, ensure_ascii=False) + "\n")

            # Extract images
            images = driver.find_elements(
                By.XPATH, "//div[contains(@class,'ImageGallery_galleryWrapper')]//img"
            )

            count = 0
            for j, img in enumerate(images):
                if count == 20:
                    break

                url = img.get_attribute("src")

                if not url:
                    continue

                try:
                    response = requests.get(url, timeout=10)
                except requests.RequestException as e:
                    log.warning(f"Image download failed for {url}: {e}")
                    continue

                with open(
                    IMAGE_FOLDER / f"apartment_{apartment_id}_{j}.jpg", "wb"
                ) as f:
                    f.write(response.content)
                count += 1

            driver.back()
            time.sleep(2)

        next_page = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[@aria-label='Zur nächsten Seite']")
            )
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", next_page
        )
        next_page.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[@role='listitem']"))
        )


def start_on_page(driver: webdriver, page_number: int) -> None:
    for _ in range(page_number):
        next_page = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[@aria-label='Zur nächsten Seite']")
            )
        )
        next_page.click()


@click.command()
@click.option(
    "--num-start-page",
    default=0,
    show_default=True,
    type=int,
    help="Pagenumber of where the scraper starts to extract listings from",
)
@click.option(
    "--num-pages-to-scrape",
    default=100,
    show_default=True,
    type=int,
    help="Number of Pages the Scraper will extract data from",
)
def main(num_start_page: int, num_pages_to_scrape: int) -> None:
    RAW_LISTINGS.parent.mkdir(parents=True, exist_ok=True)
    IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)

    driver = webdriver.Chrome()
    actions = ActionChains(driver)
    driver.get("https://www.immoscout24.ch/de")

    navigate_to_listing_overview(driver=driver, actions=actions)

    start_on_page(driver=driver, page_number=num_start_page)
    extract_listings(driver=driver, n_pages=num_pages_to_scrape)

    driver.close()

    dedup_raw_listings()


if __name__ == "__main__":
    main()
