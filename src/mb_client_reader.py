#!/usr/bin/env python
"""
MODBUS READER
version 1.0 - 2021/12/02

For a detailed description, see https://github.com/ccatp/MODBUS

run: python3 mb_client_reader.py --device <device extention> (default: default)

Copyright (C) 2021 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

from pymodbus.payload import BinaryPayloadDecoder
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
2021/10/20 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.1
2021/10/24 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.2
    * for additional key/value pairs in client mapping pass them through.
2021/10/27 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.3
    * adapted for hk
    * also function passed-through as indicator for data type     
2021/11/01 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.4
    * skip first byte of register if starts with 'xxxxx/2'
2021/11/08 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.5
    * introduce datatype for avro, disregard function for output dictionary
2021/11/11 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.6
    * complete redesign: registers are read consecutively, one-by-one.
    * multiplier & offset are processed for output to hk
2021/11/22 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.7
    * introduce endiannesses of byte- and wordorder
2021/11/24 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.8
    * strings of variable length to be decoded as well
2021/11/30
- version 1.0
    * variable filenames
"""

__author__ = "Dr. Ralf Antonius Timmermann"
__copyright__ = "Copyright (C) Dr. Ralf Antonius Timmermann, AIfA, " \
                "University Bonn"
__credits__ = ""
__license__ = "BSD"
__version__ = "1.0"
__maintainer__ = "Dr. Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "Dev"

print(__doc__)

UNIT = 0x1
function2avro = {
    "decode_bits": "boolean",
    "decode_8bit_int": "int",
    "decode_8bit_uint": "int",
    "decode_16bit_int": "int",
    "decode_16bit_uint": "int",
    "decode_16bit_float": "float",
    "decode_32bit_int": "int",
    "decode_32bit_uint": "int",
    "decode_32bit_float": "float",
    "decode_64bit_int": "long",
    "decode_64bit_uint": "long",
    "decode_64bit_float": "double",
    "decode_string": "string"
}


class MappingKeyError(Exception):
    """Base class for other exceptions"""
    pass


class DuplicateParameterError(Exception):
    """Base class for other exceptions"""
    pass


class ObjectType(object):
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
        width, no_bytes = 1, 2

        comp = address.split("/")
        start = int(comp[0][1:])
        if len(comp) == 2:
            if comp[1] in ["1", "2"]:
                no_bytes = 1
            else:
                width = int(comp[1]) - int(comp[0]) + 1
                no_bytes = width * 2

        return start, width, no_bytes

    @staticmethod
    def __binary_map(binarystring):
        """
        position of True in binary string. Report if malformated in mapping.
        source for regular expression:
        https://stackoverflow.com/questions/469913/regular-expressions-is-there-an-and-operator
        :param binarystring: str
        :return: integer
        """
        if re.match(r"^0b(?=[01]{8}$)(?=[^1]*1[^1]*$)", binarystring):
            return binarystring.split("0b")[1][::-1].index('1')
        else:
            logging.error("Error in binary string in mapping.")
            sys.exit(500)

    @staticmethod
    def __trailing_byte_check(address):
        if len(address.split("/")) == 2:
            return address.split("/")[1] == "2"
        return False

    def __decode_byte(self, register, value, function):
        """
        decode payload messages from a modbus reponse message and enrich with
        add. parameters from input mapping
        :param register: string - key in dictionary mapping
        :param value: ? - result from payload decoder method
        :param function: string - decoder method
        :return: list with dictionary
        """
        decoded = list()

        if len(self.__register_maps[register]['map']) == 1:
            # if only one entry in map, add optional parameters, otherwise no
            optional = {
                key: self.__register_maps[register][key]
                for key in self.__register_maps[register]
                if key not in {'map',
                               'description',
                               'value',
                               'function',
                               'parameter',
                               'multiplier',
                               'offset',
                               'datatype'}
            }
        else:
            optional = dict()
        for key, name in self.__register_maps[register]['map'].items():
            decoded.append(dict(
                {
                    "parameter":
                        self.__register_maps[register]['parameter'],
                    "value": value[self.__binary_map(binarystring=key)],
                    "description": name,
                    "datatype": function2avro[function]
                },
                **optional)
            )

        return decoded

    def __decode_prop(self, register, value, function):
        """
        decode payload messages from a modbus reponse message and enrich with
        add. parameters from input mapping
        :param register: string - key in dictionary mapping
        :param value: ? - result from payload decoder method
        :param function: string - decoder method
        :return: list with dictionary
        """
        maps = self.__register_maps[register].get('map')
        desc = self.__register_maps[register].get('description')
        datatype = function2avro[function]
        optional = {
            key: self.__register_maps[register][key]
            for key in self.__register_maps[register]
            if key not in {'map',
                           'description',
                           'function',
                           'datatype',
                           'multiplier',
                           'offset'}
        }
        if datatype in ['int', 'long'] and not maps:
            # multiplier and/or offset make sense for int datatypes and when
            # no map is defined
            multiplier = self.__register_maps[register].get('multiplier', 1)
            offset = self.__register_maps[register].get('offset', 0)
            value = value * multiplier + offset
            if isinstance(value, float):
                datatype = "float"
        di = {"value": value,
              "datatype": datatype}
        if maps:
            desc = maps.get(str(round(value)))
        if desc:
            di["description"] = desc

        return [dict(**di,
                     **optional)]

    def __formatter(self, decoder, register, no_bytes):
        """
        format the output dictionary and append by scanning through the mapping
        of the registers. If gaps in the mappings are detected they are skipped
        by the number of bytes.
        :param decoder: A deferred response handle from the register readings
        :param register: dictionary
        :param no_bytes: int - no of bytes to decode for strings
        :return: list with dictionary
        """
        function = self.__register_maps[register]['function']
        if function not in function2avro:
            logging.error("Decoding function not defined.")
            sys.exit(500)
        if function == 'decode_bits':
            value = getattr(decoder, function)()
            return self.__decode_byte(register=register,
                                      value=value,
                                      function=function)
        elif function == "decode_string":
            encod = getattr(decoder, function)(no_bytes)
            # ToDo what kind of characters need to be removed?
