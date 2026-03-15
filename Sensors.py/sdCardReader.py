from machine import SPI, Pin
import time
import os
import sdcard

# Import our sensor reading functions from the exact file names
from AHT21_ENT160 import read_environment_data
from lidar import get_lidar_data

# Hardware Constants
SPI_BUS = 0
SCK_PIN = 6
MOSI_PIN = 3
MISO_PIN = 4
CS_PIN = 5
SD_MOUNT_PATH = '/sd'
FILE_PATH = '/sd/sensor_log.csv' 

def setup_sd_card():
    """Initializes the SPI bus, mounts the SD card, and creates a file header if needed."""
    try:
        # Init SPI communication
        spi = SPI(SPI_BUS, sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
        cs = Pin(CS_PIN)
        sd = sdcard.SDCard(spi, cs)
        
        # Mount microSD card
        os.mount(sd, SD_MOUNT_PATH)
        print("MicroSD card mounted successfully at", SD_MOUNT_PATH)
        
        # Check if our log file already exists. If not, create it and write column headers.
        if 'sensor_log.csv' not in os.listdir(SD_MOUNT_PATH):
            with open(FILE_PATH, "w") as file:
                file.write("Uptime(ms),Temp(C),Humidity(%),AQI,TVOC(ppb),eCO2(ppm),Distance(cm)\n")
            print("Created new data file with headers.")
        else:
            print("Found existing data file. Appending new data...")
            
        return True
        
    except Exception as e:
        print('SD Card setup error:', e)
        return False

if __name__ == "__main__":
    print("Initializing system...")
    
    # Only start logging if the SD card mounted successfully
    if setup_sd_card():
        print("Starting data logging... Press Ctrl+C in the console to stop.")
        
        while True:
            try:
                # 1. Fetch data from sensors
                env_data = read_environment_data()
                lid_data = get_lidar_data()
                
                # 2. Get a simple timestamp (milliseconds since the Pico booted)
                timestamp = time.ticks_ms()
                
                # 3. Ensure we actually received data from both sensors before writing
                if env_data and lid_data:
                    
                    # Format the data as a comma-separated string
                    data_row = "{}, {:.2f}, {:.2f}, {}, {}, {}, {}\n".format(
                        timestamp,
                        env_data["temperature"],
                        env_data["humidity"],
                        env_data["aqi"],
                        env_data["tvoc"],
                        env_data["eco2"],
                        lid_data["distance"] 
                    )
                    
                    # 4. Open the file in Append mode ("a") and write the row
                    with open(FILE_PATH, "a") as file:
                        file.write(data_row)
                        
                    # Print to the console so you know it's working
                    print("Logged:", data_row.strip())
                    
                else:
                    print("Waiting for stable sensor data...")
                    
            except Exception as e:
                print("Logging error during main loop:", e)
                
            # Wait 5 seconds before taking the next reading
            time.sleep(5)
            
    else:
        print("Halting execution. Please check your SD card wiring and try again.")