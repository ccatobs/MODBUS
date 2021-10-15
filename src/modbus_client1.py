from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import time
import json
import logging


HOST = '127.0.0.40'
PORT = 5020

with open('client_mapping.json') as json_file:
    mapping = json.load(json_file)

"""
mapping = {
    "30001": {
        "function": "decode_16bit_uint",
        "parameter": "Operating State",
        "map": {
            "0": "Idling ‐ ready to start",
            "2": "Starting",
            "3": "Running",
            "5": "Stopping",
            "6": "Error Lockout",
            "7": "Error",
            "8": "Helium Cool Down",
            "9": "Power related Error",
            "15": "Recovered from Error"
        }
    },
    "30002": {
        "function": "decode_16bit_uint",
        "parameter": "Compressor Running",
        "map": {
            "0": "Off",
            "1": "On"
        }
    },
    "30003/30004": {
        "function": "decode_32bit_float",
        "parameter": "Warning State",
        "map": {
            "0": "No warnings",
            "-1": "Coolant IN running High",
            "-2": "Coolant IN running Low",
            "-4": "Coolant OUT running High",
            "-8": "Coolant OUT running Low",
            "-16": "Oil running High",
            "-32": "Oil running Low",
            "-64": "Helium running High",
            "-128": "Helium running Low",
            "-256": "Low Pressure running High",
            "-512": "Low Pressure running Low",
            "-1024": "High Pressure running High",
            "-2048": "High Pressure running Low",
            "-4096": "Delta Pressure running High",
            "-8192": "Delta Pressure running Low",
            "-131072": "Static Pressure running High",
            "-262144": "Static Pressure running Low",
            "-524288": "Cold head motor Stall"
        }
    },
    "30005/30006": {
        "function": "decode_32bit_float",
        "parameter": "Alarm State",
        "map": {
            "0": "No Errors",
            "-1": "Coolant IN High",
            "-2": "Coolant IN Low",
            "-4": "Coolant OUT High",
            "-8": "Coolant OUT Low",
            "-16": "Oil High",
            "-32": "Oil Low",
            "-64": "Helium High",
            "-128": "Helium Low",
            "-256": "Low Pressure High",
            "-512": "Low Pressure Low",
            "-1024": "High Pressure High",
            "-2048": "High Pressure Low",
            "-4096": "Delta Pressure High",
            "-8192": "Delta Pressure Low",
            "-16384": "Motor Current Low",
            "-32768": "Three Phase Error",
            "-65536": "Power Supply Error",
            "-131072": "Static Pressure High",
            "-262144": "Static Pressure Low",
        }
    },
    "30007/30008": {
        "function": "decode_32bit_float",
        "parameter": "Coolant In Temp",
    },
    "30009/30010": {
        "function": "decode_32bit_float",
        "parameter": "Coolant Out Temp",
    },
    "30011":
        {
        "function": "skip_bytes",
        "parameter": 36
    },
    "30029": {
        "function": "decode_16bit_uint",
        "parameter": "Pressure",
        "map": {
            "0": "PSI",
            "1": "Bar",
            "2": "KPA"
        }
    },
    "30030": {
        "function": "decode_16bit_uint",
        "parameter": "Temperature",
        "map": {
            "0": "Fahrenheit",
            "1": "Celcius",
            "2": "Kelvin"
        }
    },
    "30031": {
        "function": "decode_16bit_uint",
        "parameter": "Panel Serial Number"
    },
    "30032/1": {
        "function": "decode_8bit_uint",
        "parameter": "Model Major Number",
        "map":
            {
                "1": "800 Series",
                "2": "900 Series",
                "3": "1000 Series",
                "4": "1100 Series",
                "5": "2800 Series"
            }
    },
    "30032/2": {
        "function": "decode_8bit_uint",
        "parameter": "Model Minor Number",
        "map":
            {
                "1": "A1",
                "2": "01",
                "3": "02",
                "4": "03",
                "5": "H3",
                "6": "I3",
                "7": "04",
                "8": "H4",
                "9": "05",
                "10": "H5",
                "11": "I6",
                "12": "06",
                "13": "07",
                "14": "H7",
                "15": "I7",
                "16": "08",
                "17": "09",
                "18": "9C",
                "19": "10",
                "20": "1I",
                "21": "11",
                "22": "12",
                "23": "13",
                "24": "14",
            }
    },
    "30033": {
        "function": "decode_16bit_uint",
        "parameter": "Software Rev"
    },
    "30034": {
        "function": "decode_bits",
        "parameter": "TEST",
        "map":
            {
                "0b00000001": "test1",
                "0b00000010": "test2",
                "0b00000100": "test3",
                "0b00001000": "test4",
                "0b00010000": "test5",
                "0b00100000": "test6",
                "0b01000000": "test7",
                "0b10000000": "test8"
            }
    }
}
"""
myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: %(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
logging.basicConfig(format=myformat,
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")
logging.getLogger().setLevel(logging.INFO)


class BinaryStringError(Exception):
    """Base class for other exceptions"""
    pass


def find_min_max(register_maps):
    els = [i for i in register_maps if i[0] == '3']
    if not els:
        return None, None
    last = els[-1]
    # length of key, e.g. '3xxxx/3xxxx'
    if len(last) != 11:
        return els[0].split("/")[0], last.split("/")[0]
    else:
        return els[0].split("/")[0], last.split("/")[1]


# def find_gaps(register_maps):
def diff(i, j):
    """gap in number of bytes"""
    high = j.split("/")[0]
    if len(i) == 11:
        low = i.split("/")[1]
    elif len(i) > 5:
        low = i.split("/")[0]
        if low == high:
            return 0
        if i.split("/")[1] == "1":
            return (int(high) - int(low) - 1) * 2 + 1
    else:
        low = i.split("/")[0]
    return (int(high) - int(low) - 1) * 2


def binary_map(binarystring):
    try:
        tmp = binarystring.split("0b")[1]
        if tmp.count('1') != 1:
            raise BinaryStringError
        return tmp[::-1].index('1')
    except IndexError:
        print("Error: no binary string in mapping")
    except BinaryStringError:
        print("Error: wrong binary string")


def formatter(decoder, decoded, register):
    function = mapping[register]['function']
    parameter = mapping[register]['parameter']
    maps = mapping[register].get('map')
    value = getattr(decoder, function)()
    if function == 'decode_bits':
        for key, desc in mapping[register]['map'].items():
            decoded.append(
                {
                    "parameter": parameter,
                    "value": value[binary_map(binarystring=key)],
                    "description": desc
                }
            )
    else:
        desc = maps.get(str(round(value))) if maps else parameter
        decoded.append(
            {
                "parameter": parameter,
                "value": value,
                "description": desc
            }
        )

    return decoded


def read_compressor_modbus_result(client):
    decoded = list()
    res = find_min_max(register_maps=mapping)

#    result = client.read_input_registers(0, 34)
    result = client.read_input_registers(0, 34)
    decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                 byteorder=Endian.Big)

    # loop till penultimate and find gaps not to be read-out
    for index, item in enumerate(list(mapping.keys())[:-1]):
        decoded = formatter(decoder, decoded, item)
        # find if there's something to skip
        skip = diff(item, list(mapping.keys())[index+1])
        decoder.skip_bytes(skip)
    # last entry in dict
    decoded = formatter(decoder, decoded, list(mapping.keys())[-1])

    print(decoded)


def main():
    client = ModbusClient(HOST, port=PORT)
    client.connect()

    while True:
        read_compressor_modbus_result(client)
        time.sleep(30)


if __name__ == '__main__':
    main()
