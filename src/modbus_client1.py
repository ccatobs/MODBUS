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
        print("Error: wrong binary string in mapping")


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
    start, width = int(res[0][1:]) - 1, int(res[1][1:]) - int(res[0][1:]) + 1
#    result = client.read_input_registers(0, 34)
    result = client.read_input_registers(start, width)
    decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                 byteorder=Endian.Big)
    # loop incl. penultimate and find gaps not to be read-out
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
