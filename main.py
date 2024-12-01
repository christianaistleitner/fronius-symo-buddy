#!/usr/bin/env python
"""
Based on https://www.photovoltaikforum.com/thread/185108-fronius-smart-meter-tcp-protokoll
"""

import logging
import struct
import threading

from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSparseDataBlock
from pymodbus.server import StartTcpServer
from pymodbus.transaction import ModbusSocketFramer

import src.ecoflow as ecoflow

# --------------------------------------------------
# Configuration
# --------------------------------------------------

# Fronius
SMART_METER_ADDRESS = 2
CORRECTION_FACTOR = 1000

# Modbus
MODBUS_PORT = 502

# --------------------------------------------------
# Globals
# --------------------------------------------------

leistung: int | float = 0  # W
einspeisung: int | float = 0  # Wh
netzbezug: int | float = 0  # Wh
rtime = 0

ti_int1 = "0"
ti_int2 = "0"
exp_int1 = "0"
exp_int2 = "0"
ep_int1 = "0"
ep_int2 = "0"

lock = threading.Lock()

# --------------------------------------------------
# Logging
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='$asctime $levelname [$process,$threadName] [$name] [$filename:$lineno]: $message',
    style='$'
)
logging.getLogger("pymodbus").setLevel(logging.DEBUG)


# --------------------------------------------------
# Update Modbus Registers
# --------------------------------------------------
def updating_writer(slave_context: ModbusSlaveContext):
    global leistung
    global einspeisung
    global netzbezug
    #    global rtime

    global ep_int1
    global ep_int2
    global exp_int1
    global exp_int2
    global ti_int1
    global ti_int2

    global flag_connected

    lock.acquire()

    leistung = ecoflow.output_power_watts

    # Considering correction factor
    float_netzbezug = float(netzbezug)
    netzbezug_corr = float_netzbezug * CORRECTION_FACTOR

    float_einspeisung = float(einspeisung)
    einspeisung_corr = float_einspeisung * CORRECTION_FACTOR

    # Converting current power consumption out of MQTT payload to Modbus register

    electrical_power_float = 0 - float(leistung)  # extract value out of payload

    logging.info(
        'Updating values, netzbezug=%f, einspeisung=%f, leistung=%f',
        netzbezug_corr,
        einspeisung_corr,
        electrical_power_float
    )

    if electrical_power_float == 0:
        ep_int1 = 0
        ep_int2 = 0
    else:
        electrical_power_hex = hex(struct.unpack('<I', struct.pack('<f', electrical_power_float))[0])
        electrical_power_hex_part1 = str(electrical_power_hex)[2:6]  # extract first register part (hex)
        electrical_power_hex_part2 = str(electrical_power_hex)[6:10]  # extract seconds register part (hex)
        ep_int1 = int(electrical_power_hex_part1,
                      16)  # convert hex to integer because pymodbus converts back to hex itself
        ep_int2 = int(electrical_power_hex_part2,
                      16)  # convert hex to integer because pymodbus converts back to hex itself

    # Converting total import value of smart meter out of MQTT payload into Modbus register

    total_import_float = int(netzbezug_corr)
    total_import_hex = f"0x{total_import_float:08x}"
    total_import_hex_part1 = str(total_import_hex)[2:6]
    total_import_hex_part2 = str(total_import_hex)[6:10]
    ti_int1 = int(total_import_hex_part1, 16)
    ti_int2 = int(total_import_hex_part2, 16)

    # Converting total export value of smart meter out of MQTT payload into Modbus register

    total_export_float = int(einspeisung_corr)
    total_export_hex = f"0x{total_import_float:08x}"
    total_export_hex_part1 = str(total_export_hex)[2:6]
    total_export_hex_part2 = str(total_export_hex)[6:10]
    exp_int1 = int(total_export_hex_part1, 16)
    exp_int2 = int(total_export_hex_part2, 16)

    values = [
        0, 0,  # Ampere - AC Total Current Value [A]
        0, 0,  # Ampere - AC Current Value L1 [A]
        0, 0,  # Ampere - AC Current Value L2 [A]
        0, 0,  # Ampere - AC Current Value L3 [A]
        0, 0,  # Voltage - Average Phase to Neutral [V]
        0, 0,  # Voltage - Phase L1 to Neutral [V]
        0, 0,  # Voltage - Phase L2 to Neutral [V]
        0, 0,  # Voltage - Phase L3 to Neutral [V]
        0, 0,  # Voltage - Average Phase to Phase [V]
        0, 0,  # Voltage - Phase L1 to L2 [V]
        0, 0,  # Voltage - Phase L2 to L3 [V]
        0, 0,  # Voltage - Phase L1 to L3 [V]
        0, 0,  # AC Frequency [Hz]
        ep_int1, 0,  # AC Power value (Total) [W] ==> Second hex word not needed
        0, 0,  # AC Power Value L1 [W]
        0, 0,  # AC Power Value L2 [W]
        0, 0,  # AC Power Value L3 [W]
        0, 0,  # AC Apparent Power [VA]
        0, 0,  # AC Apparent Power L1 [VA]
        0, 0,  # AC Apparent Power L2 [VA]
        0, 0,  # AC Apparent Power L3 [VA]
        0, 0,  # AC Reactive Power [VAr]
        0, 0,  # AC Reactive Power L1 [VAr]
        0, 0,  # AC Reactive Power L2 [VAr]
        0, 0,  # AC Reactive Power L3 [VAr]
        0, 0,  # AC power factor total [cosphi]
        0, 0,  # AC power factor L1 [cosphi]
        0, 0,  # AC power factor L2 [cosphi]
        0, 0,  # AC power factor L3 [cosphi]
        exp_int1, exp_int2,  # Total Watt Hours Exportet [Wh]
        0, 0,  # Watt Hours Exported L1 [Wh]
        0, 0,  # Watt Hours Exported L2 [Wh]
        0, 0,  # Watt Hours Exported L3 [Wh]
        ti_int1, ti_int2,  # Total Watt Hours Imported [Wh]
        0, 0,  # Watt Hours Imported L1 [Wh]
        0, 0,  # Watt Hours Imported L2 [Wh]
        0, 0,  # Watt Hours Imported L3 [Wh]
        0, 0,  # Total VA hours Exported [VA]
        0, 0,  # VA hours Exported L1 [VA]
        0, 0,  # VA hours Exported L2 [VA]
        0, 0,  # VA hours Exported L3 [VA]
        0, 0,  # Total VAr hours imported [VAr]
        0, 0,  # VA hours imported L1 [VAr]
        0, 0,  # VA hours imported L2 [VAr]
        0, 0  # VA hours imported L3 [VAr]
    ]

    slave_context.setValues(3, 40071, values)
    lock.release()


