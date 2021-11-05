#!/usr/bin/env python
"""
For a detailed description, see https://github.com/ccatp/MODBUS

version 0.4 - 2021/11/01

Copyright (C) 2021 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import pymodbus.exceptions
import json
import re
import sys
import logging

"""
change history
2021/10/20 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.1
2021/10/24 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.2
    * for additional key/value pairs in client mapping parse'em through.
2021/10/27 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.3
    * adapted for hk
    * also function parsed through as indicator for data type     
2021/11/01 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.4
    * skip first byte of register if starts with 'xxxxx/2'
"""

__author__ = "Dr. Ralf Antonius Timmermann"
__copyright__ = "Copyright (C) Dr. Ralf Antonius Timmermann, AIfA, " \
                "University Bonn"
__credits__ = ""
__license__ = "GPLv3"
__version__ = "0.4.0"
__maintainer__ = "Dr. Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "Dev"

print(__doc__)

UNIT = 0x1


class BinaryStringError(Exception):
    """Base class for other exceptions"""
    pass


class MappingKeyError(Exception):
    """Base class for other exceptions"""
    pass


class DuplicateParameterError(Exception):
    """Base class for other exceptions"""
    pass


class ObjectType(object):
    def __init__(self, client, mapping, entity):
        """
        :param client: instance- MODBUS client
        :param mapping: dictionary - mapping of all registers as from JSON
        :param entity: str - register prefix
        """
        self.client = client
        self.entity = entity
        # select mapping for each entity and sort by key
        self.register_maps = {
            key: value for key, value in
            sorted(mapping.items()) if key[0] == self.entity
        }
        els = [i for i in self.register_maps]

        if not els:
            self.boundaries = {}
        else:
            mini = els[0].split("/")[0]
            maxi = els[-1].split("/")[0]
            if len(els[-1].split("/")) == 2:
                if els[-1].split("/")[1] not in ['1', '2']:
                    maxi = els[-1].split("/")[1]
            self.boundaries = {
                "min": mini,
                "max": maxi,
                "start": int(mini[1:]),
                "width": int(maxi[1:]) - int(mini[1:]) + 1
            }
            if self.entity in ['0', '1']:
                if self.boundaries['start'] + self.boundaries['width'] >= 2000:
                    logging.error("Error: number of registers superseed "
                                  "limit of 2000. Consider a redesign!")
                    sys.exit(1)

    @staticmethod
    def gap(low, high):
        """
        :param low: str - low register number
        :param high: str - high register number
        :return: int - gap between high and low registers in number of bytes
        """
        byt = 0
        lb = low.split("/")
        hb = high.split("/")
        if len(hb) == 2:
            if hb[1] == "2":
                byt += 1
        if len(lb) == 2:
            if lb[1] == "1":
                return (int(hb[0]) - int(lb[0]) - 1) * 2 + 1 + byt
            elif lb[1] == "2":
                return (int(hb[0]) - int(lb[0]) - 1) * 2 + byt
            else:
                return (int(hb[0]) - int(lb[1]) - 1) * 2 + byt
        else:
            return (int(hb[0]) - int(lb[0]) - 1) * 2 + byt

    @staticmethod
    def binary_map(binarystring):
        """
        position of True in binary string. Report if malformated in mapping.
        :param binarystring: str
        :return: integer
        """
        try:
            tmp = binarystring.split("0b")[1]
            if tmp.count('1') != 1:
                raise BinaryStringError
            return tmp[::-1].index('1')
        except IndexError:
            logging.error("Error: no binary string in mapping")
            sys.exit(1)
        except BinaryStringError:
            logging.error("Error: wrong binary string in mapping")
            sys.exit(1)

    def formatter(self, decoder, register):
        """
        format the output dictionary and append by scanning through the mapping
        of the registers. If gaps in the mappings are detected they are skipped
        by the number of bytes.
        :param decoder: A deferred response handle from the register readings
        :param register: dictionary
        :return: list with dictionary
        """
        function = self.register_maps[register]['function']
        value = getattr(decoder, function)()
        if function == 'decode_bits':
            # if only one entry in map found, add optional parameters
            if len(self.register_maps[register]['map']) == 1:
                optional = {
                    key: self.register_maps[register][key]
                    for key in self.register_maps[register]
                    if key not in {'map',
                                   'description',
                                   'value',
                                   'function',
                                   'parameter',
                                   'multiplier'}
                }
            else:
                optional = dict()
            decoded = list()
            for key, name in self.register_maps[register]['map'].items():
                decoded.append(dict(
                    {
                        "parameter": self.register_maps[register]['parameter'],
                        "value": value[self.binary_map(binarystring=key)],
                        "description": name,
                        "function": function
                    },
                    **optional)
                )
        else:
            maps = self.register_maps[register].get('map')
            desc = self.register_maps[register].get('description')
            optional = {
                key: self.register_maps[register][key]
                for key in self.register_maps[register]
                if key not in {'map',
                               'description'}
            }
            di = {"value": value}
            if maps:
                desc = maps.get(str(round(value)))
            if desc:
                di["description"] = desc
            decoded = [
                dict(**optional,
                     **di)
            ]

        return decoded

    def formatter_bit(self, decoder, register):
        """
        indexes the result array of bits by the keys found in the mapping
        :param decoder: A deferred response handle from the register readings
        :param register: dictionary
        :return: list with dictionary
        """
        return [
            dict(
                **self.register_maps[register],
                **{"function": "decode_bits",
                   "value": decoder[int(register[1:])]}
            )
        ]

    def run(self):
        """
        instantiates the classes for the 4 register object types and invokes
        the run methods within an interval.
        These two methods are not yet implemented !!!
            decoder.decode_string(size=1) - Decodes a string from the buffer
            decoder.bit_chunks() - classmethod
        :return: dictionary
        """
        if not self.boundaries:
            return []
        result = None
        decoded = list()

        if self.entity == '0':
            # ToDo: for simplicity we read first 2000 bits
            result = self.client.read_coils(
                address=0,
                count=2000,
                unit=UNIT
            )
        elif self.entity == '1':
            # ToDo: for simplicity we read first 2000 bits
            result = self.client.read_discrete_inputs(
                address=0,
                count=2000,
                unit=UNIT
            )
        elif self.entity == '3':
            result = self.client.read_input_registers(
                address=self.boundaries['start'],
                count=self.boundaries['width'],
                unit=UNIT
            )
        elif self.entity == '4':
            result = self.client.read_holding_registers(
                address=self.boundaries['start'],
                count=self.boundaries['width'],
                unit=UNIT
            )
        assert (not result.isError())

        if self.entity in ['0', '1']:
            decoder = result.bits
            for register in self.register_maps.keys():
                decoded = decoded + self.formatter_bit(
                    decoder=decoder,
                    register=register
                )
        elif self.entity in ['3', '4']:
            decoder = BinaryPayloadDecoder.fromRegisters(
                registers=result.registers,
                byteorder=Endian.Big
            )
            # skip leading byte for very first register to start with
            # trailing byte if key='xxxxx/2'
            first_key = list(self.register_maps.keys())[0].split("/")
            if len(first_key) == 2:
                if first_key[1] == '2':
                    decoder.skip_bytes(nbytes=1)
            # loop incl. penultimate and find gaps to be skipped
            for index, register in enumerate(
                    list(self.register_maps.keys())[:-1]):
                decoded = decoded + self.formatter(
                    decoder=decoder,
                    register=register
                )
                skip = self.gap(
                    low=register,
                    high=list(self.register_maps.keys())[index+1]
                )
                decoder.skip_bytes(nbytes=skip)
            # last entry in dictionary
            decoded = decoded + self.formatter(
                decoder=decoder,
                register=list(self.register_maps.keys())[-1])

        return decoded


def initialize():
    """
    initializing the modbus client and perform checks on client_mapping.json:
    1) format of register key
    2) existance and uniqueness of "parameter"
    3) connection to modbus server via synchronous TCP
    :return:
    object - modbus client
    dictionary - mapping
    """
    rev_dict = dict()
    key = None
    parameter = None

    with open('client_config.json') as config_file:
        client_config = json.load(config_file)

    myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: %(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
    logging.basicConfig(format=myformat,
                        level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")
    if client_config['debug']:
        logging.getLogger().setLevel(logging.DEBUG)

    with open('client_mapping.json') as json_file:
        mapping = json.load(json_file)
    # perform checks on the client mapping
    # 1) keys are of following formate: '3xxxx/3xxxx', '3xxxx/2 or '3xxxx'
    # 2) test on duplicate parameter
    try:
        for key, value in mapping.items():
            if not re.match(
                    r"^[0134][0-9]{4}(/([12]|[0134][0-9]{4}))?$",
                    key):
                raise MappingKeyError
            rev_dict.setdefault(value["parameter"], set()).add(key)
        parameter = [key for key, values in rev_dict.items()
                     if len(values) > 1]
        if parameter:
            raise DuplicateParameterError
    except MappingKeyError:
        logging.error("Error: wrong key in mapping: {0}".format(key))
        sys.exit(1)
    except DuplicateParameterError:
        logging.error("Error: duplicate parameters: {0}".format(parameter))
        sys.exit(1)

    try:
        client = ModbusClient(host=client_config["server"]["listenerAddress"],
                              port=client_config["server"]["listenerPort"])
        client.debug_enabled()
        client.connect()
    except pymodbus.exceptions.ConnectionException:
        logging.error("Error: could not connect to server.")
        sys.exit(1)

    return client, mapping


def retrieve(client, mapping):
    """
    invoke for monitoring
    :param client: object
    :param mapping: dictionary
    :return:
    """
    register_class = ['0', '1', '3', '4']
    instance_list = list()

    for regs in register_class:
        instance_list.append(
            ObjectType(client=client,
                       mapping=mapping,
                       entity=regs
                       )
        )

    decoded = list()
    for insts in instance_list:
        # append result from all register classes
        decoded = decoded + insts.run()

    return decoded


def close(client):
    """
    close the client
    :param client: object
    :return:
    """
    client.close()


if __name__ == '__main__':

    client, mapping = initialize()
    to_hk = retrieve(client=client,
                     mapping=mapping)
    close(client=client)

    # if JSON needs to be sorted by keys
    print(json.dumps([dict(sorted(i.items())) for i in to_hk], indent=4))
    # otherwise, this will suffice
    # print(json.dumps(to_hk, indent=4))

    exit(0)
