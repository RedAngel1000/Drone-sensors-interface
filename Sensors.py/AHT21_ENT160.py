from machine import Pin, I2C
import time


# I2C SETUP

i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=100000)

print("I2C devices found:", [hex(x) for x in i2c.scan()])


# AHT21 DRIVER (Temperature + Humidity)

class AHT21:
    ADDRESS = 0x38

    def __init__(self, i2c):
        self.i2c = i2c
        time.sleep(0.04)

    def trigger_measurement(self):
        self.i2c.writeto(self.ADDRESS, b'\xAC\x33\x00')
        time.sleep(0.08)

    def read(self):
        self.trigger_measurement()
        data = self.i2c.readfrom(self.ADDRESS, 6)

        raw_humidity = ((data[1] << 12) |
                        (data[2] << 4) |
                        (data[3] >> 4))

        raw_temp = (((data[3] & 0x0F) << 16) |
                    (data[4] << 8) |
                    data[5])

        humidity = (raw_humidity / 1048576) * 100
        temperature = (raw_temp / 1048576) * 200 - 50

        return temperature, humidity


# ENS160 DRIVER (Air Quality)
class ENS160:
    ADDRESS = 0x53

    REG_OPMODE = 0x10
    REG_DATA_AQI = 0x21
    REG_DATA_TVOC = 0x22
    REG_DATA_ECO2 = 0x24

    def __init__(self, i2c):
        self.i2c = i2c
        self.set_operating_mode()
        time.sleep(0.5)

    def write_reg(self, reg, value):
        self.i2c.writeto_mem(self.ADDRESS, reg, bytes([value]))

    def read_reg(self, reg, nbytes):
        return self.i2c.readfrom_mem(self.ADDRESS, reg, nbytes)

    def set_operating_mode(self):
        # Standard operating mode
        self.write_reg(self.REG_OPMODE, 0x02)

    def read_air_quality(self):
        aqi = self.read_reg(self.REG_DATA_AQI, 1)[0]

        tvoc_bytes = self.read_reg(self.REG_DATA_TVOC, 2)
        tvoc = tvoc_bytes[0] | (tvoc_bytes[1] << 8)

        eco2_bytes = self.read_reg(self.REG_DATA_ECO2, 2)
        eco2 = eco2_bytes[0] | (eco2_bytes[1] << 8)

        return aqi, tvoc, eco2


# SENSOR INIT

aht21 = AHT21(i2c)
ens160 = ENS160(i2c)

print("Sensors initialized.\n")


def read_environment_data():
    temperature, humidity = aht21.read()
    aqi, tvoc, eco2 = ens160.read_air_quality()
    return {
        "temperature": temperature,
        "humidity": humidity,
        "aqi": aqi,
        "tvoc": tvoc,
        "eco2": eco2,
    }


if __name__ == "__main__":
    while True:
        try:
            data = read_environment_data()

            print("Temperature: {:.2f} C".format(data["temperature"]))
            print("Humidity: {:.2f} %".format(data["humidity"]))
            print("AQI:", data["aqi"])
            print("TVOC:", data["tvoc"], "ppb")
            print("eCO2:", data["eco2"], "ppm")
            print("----------------------------")

        except Exception as e:
            print("Error:", e)

        time.sleep(2)

