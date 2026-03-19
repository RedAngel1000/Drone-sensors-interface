# okay, there may still need to be some fixes, but the input argument at least matches uart by name instead of i2c

# bno055_base.py Minimal MicroPython driver for Bosch BNO055 nine degree of
# freedom inertial measurement unit module with sensor fusion.

# The MIT License (MIT)
#
# Copyright (c) 2017 Radomir Dopieralski for Adafruit Industries.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# This is a port of the Adafruit CircuitPython driver to MicroPython, with
# modified/enhanced functionality.

# Original Author: Radomir Dopieralski
# Ported to MicroPython and extended by Peter Hinch
# This port copyright (c) Peter Hinch 2019

import utime as time
import ustruct
from micropython import const

_CHIP_ID = const(0xA0)

_CONFIG_MODE = const(0)
_NDOF_MODE = const(0x0C)

_POWER_NORMAL = const(0x00)
_POWER_LOW = const(0x01)
_POWER_SUSPEND = const(0x02)

_MODE_REGISTER = const(0x3D)
_PAGE_REGISTER = const(0x07)
_CALIBRATION_REGISTER = const(0x35)
_TRIGGER_REGISTER = const(0x3F)
_POWER_REGISTER = const(0x3E)
_ID_REGISTER = const(0x00)

ACCEL_OFFSET_X_LSB_ADDR = const(0x55)
ACCEL_OFFSET_X_MSB_ADDR = const(0x56)
ACCEL_OFFSET_Y_LSB_ADDR = const(0x57)
ACCEL_OFFSET_Y_MSB_ADDR = const(0x58)
ACCEL_OFFSET_Z_LSB_ADDR = const(0x59)
ACCEL_OFFSET_Z_MSB_ADDR = const(0x5A)

MAG_OFFSET_X_LSB_ADDR = const(0x5B)
MAG_OFFSET_X_MSB_ADDR = const(0x5C)
MAG_OFFSET_Y_LSB_ADDR = const(0x5D)
MAG_OFFSET_Y_MSB_ADDR = const(0x5E)
MAG_OFFSET_Z_LSB_ADDR = const(0x5F)
MAG_OFFSET_Z_MSB_ADDR = const(0x60)

GYRO_OFFSET_X_LSB_ADDR = const(0x61)
GYRO_OFFSET_X_MSB_ADDR = const(0x62)
GYRO_OFFSET_Y_LSB_ADDR = const(0x63)
GYRO_OFFSET_Y_MSB_ADDR = const(0x64)
GYRO_OFFSET_Z_LSB_ADDR = const(0x65)
GYRO_OFFSET_Z_MSB_ADDR = const(0x66)

ACCEL_RADIUS_LSB_ADDR = const(0x67)
ACCEL_RADIUS_MSB_ADDR = const(0x68)
MAG_RADIUS_LSB_ADDR = const(0x69)
MAG_RADIUS_MSB_ADDR = const(0x6A)