def start_smart_meter():
    lock.acquire()

    data_block = ModbusSparseDataBlock({
        40001: [
            # Well-known value to uniquely identify this as a SunSpec Modbus Map.
            *struct.unpack('>HH', b'SunS')
        ],
        40003: [
            # Well-known value to uniquely identify this as a SunSpec Common Model block.
            1
        ],
        40004: [
            # Length of Common Model block.
            65
        ],
        40005: [
            # Manufacturer
            *struct.unpack('>HHHHHHHHHHHHHHHH', b'Fronius'.ljust(32, b'\0'))
        ],
        40021: [
            # Device model
            *struct.unpack('>HHHHHHHHHHHHHHHH', b'Smart Meter'.ljust(32, b'\0'))
        ],
        40037: [
            # Options
            *struct.unpack('>HHHHHHHH', b''.ljust(16, b'\0'))
        ],
        40045: [
            # Software Version
            *struct.unpack('>HHHHHHHH', b''.ljust(16, b'\0'))
        ],
        40053: [
            # Serial Number
            *struct.unpack('>HHHHHHHHHHHHHHHH', b'0'.ljust(32, b'\0'))
        ],
        40069: [
            # Modbus Device Address
            239 + SMART_METER_ADDRESS
        ],
        40070: [
            # SunSpec Meter Modbus Map (float): 211 = single phase, 212 = split phase, 213 = three phase
            213
        ],
        40071: [
            # Length of block
            124
        ],
        40072: [0] * 124,  # meter values block
        40196: [
            # Well-known value to uniquely identify this as the end block
            65535, 0
        ],
    })
    slave_context = ModbusSlaveContext(hr=data_block)
    server_context = ModbusServerContext(slaves=slave_context, single=True)

    lock.release()

    # --------------------------------------------------
    # Run Update Register every 5 Seconds
    # --------------------------------------------------
    time = 5  # 5 seconds delay
    # rt = RepeatedTimer(time, updating_writer, server_context)
    #updating_writer(server_context[0])
    ecoflow.on_update = lambda : updating_writer(server_context[0])

    StartTcpServer(
        context=server_context,
        address=("0.0.0.0", MODBUS_PORT),
        framer=ModbusSocketFramer
    )


if __name__ == "__main__":
    start_smart_meter()

# TODO: Exception response Exception Response(131, 3, IllegalAddress)
