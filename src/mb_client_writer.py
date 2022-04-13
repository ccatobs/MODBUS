#!/usr/bin/env python
"""
MODBUS WRITER
version 1.1 - 2021/12/18

For a detailed description, see https://github.com/ccatp/MODBUS

run, e.g.:
python3 mb_client_writer.py --device <device extention> (default: default)
--payload \'{\"test 32 bit int\": 720.04}\'

Copyright (C) 2021 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import pymodbus.exceptions
import json
import re
import sys
import logging
from timeit import default_timer as timer
from os import path
import argparse

"""
change history
2021/11/23 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.1
2021/12/01 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.0
    * adapted for modbus REST API
2021/12/18 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.1
    * strings modified
"""

__author__ = "Dr. Ralf Antonius Timmermann"
__copyright__ = "Copyright (C) Dr. Ralf Antonius Timmermann, AIfA, " \
                "University Bonn"
__credits__ = ""
__license__ = "BSD"
__version__ = "1.1"
__maintainer__ = "Dr. Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "Dev"

print(__doc__)

UNIT = 0x1


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
        :return: (int, int, int) - address to start from, its register
        and byte widths
        """
        width, no_bytes, pos_byte = 1, 2, 1

        comp = address.split("/")
        start = int(comp[0][1:])
        if len(comp) == 2:
            if comp[1] in ["1", "2"]:
                no_bytes = 1
                pos_byte = int(comp[1])
            else:
                width = int(comp[1]) - int(comp[0]) + 1
                no_bytes = width * 2

        return {
            "start": start,
            "width": width,
            "no_bytes": no_bytes,
            "pos_byte": pos_byte
        }

    def __holding(self, wr):
        """
        dictionary with "parameter: value" pairs to be changed in coil and
        holding registers
        :param wr: dictionary with {parameter: value} pairs
        :return:
        """
        builder = BinaryPayloadBuilder(
            byteorder=self.__endianness['byteorder'],
            wordorder=self.__endianness['wordorder']
        )

        for parameter, value in wr.items():
            for address, attributes in self.__register_maps.items():
                if attributes['parameter'] == parameter:
                    # holding register updates
                    function = attributes['function'].replace("decode_", "add_")
                    reg_info = self.__register_width(address)
                    if "int" in function:
                        multiplier = attributes.get('multiplier', 1)
                        offset = attributes.get('offset', 0)
                        value = int((value - offset) / multiplier)
                    if "string" in function:
                        if len(value) > reg_info['no_bytes']:
                            logging.error(
                                "'{0}' too long for parameter '{1}'"
                                .format(value, parameter)
                            )
                            sys.exit(500)
                        # fill entire string with spaces
                        s = list(" " * (2*reg_info['width']))
                        s[reg_info['pos_byte'] - 1] = value
                        value = "".join(s)
                    if "bits" in function:
                        if len(value) / 16 > reg_info['width']:
                            logging.error(
                                "'{0}' too long for parameter '{1}'"
                                .format(value, parameter)
                            )
                            sys.exit(500)
                    getattr(builder, function)(value)
                    payload = builder.to_registers()
                    rq = self.__client.write_registers(
                        address=reg_info['start'],
                        values=payload,
                        unit=UNIT)
                    assert (not rq.isError())  # test we are not an error
                    builder.reset()  # reset builder
                    break  # if parameter matched

        return 0

    def run(self, wr):
        """
        call coil or holding register writes
        :param wr: dictionary with {parameter: value} pairs
        :return:
        """
        if self.__entity == '4':
            self.__holding(wr=wr)

        elif self.__entity == '0':
            for parameter, value in wr.items():
                for address, attributes in self.__register_maps.items():
                    if attributes['parameter'] == parameter:
                        # coil register updates one-by-one
                        rq = self.__client.write_coil(
                            address=int(address),
                            value=value,
                            unit=UNIT)
                        assert (not rq.isError())  # test we are not an error
                        break

        return 0


def initialize(name: str = "default"):
    """
    initializing the modbus client and perform checks on
    mb_client_mapping_<name>.json:
    1) format of register key
    2) existance and uniqueness of "parameter"
    3) connection to modbus server via synchronous TCP
    :return:
    object - modbus client
    dictionary - mapping
    """

    def address_integrity(address):
        if not re.match(r"^[0134][0-9]{4}(/([12]|[0134][0-9]{4}))?$", address):
            return False
        comp = address.split("/")
        if len(comp) == 2:
            if comp[1] not in ["1", "2"] and \
                    (comp[0][0] != comp[1][0] or
                     int(comp[1]) - int(comp[0]) < 1):
                return False
        return True

    rev_dict = dict()
    key = None
    parameter = None
    file_config = "mb_client_config_{0}.json".format(name)
    file_mapping = "mb_client_mapping_{0}.json".format(name)
    # verify existance of both files
    if not path.isfile(file_config):
        logging.error("Client config file {0} not found".format(
            file_config))
        sys.exit(404)
    if not path.isfile(file_mapping):
        logging.error("Client config file {0} not found".format(
            file_mapping))
        sys.exit(404)
    with open(file_config) as config_file:
        client_config = json.load(config_file)
    with open(file_mapping) as json_file:
        mapping = json.load(json_file)
    if client_config['debug']:
        logging.getLogger().setLevel(logging.DEBUG)

    # perform checks on the client mapping
    # 1) key formate: '0xxxx', '3xxxx/3xxxx', or '4xxxx/y
    # 2) parameter must not be duplicate
    try:
        for key, value in mapping.items():
            if not address_integrity(key):
                raise MappingKeyError
            rev_dict.setdefault(value["parameter"], set()).add(key)
        parameter = [key for key, values in rev_dict.items()
                     if len(values) > 1]
        if parameter:
            raise DuplicateParameterError
    except MappingKeyError:
        logging.error("Wrong key in mapping: {0}.".format(key))
        sys.exit(500)
    except DuplicateParameterError:
        logging.error("Duplicate parameter: {0}.".format(parameter))
        sys.exit(500)

    try:
        client = ModbusClient(host=client_config["server"]["listenerAddress"],
                              port=client_config["server"]["listenerPort"])
        if not client.connect():
            raise pymodbus.exceptions.ConnectionException
        client.debug_enabled()
    except pymodbus.exceptions.ConnectionException:
        logging.error("Could not connect to server.")
        sys.exit(503)

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

    argparser = argparse.ArgumentParser(
        description="Universal MODBUS Writer")
    argparser.add_argument('--device',
                           required=False,
                           help='Device extention (default: "default")',
                           default='default'
                           )
    argparser.add_argument('--payload',
                           required=True,
                           help="Payload ('{parameter: value}')"
                           )
    myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: " \
               "%(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
    logging.basicConfig(format=myformat,
                        level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")
    """
    test = {"test 32 bit int": 720.04,
            "write int register": 10,
            "string of register/1": "YZ",
            "Write bits/1": [
                True, True, True, False, True, False, True, False,
                True, False, True, False, True, False, False, False
            ],
            "Coil 0": True,
            "Coil 1": True,
            "Coil 10": True
            }
    """
    _start_time = timer()

    print("Device extention: {0}".format(argparser.parse_args().device))
    print(argparser.parse_args().payload)
    try:
        initial = initialize(argparser.parse_args().device)
        writer(init=initial,
               wr=json.loads(argparser.parse_args().payload))
        close(client=initial["client"])
    except SystemExit as e:
        exit("Error code {0}".format(e))
    print("Time consumed to process modbus writer: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    exit(0)
