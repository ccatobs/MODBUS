#!/usr/bin/env python
"""
For a detailed description, see https://github.com/ccatp/MODBUS

version 0.1 - 2021/11/23

Copyright (C) 2021 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

# from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import pymodbus.exceptions
import json
import re
import sys
import logging
from timeit import default_timer as timer

"""
change history
2021/11/23 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.1
"""

__author__ = "Dr. Ralf Antonius Timmermann"
__copyright__ = "Copyright (C) Dr. Ralf Antonius Timmermann, AIfA, " \
                "University Bonn"
__credits__ = ""
__license__ = "BSD"
__version__ = "0.1"
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


class ObjectWrite(object):
    def __init__(self, init, entity):
        """
        :param init: dictionary - client parameter
            init["client"] instance- MODBUS client
            init["mapping"] mapping of all registers as from JSON
            init["endianness"] endianness's of byte and word
        :param entity: str - register prefix
        """
        self.__client = init["client"]
        self.__endianness = init["endianness"]
        self.__entity = entity
        # select mapping for each entity and sort by key
        self.__register_maps = {
            key: value for key, value in
            sorted(init["mapping"].items()) if key[0] == self.__entity
        }

    @staticmethod
    def __register_width(address):
        """
        determine the number of registers to read for a given key
        :param address: string
        :return: (int, int) - address to start from and its width
        """
        width = 0
        comp = address.split("/")
        start = int(comp[0][1:])
        if len(comp) == 1:
            width = 1
        elif len(comp) == 2:
            if comp[1] in ["1", "2"]:
                width = 1
            else:
                width = int(comp[1]) - int(comp[0]) + 1
        if width not in [1, 2, 4]:
            logging.error("Error in number of registers to read for "
                          "address: {0}".format(comp[0]))
            sys.exit(1)

        return start, width

    @staticmethod
    def trailing_byte_check(address):
        if len(address.split("/")) == 2:
            return address.split("/")[1] == "2"
        return False

    def run(self, wr):
        """

        :param wr: list of dictionaries with {parameter: value}
        :return:
        """
        builder = BinaryPayloadBuilder(
            byteorder=self.__endianness['byteorder'],
            wordorder=self.__endianness['wordorder']
        )
        print("entity: ", self.__entity)
        for parameter, value in wr.items():
            for address, attributes in self.__register_maps.items():
                if attributes['parameter'] == parameter:
                    function = attributes['function'].replace("decode_", "add_")
                    # holding register updates
                    if self.__entity == '4':
                        register, width = self.__register_width(address)
                        if "int" in function:
                            multiplier = attributes.get('multiplier', 1)
                            offset = attributes.get('offset', 0)
                            value = int((value - offset) / multiplier)
                        if "string" in function:
                            if len(value) / 2 > width:
                                logging.error(
                                    "'{0}' too long for parameter '{1}'"
                                    .format(value, parameter)
                                )
                                sys.exit(1)
                        if "bits" in function:
                            if len(value) / 16 > width:
                                logging.error(
                                    "'{0}' too long for parameter '{1}'"
                                    .format(value, parameter)
                                )
                                sys.exit(1)
                        getattr(builder, function)(value)
                        payload = builder.to_registers()
                        rq = self.__client.write_registers(
                            register,
                            payload,
                            unit=UNIT)
                        assert (not rq.isError())  # test we are not an error
                        builder.reset()  # reset builder
                        break

                    elif self.__entity == '0':
                        pass


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
    myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: " \
               "%(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
    logging.basicConfig(format=myformat,
                        level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")
    if client_config['debug']:
        logging.getLogger().setLevel(logging.DEBUG)
    with open('client_mapping.json') as json_file:
        mapping = json.load(json_file)
    # perform checks on the client mapping
    # 1) key formate: '0xxxx', '3xxxx/3xxxx', or '4xxxx/y
    # 2) parameter must not be duplicate
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
        logging.error("Wrong key in mapping: {0}.".format(key))
        sys.exit(1)
    except DuplicateParameterError:
        logging.error("Duplicate parameter: {0}.".format(parameter))
        sys.exit(1)

    try:
        client = ModbusClient(host=client_config["server"]["listenerAddress"],
                              port=client_config["server"]["listenerPort"])
        if not client.connect():
            raise pymodbus.exceptions.ConnectionException
        client.debug_enabled()
    except pymodbus.exceptions.ConnectionException:
        logging.error("Could not connect to server.")
        sys.exit(1)

    return {
        "client": client,
        "mapping": mapping,
        # if endianness not found, apply default:
        # "byteorder": Endian.Little, "wordorder": Endian.Big
        "endianness": client_config.get(
            "endianness",
            {"byteorder": "<",
             "wordorder": ">"})
    }


def writer(init, wr):
    """
    invoke for monitoring
    :param init: dictionary - client parameter
        init["client"] instance- MODBUS client
        init["mapping"] mapping of all registers as from JSON
        init["endianness"] endianness's of byte and word
    :param wr: list of dicts {parameter: value} to write to register
    :return:
    """
    register_class = ['0', '4']
    instance_list = list()

    for regs in register_class:
        instance_list.append(
            ObjectWrite(
                init=init,
                entity=regs
            )
        )
    for insts in instance_list:
        insts.run(wr)

    return 0


def close(client):
    """
    close the client
    :param client: object
    :return:
    """
    client.close()


if __name__ == '__main__':

    test = {"test 32 bit int": 720.04,
            "write int register": 10,
            "string of register/1": "YZ",
            "Write bits/1": [
                True, True, True, False, True, False, True, False,
                True, False, True, False, True, False, False, False]
            }

    initial = initialize()
    writer(init=initial, wr=test)
    close(client=initial["client"])

    exit(0)