class BNO055_BASE:
    def __init__(self, uart0, crystal=True, transpose=(0, 1, 2), sign=(0, 0, 0)):
        self._uart0 = uart0
        self.crystal = crystal
        self.mag = lambda: self.scaled_tuple(0x0E, 1 / 16)  # microteslas (x, y, z)
        self.accel = lambda: self.scaled_tuple(0x08, 1 / 100)  # m.s^-2
        self.lin_acc = lambda: self.scaled_tuple(0x28, 1 / 100)  # m.s^-2
        self.gravity = lambda: self.scaled_tuple(0x2E, 1 / 100)  # m.s^-2
        self.gyro = lambda: self.scaled_tuple(0x14, 1 / 16)  # deg.s^-1
        self.euler = lambda: self.scaled_tuple(0x1A, 1 / 16)  # degrees (heading, roll, pitch)
        self.quaternion = lambda: self.scaled_tuple(
            0x20, 1 / (1 << 14), bytearray(8), "<hhhh"
        )  # (w, x, y, z)
        self._mode = _CONFIG_MODE

        # Clear any stale UART bytes
        self._flush_uart()

        try:
            chip_id = self._read(_ID_REGISTER)
        except OSError:
            raise RuntimeError("No BNO055 chip detected.")

        if chip_id != _CHIP_ID:
            raise RuntimeError("bad chip id (%x != %x)" % (chip_id, _CHIP_ID))

        self.reset()

    def _flush_uart(self):
        while self._uart0.any():
            self._uart0.read()

    def reset(self):
        self.mode(_CONFIG_MODE)
        try:
            self._write(_TRIGGER_REGISTER, 0x20)
        except OSError:
            # Expected during reset
            pass

        # Wait for the chip to reset (650 ms typ.)
        time.sleep_ms(700)
        self._flush_uart()

        self._write(_POWER_REGISTER, _POWER_NORMAL)
        self._write(_PAGE_REGISTER, 0x00)
        self._write(_TRIGGER_REGISTER, 0x80 if self.crystal else 0)
        time.sleep_ms(500 if self.crystal else 10)

        if hasattr(self, "orient"):
            self.orient()

        self.mode(_NDOF_MODE)

    def scaled_tuple(self, addr, scale, buf=bytearray(6), fmt="<hhh"):
        return tuple(b * scale for b in ustruct.unpack(fmt, self._readn(buf, addr)))

    def temperature(self):
        t = self._read(0x34)
        return t if t < 128 else t - 256

    # Return bytearray [sys, gyro, accel, mag] calibration data.
    def cal_status(self, s=bytearray(4)):
        cdata = self._read(_CALIBRATION_REGISTER)
        s[0] = (cdata >> 6) & 0x03
        s[1] = (cdata >> 4) & 0x03
        s[2] = (cdata >> 2) & 0x03
        s[3] = cdata & 0x03
        return s

    def calibrated(self):
        s = self.cal_status()
        return min(s[1:]) == 3 and s[0] > 0

    def sensor_offsets(self):
        last_mode = self._mode
        self.mode(_CONFIG_MODE)
        offsets = self._readn(bytearray(22), ACCEL_OFFSET_X_LSB_ADDR)
        self.mode(last_mode)
        return offsets

    def set_offsets(self, buf):
        last_mode = self._mode
        self.mode(_CONFIG_MODE)
        time.sleep_ms(25)

        self._write(ACCEL_OFFSET_X_LSB_ADDR, buf[0])
        self._write(ACCEL_OFFSET_X_MSB_ADDR, buf[1])
        self._write(ACCEL_OFFSET_Y_LSB_ADDR, buf[2])
        self._write(ACCEL_OFFSET_Y_MSB_ADDR, buf[3])
        self._write(ACCEL_OFFSET_Z_LSB_ADDR, buf[4])
        self._write(ACCEL_OFFSET_Z_MSB_ADDR, buf[5])

        self._write(MAG_OFFSET_X_LSB_ADDR, buf[6])
        self._write(MAG_OFFSET_X_MSB_ADDR, buf[7])
        self._write(MAG_OFFSET_Y_LSB_ADDR, buf[8])
        self._write(MAG_OFFSET_Y_MSB_ADDR, buf[9])
        self._write(MAG_OFFSET_Z_LSB_ADDR, buf[10])
        self._write(MAG_OFFSET_Z_MSB_ADDR, buf[11])

        self._write(GYRO_OFFSET_X_LSB_ADDR, buf[12])
        self._write(GYRO_OFFSET_X_MSB_ADDR, buf[13])
        self._write(GYRO_OFFSET_Y_LSB_ADDR, buf[14])
        self._write(GYRO_OFFSET_Y_MSB_ADDR, buf[15])
        self._write(GYRO_OFFSET_Z_LSB_ADDR, buf[16])
        self._write(GYRO_OFFSET_Z_MSB_ADDR, buf[17])

        self._write(ACCEL_RADIUS_LSB_ADDR, buf[18])
        self._write(ACCEL_RADIUS_MSB_ADDR, buf[19])

        self._write(MAG_RADIUS_LSB_ADDR, buf[20])
        self._write(MAG_RADIUS_MSB_ADDR, buf[21])

        self.mode(last_mode)

    def _read(self, memaddr, buf=bytearray(1)):
        self._flush_uart()
        packet = bytes([0xAA, 0x01, memaddr, 0x01])
        self._uart0.write(packet)
        time.sleep_ms(20)
        resp = self._uart0.read(3)
        if resp is None or len(resp) < 3 or resp[0] != 0xBB or resp[1] != 0x01:
            raise OSError("UART read failed at register 0x{:02X}".format(memaddr))
        return resp[2]

    def _write(self, memaddr, data, buf=bytearray(1)):
        self._flush_uart()
        packet = bytes([0xAA, 0x00, memaddr, 0x01, data])
        self._uart0.write(packet)
        time.sleep_ms(20)
        resp = self._uart0.read(2)
        if resp is None or len(resp) < 2:
            raise OSError("UART write failed at register 0x{:02X}".format(memaddr))
        if resp[0] != 0xEE or resp[1] != 0x01:
            raise OSError("UART write failed at register 0x{:02X}".format(memaddr))

    def _readn(self, buf, memaddr):
        n = len(buf)
        self._flush_uart()
        packet = bytes([0xAA, 0x01, memaddr, n])
        self._uart0.write(packet)
        time.sleep_ms(20)
        resp = self._uart0.read(n + 2)
        if resp is None or len(resp) < (n + 2) or resp[0] != 0xBB or resp[1] != n:
            raise OSError("UART readn failed at register 0x{:02X}".format(memaddr))
        buf[:] = resp[2:2 + n]
        return buf

    def mode(self, new_mode=None):
        old_mode = self._read(_MODE_REGISTER)
        if new_mode is not None:
            self._write(_MODE_REGISTER, _CONFIG_MODE)
            time.sleep_ms(20)
            if new_mode != _CONFIG_MODE:
                self._write(_MODE_REGISTER, new_mode)
                time.sleep_ms(10)

        self._mode = old_mode if new_mode is None else new_mode
        return old_mode

    def external_crystal(self):
        return bool(self._read(_TRIGGER_REGISTER) & 0x80)