#            value = re.sub(r'[^\x01-\x7F]+', r'', encod.decode())
            value = ''.join(list(s for s in encod.decode() if s.isprintable()))
        else:
            value = getattr(decoder, function)()

        return self.__decode_prop(register=register,
                                  value=value,
                                  function=function)

    def __formatter_bit(self, decoder, register):
        """
        indexes the result array of bits by the keys found in the mapping
        :param decoder: A deferred response handle from the register readings
        :param register: dictionary
        :return: list with dictionary
        """
        return [
            dict(
                **self.__register_maps[register],
                **{"datatype": function2avro["decode_bits"],
                   "value": decoder[0]}
            )
        ]

    def run(self):
        """
        reads the coil discrete input, input, or holding registers according
        to their length defined in key and decodes them accordingly. The
        list of dictionary/ies is appended to the result list
        :return: list - result
        """
        result = None
        decoded = list()

        for key in self.__register_maps.keys():
            start, width, no_bytes = self.__register_width(key)
            # read appropriate register(s)
            if self.__entity == '0':
                result = self.__client.read_coils(
                    address=start,
                    count=1,
                    unit=UNIT
                )
            elif self.__entity == '1':
                result = self.__client.read_discrete_inputs(
                    address=start,
                    count=1,
                    unit=UNIT
                )
            elif self.__entity == '3':
                result = self.__client.read_input_registers(
                    address=start,
                    count=width,
                    unit=UNIT
                )
            elif self.__entity == '4':
                result = self.__client.read_holding_registers(
                    address=start,
                    count=width,
                    unit=UNIT
                )
            assert (not result.isError())
            # decode and append to list
            if self.__entity in ['0', '1']:
                decoder = result.bits
                decoded = decoded + self.__formatter_bit(
                    decoder=decoder,
                    register=key
                )
            elif self.__entity in ['3', '4']:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    registers=result.registers,
                    byteorder=self.__endianness["byteorder"],
                    wordorder=self.__endianness["wordorder"]
                )
                # skip leading byte, if key = "xxxxx/2"
                if self.__trailing_byte_check(key):
                    decoder.skip_bytes(nbytes=1)
                decoded = decoded + self.__formatter(
                    decoder=decoder,
                    register=key,
                    no_bytes=no_bytes
                )

        return decoded


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


def retrieve(init):
    """
    invoke for monitoring
    :param init: dictionary - client parameter
        init["client"] instance- MODBUS client
        init["mapping"] mapping of all registers as from JSON
        init["endianness"] endianness's of byte and word
    :return: list of dictionaries (in asc order) for hk
    """
    register_class = ['0', '1', '3', '4']
    instance_list = list()
    decoded = list()

    for regs in register_class:
        instance_list.append(
            ObjectType(
                init=init,
                entity=regs
            )
        )
    for insts in instance_list:
        decoded = decoded + insts.run()

    return [dict(sorted(item.items())) for item in decoded]


def close(client):
    """
    close the client
    :param client: object
    :return:
    """
    client.close()


if __name__ == '__main__':

    argparser = argparse.ArgumentParser(
        description="Universal MODBUS Reader")
    argparser.add_argument('--device',
                           required=False,
                           help='Device extention (default: "default")',
                           default='default'
                           )
    myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: " \
               "%(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
    logging.basicConfig(format=myformat,
                        level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")
    to_housekeeping = dict()
    _start_time = timer()

    print("Device extention: {0}".format(argparser.parse_args().device))
    try:
        initial = initialize(argparser.parse_args().device)
        to_housekeeping = retrieve(init=initial)
        close(client=initial["client"])
    except SystemExit as e:
        exit("Error code {0}".format(e))
    print(json.dumps(to_housekeeping,
                     indent=4))
    print("Time consumed to process modbus interface: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    exit(0)
