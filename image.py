#!/usr/bin/env python3

import gpiod
import gpiodevice
import requests
import threading
import time
import logging
import os
from datetime import datetime
from gpiod.line import Bias, Direction, Edge
from PIL import Image
from io import BytesIO
from inky.auto import auto

# Configure logging
logging.basicConfig(
    filename="script.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# GPIO pins for buttons (A, B, C, D)
BUTTONS = [5, 6, 16, 24]
LABELS = ["A", "B", "C", "D"]
API_URL = "https://muses.robr.app/entry"
IMAGE_DIR = "images"

# Ensure images directory exists
os.makedirs(IMAGE_DIR, exist_ok=True)

# Configure GPIO input settings
INPUT = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP, edge_detection=Edge.FALLING)

# Find GPIO chip
chip = gpiodevice.find_chip_by_platform()
OFFSETS = [chip.line_offset_from_id(id) for id in BUTTONS]
line_config = dict.fromkeys(OFFSETS, INPUT)

# Request GPIO lines
request = chip.request_lines(consumer="inky7-buttons", config=line_config)

# Inky display instance
inky = auto(ask_user=True, verbose=True)

def fetch_image_url():
    """Fetch image URL from the API"""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        image_url = data.get("images", {}).get("small")

        if image_url:
            logging.info(f"Fetched image URL: {image_url}")
        else:
            logging.warning("No image URL found in API response.")

        return image_url

    except requests.RequestException as e:
        logging.error(f"Error fetching image URL: {e}")
        return None

def download_image(image_url):
    """Download an image and save it locally"""
    if not image_url:
        return None

    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))

        # Save image with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = os.path.join(IMAGE_DIR, f"{timestamp}.png")
        image.save(image_path)
        logging.info(f"Saved new image: {image_path}")

        return image_path

    except requests.RequestException as e:
        logging.error(f"Error downloading image: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error processing image: {e}")
        return None

def get_latest_saved_image():
    """Get the most recent image from the 'images' directory"""
    try:
        files = sorted(
            (f for f in os.listdir(IMAGE_DIR) if f.endswith(".png")),
            key=lambda x: os.path.getmtime(os.path.join(IMAGE_DIR, x)),
            reverse=True
        )
        if files:
            return os.path.join(IMAGE_DIR, files[0])
    except Exception as e:
        logging.error(f"Error retrieving saved images: {e}")
    
    return None

def update_display(image_path, saturation=0.8):
    """Display an image on the e-ink screen"""
    if not image_path:
        logging.warning("No valid image found. Skipping update.")
        return

    try:
        image = Image.open(image_path)
        resized_image = image.resize(inky.resolution)

        try:
            inky.set_image(resized_image, saturation=saturation)
            inky.set_border(inky.BLACK)
        except TypeError:
            inky.set_image(resized_image)

        inky.show()
        logging.info(f"Display updated with image from {image_path}")

    except Exception as e:
        logging.error(f"Error displaying image: {e}")

def refresh_image():
    """Fetch and update the display with a new image or fallback to a saved one"""
    logging.info("Refreshing image...")
    image_url = fetch_image_url()
    image_path = download_image(image_url) if image_url else None

    if not image_path:
        logging.warning("Falling back to last saved image.")
        image_path = get_latest_saved_image()

    update_display(image_path)

def button_listener():
    """Continuously listens for button presses"""
    logging.info("Button listener started. Waiting for button presses...")
    while True:
        for event in request.read_edge_events():
            index = OFFSETS.index(event.line_offset)
            gpio_number = BUTTONS[index]
            label = LABELS[index]
            logging.info(f"Button press detected on GPIO #{gpio_number} label: {label}")

            if label == "B":
                logging.info("Button B pressed: Fetching new image...")
                refresh_image()

def auto_refresh():
    """Automatically refresh the display on the hour"""
    while True:
        now = datetime.now()
        seconds_until_next_hour = (
            60 - now.minute
        ) * 60 - now.second # time until next top of the hour

        logging.info(f"Sleeping for {seconds_until_next_hour} seconds until the next top of the hour...")
        time.sleep(seconds_until_next_hour)

        logging.info("Top of the hour reached. Refreshing image ...")
        refresh_image()

# Start the button listener in a separate thread
button_thread = threading.Thread(target=button_listener, daemon=True)
button_thread.start()

# Start auto-refresh loop (runs in the main thread)
auto_refresh()
