#!/usr/bin/env python
import os
import time
import logging
import pygame
from keypad import Keypad
import RPi.GPIO as GPIO
import asyncio
import configparser

# Load configuration
config = configparser.ConfigParser()
config.sections()
config.read('config.ini')

coinslot_gpio_pin = config['general'].getint('coinslot_gpio_pin')
cabinet_lights_colour = config['general']['cabinet_lights_colour'].split(",")

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')

# Initialize pygame mixer for MP3 playback
pygame.mixer.init()

# Path to your MP3 files (adjust this to where your MP3 files are stored)
MP3_PATH = "/home/pi/music/"

# Map keypad selection to MP3 filenames (adjust these keys and filenames as needed)
keypad_to_mp3 = {
    "A1": "song1.mp3",
    "A2": "song2.mp3",
    "A3": "song3.mp3",
    "B1": "song4.mp3",
    # Add more key mappings here
}

# Track credits locally (simple counter)
credits = 0

# Ensure GPIO mode is set only once at the start of the program
GPIO.setmode(GPIO.BCM)

def coinslot_handler(c):
    # Make sure the GPIO pin is properly set up for coin detection
    GPIO.setup(coinslot_gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Add event detection for falling edge (coin inserted)
    try:
        GPIO.add_event_detect(coinslot_gpio_pin, GPIO.FALLING, callback=coinslot_callback, bouncetime=200)
        logging.info("Edge detection set up successfully")
    except RuntimeError as e:
        logging.error(f"Failed to add edge detection: {e}")

def coinslot_callback(channel):
    global credits
    credits += 1
    logging.info(f"Coin inserted - Credits: {credits}")

async def jukebox_handler(queue, keypad):
    global credits
    while True:
        if credits >= 1:
            keypad.set_credit_light_on()

            output = await queue.get()
            queue.task_done()

            logging.info(f'Track selection detected: {output}')
            if output in keypad_to_mp3:
                mp3_file = keypad_to_mp3[output]
                mp3_path = os.path.join(MP3_PATH, mp3_file)
                
                if os.path.exists(mp3_path):
                    logging.info(f"Playing {mp3_file}")
                    play_mp3(mp3_path)
                    credits -= 1  # Decrement credits after song selection
                else:
                    logging.error(f"MP3 file {mp3_file} not found.")
            else:
                logging.error(f"Invalid selection: {output}")
        else:
            keypad.set_credit_light_off()

def play_mp3(mp3_path):
    # Stop any previously playing audio
    pygame.mixer.music.stop()
    pygame.mixer.music.load(mp3_path)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():  # Wait until the song finishes
        time.sleep(0.1)

def init_cabinet_lights(r, g, b):
    # Assuming NeoPixel is set up (leave it unchanged)
    pass

def main():
    global credits
    try:
        # Set up the cabinet lights (if needed)
        cabinet_lights = init_cabinet_lights(int(cabinet_lights_colour[0]), int(cabinet_lights_colour[1]), int(cabinet_lights_colour[2]))
        
        # Initialize the keypad queue and keypad handler
        keypad_queue = asyncio.Queue()
        keypad = Keypad(keypad_queue)

        # Initialize the coin slot handler
        coinslot_handler(credits)

        # Set up the event loop for asynchronous tasks
        loop = asyncio.get_event_loop()
        loop.create_task(keypad.get_key_combination())  # Wait for keypad input
        loop.create_task(jukebox_handler(keypad_queue, keypad))  # Handle song selection
        loop.run_forever()

    finally:
        GPIO.cleanup()  # Cleanup GPIO resources when done
        loop.close()  # Close the event loop

if __name__ == "__main__":
    main()
