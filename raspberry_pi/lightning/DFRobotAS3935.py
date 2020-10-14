# -*- coding: utf-8 -*-
# Small refactoring of DFRobot DFRobot_AS3935_Lib.py library:
# https://github.com/DFRobot/DFRobot_AS3935/tree/master/RaspberryPi/Python

import time
import logging
from smbus import SMBus
from enum import Enum


class Location(Enum):
    OUTDOORS = 0
    INDOORS = 1


class Interrupt(Enum):
    ERROR = 0
    LIGHTNING = 1
    DISTURBANCE = 2
    NOISE = 3


class IrqOutputSource(Enum):
    NONE = 0
    TRCO = 1
    SRCO = 2
    LCO = 3


class DFRobotAS3935:
    def __init__(self,
                 address,
                 bus=1,
                 capacitance=12,
                 location=Location.INDOORS,
                 disturber_detection=True):
        self.address = address
        self.i2c_bus = SMBus(bus)
        self.initialize(capacitance, location, disturber_detection)

    def initialize(self, capacitance, location, disturber_detection):
        self.power_up()
        self.set_location(location)
        self.enable_disturber_detection() if disturber_detection else self.disable_disturber_detection()
        self.set_irq_output_source(IrqOutputSource.NONE)
        time.sleep(0.5)
        self.capacitance(capacitance)

    def capacitance(self, capacitance):
        if 0 <= capacitance < 16:
            self._write_register(0x08, 0x0F, capacitance * 8 >> 3)
        else:
            self._write_register(0x08, 0x0F, 0x0F)
            logging.warning(f'Capacitance {capacitance} our of rage 0-15. Setting capacitance to max value of 15.')
        register = self._read_data(0x08)
        logging.info(f'Capacitance set to {register[0] & 0x0F}.')

    def power_up(self):
        self._write_register(0x00, 0x01, 0x00)
        time.sleep(0.002)
        self._write_byte(0x3D, 0x96)
        time.sleep(0.002)
        self._write_register(0x08, 0x20, 0x20)
        time.sleep(0.002)
        self._write_register(0x08, 0x20, 0x00)

    def power_down(self):
        self._write_register(0x00, 0x01, 0x01)

    def set_location(self, location):
        if location == Location.INDOORS:
            self._write_register(0x00, 0x3E, 0x24)
            logging.info("Setting location to indoors.")
        else:
            self._write_register(0x00, 0x3E, 0x1C)
            logging.info("Setting location to outdoors.")

    def enable_disturber_detection(self):
        self._write_register(0x03, 0x20, 0x00)
        logging.info("Disturber detection enabled.")

    def disable_disturber_detection(self):
        self._write_register(0x03, 0x20, 0x20)
        logging.info("Disturber detection disabled.")

    def get_interrupt(self):
        time.sleep(0.03)
        register = self._read_data(0x03)
        interrupt_source = register[0] & 0x0F
        if interrupt_source == 0x08:
            return Interrupt.LIGHTNING
        elif interrupt_source == 0x04:
            return Interrupt.DISTURBANCE
        elif interrupt_source == 0x01:
            return Interrupt.NOISE
        else:
            logging.warning(f'Unexpected interrupt: 0x{interrupt_source:02x}')
            return Interrupt.ERROR

    def reset(self):
        success = self._write_byte(0x3C, 0x96)
        time.sleep(0.002)
        return success

    def set_irq_output_source(self, clock):
        if clock == IrqOutputSource.TRCO:
            self._write_register(0x08, 0xE0, 0x20)
        elif clock == IrqOutputSource.SRCO:
            self._write_register(0x08, 0xE0, 0x40)
        elif clock == IrqOutputSource.LCO:
            self._write_register(0x08, 0xE0, 0x80)
        else:
            self._write_register(0x08, 0xE0, 0x00)

    def get_lightning_dist(self):
        register = self._read_data(0x07)
        return register[0] & 0x3F

    def get_strike_energy(self):
        register = self._read_data(0x06)
        energy = (register[0] & 0x1F) << 8
        register = self._read_data(0x05)
        energy |= register[0]
        energy <<= 8
        register = self._read_data(0x04)
        energy |= register[0]
        return energy/16777

    def set_min_strikes(self, min_strike):
        if min_strike < 5:
            self._write_register(0x02, 0x30, 0x00)
            return 1
        elif min_strike < 9:
            self._write_register(0x02, 0x30, 0x10)
            return 5
        elif min_strike < 16:
            self._write_register(0x02, 0x30, 0x20)
            return 9
        else:
            self._write_register(0x02, 0x30, 0x30)
            return 16

    def clear_statistics(self):
        self._write_register(0x02, 0x40, 0x40)
        self._write_register(0x02, 0x40, 0x00)
        self._write_register(0x02, 0x40, 0x40)

    def get_noise_floor_lv1(self):
        register = self._read_data(0x01)
        return (register[0] & 0x70) >> 4

    def set_noise_floor_lv1(self, noise_floor):
        if noise_floor <= 7:
            self._write_register(0x01, 0x70, (noise_floor & 0x07) << 4)
        else:
            self._write_register(0x01, 0x70, 0x20)
        
    def get_watchdog_threshold(self):
        register = self._read_data(0x01)
        return register[0] & 0x0F

    def set_watchdog_threshold(self, threshold):
        self._write_register(0x01, 0x0F, threshold & 0x0F)

    def get_spike_rejection(self):
        register = self._read_data(0x02)
        return register[0] & 0x0F

    def set_spike_rejection(self, spike_rejection):
        self._write_register(0x02, 0x0F, spike_rejection & 0x0F)
        
    def print_all_registers(self):
        print(f'Register 0x00: 0x{self._read_data(0x00)[0]:02x}')
        print(f'Register 0x01: 0x{self._read_data(0x01)[0]:02x}')
        print(f'Register 0x02: 0x{self._read_data(0x02)[0]:02x}')
        print(f'Register 0x03: 0x{self._read_data(0x03)[0]:02x}')
        print(f'Register 0x04: 0x{self._read_data(0x04)[0]:02x}')
        print(f'Register 0x05: 0x{self._read_data(0x05)[0]:02x}')
        print(f'Register 0x06: 0x{self._read_data(0x06)[0]:02x}')
        print(f'Register 0x07: 0x{self._read_data(0x07)[0]:02x}')
        print(f'Register 0x08: 0x{self._read_data(0x08)[0]:02x}')

    def _read_data(self, register):
        return self.i2c_bus.read_i2c_block_data(self.address, register)

    def _write_byte(self, register, value):
        try:
            self.i2c_bus.write_byte_data(self.address, register, value)
            return True
        except IOError as e:
            logging.error('Write error', e)
            return False
        except Exception as e:
            logging.error('Unexpected write error.', e)
            return False

    def _write_register(self, address, mask, data):
        register = self._read_data(address)
        self._write_byte(address, (register[0] & ~mask) | (data & mask))
