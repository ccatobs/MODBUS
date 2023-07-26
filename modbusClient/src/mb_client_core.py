#!/usr/bin/env python3

"""
MODBUS core class
"""

from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
import json
import re
import logging
from typing import Dict, List
# internal
from .mb_client_aux import MODBUS2AVRO, _throw_error

UNIT = 0x1


class _ObjectType(object):

    def __init__(
            self,
            init: Dict,
            entity: str
    ):
        """
        :param init: Dict - client parameter
            init["client"] instance - MODBUS client
            init["mapping"] mapping of all registers as from JSON
            init["endianness"] endianness's of byte and word
        :param entity: str - register prefix
        """
        self._entity = entity
        self.__client = init["client"]
        self.__endianness = init["endianness"]
        # select mapping for each entity and sort by key
        self.__register_maps = {
            key: value for key, value in
            sorted(init["mapping"].items()) if key[0] == self._entity
        }
        # parameter updated in registers after write to date, needs reset
        self.updated_items = dict()

    @property
    def entity(self): return self._entity

    def __register_width(
            self,
            address: str
    ) -> Dict:
        """
        determine the specs for an address
        :param address: string
        :return: Dict
            start - address to start from,
            width - no of 16-bit register
            no_bytes - no of total bytes contained
            pos_byte - position of byte in register (1: major, 2: minor)
        """
        width, no_bytes, pos_byte = 1, 2, 1  # default
        comp = address.split("/")
        start = int(comp[0][1:])
        if len(comp) == 2:
            if comp[1] in ["1", "2"]:
                no_bytes = 1
                pos_byte = int(comp[1])
            else:
                width = int(comp[1]) - int(comp[0]) + 1
                no_bytes = width * 2
        parameter = self.__register_maps[address]['parameter']
        function = self.__register_maps[address].get('function')
        if function:
            try:
                if MODBUS2AVRO(function).supersede:
                    width = MODBUS2AVRO.width(function)
                    no_bytes = MODBUS2AVRO.no_bytes(function)
            except ValueError:
                detail = "Decoding function '{0}' not defined for " \
                         "parameter '{1}'".format(function,
                                                  parameter)
                _throw_error(detail, 422)
        result = {
            "start": start,
            "width": width,
            "no_bytes": no_bytes,
            "pos_byte": pos_byte
        }
        logging.debug("register:{0} -> {1}".format(address,
                                                   json.dumps(result)))

        return result

    @staticmethod
    def __binary_map(binarystring: str) -> int:
        """
        position of True in binary string. Report if malformated in mapping.
        source for regular expression:
        https://stackoverflow.com/questions/469913/regular-expressions-is-there-an-and-operator
        :param binarystring: str
        :return: int
        """
        if re.match(r"^0b(?=[01]{8}$)(?=[^1]*1[^1]*$)", binarystring):
            return binarystring.split("0b")[1][::-1].index('1')
        else:
            detail = "Error in binary string in mapping."
            _throw_error(detail, 422)

    def __decode_byte(
            self,
            register: str,
            value: List[bool],
            function: str
    ) -> List[Dict]:
        """
        decode payload messages from a modbus reponse message and enrich with
        add. parameters from input mapping
        :param register: string - key in dictionary mapping
        :param value: List[bool] - result from payload decoder method
        :param function: string - decoder method
        :return: List of Dict
        """
        decoded = list()
        optional = dict()

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
                               'datatype',
                               'isTag'}
            }
        for key, name in self.__register_maps[register]['map'].items():
            decoded.append(
                dict(
                    {
                        "parameter":
                            self.__register_maps[register]['parameter'],
                        "value": value[self.__binary_map(binarystring=key)],
                        "description": name,
                        "datatype": MODBUS2AVRO(function).datatype,
                        "isTag": self.__register_maps[register].get('isTag',
                                                                    False)
                    },
                    **optional)
            )

        return decoded

    def __decode_prop(
            self,
            register: str,
            value: str | int | float,
            function: str
    ) -> List[Dict]:
        """
        decode payload messages from a modbus reponse message and enrich with
        add. parameters from input mapping
        :param register: string - key in dictionary mapping
        :param value: str | int | float - result from payload decoder method
        :param function: string - decoder method
        :return: List of Dict
        """
        maps = self.__register_maps[register].get('map')
        desc = self.__register_maps[register].get('description')
        datatype = MODBUS2AVRO(function).datatype
        optional = {
            key: self.__register_maps[register][key]
            for key in self.__register_maps[register]
            if key not in {'map',
                           'description',
                           'function',
                           'datatype',
                           'multiplier',
                           'offset',
                           'isTag'}
        }
        if datatype in ['int', 'long'] and not maps:
            # multiplier and/or offset make sense for int datatypes and when
            # no map is defined
            multiplier = self.__register_maps[register].get('multiplier', 1)
            offset = self.__register_maps[register].get('offset', 0)
            value = value * multiplier + offset
            if isinstance(value, float):
                datatype = "float"  # to serve Reinhold's AVRO schema
        di = {
            "value": value,
            "datatype": datatype,
            "isTag": self.__register_maps[register].get('isTag', False)
        }
        # add description if applicable
        if maps is not None:
            desc = maps.get(str(round(value)))
        if desc is not None:
            di["description"] = desc

        return [
            dict(
                **di,
                **optional
            )
        ]

    def __formatter(
            self,
            decoder: BinaryPayloadDecoder,
            register: str,
            no_bytes: int
    ) -> List[Dict]:
        """
        format the output dictionary and append by scanning through the mapping
        of the registers. If gaps in the mappings are detected they are skipped
        by the number of bytes.
        :param decoder: A deferred response handle from the register readings
        :param register: str
        :param no_bytes: int - no of bytes to decode for strings
        :return: List of Dict
        """
        value = None
        parameter = self.__register_maps[register]['parameter']
        function = self.__register_maps[register].get('function')

        match function:
            case None:
                detail = "Decoding function missing for " \
                         "parameter '{0}'".format(parameter)
                _throw_error(detail, 422)
            case 'decode_bits':
                return self.__decode_byte(register=register,
                                          value=getattr(decoder, function)(),
                                          function=function)
            case "decode_string":
                # Pending: what kind of characters need to be removed?
                # value = re.sub(r'[^\x01-\x7F]+', r'', encod.decode())
                try:
                    value = "".join(
                        list(s for s in
                             getattr(decoder, function)(no_bytes).decode() if
                             s.isprintable())
                    )
                except UnicodeDecodeError as e:
                    _throw_error(str(e))
                return self.__decode_prop(register=register,
                                          value=value,
                                          function=function)
            case _:
                return self.__decode_prop(register=register,
                                          value=getattr(decoder, function)(),
                                          function=function)

    def __formatter_bit(
            self,
            decoder: List,
            register: str
    ) -> List[Dict]:
        """
        indexes the result array of bits by the keys found in the mapping
        :param decoder: A deferred response handle from the register readings
        :param register: str
        :return: List of Dict
        """
        return [
            dict(
                **self.__register_maps[register],
                **{"datatype": MODBUS2AVRO("decode_bits").datatype,
                   "value": decoder[0],
                   "isTag": self.__register_maps[register].get('isTag',
                                                               False)
                   }
            )
        ]

    def __coil(
            self,
            wr: Dict
    ) -> None:
        """
        dictionary with "parameter: value" pairs to be changed in coil and
        holding registers
        :param wr: dictionary with {parameter: value} pairs
        :return:
        """
        for parameter, value in wr.items():
            for address, attributes in self.__register_maps.items():
                if attributes['parameter'] == parameter:
                    # coil register updates one-by-one
                    if self.__client.write_coil(
                        address=int(address),
                        value=value,
                        slave=UNIT
                    ).isError():
                        detail = "Error writing coil register at address " \
                                 "'{0}' with payload '{1}'".format(int(address),
                                                                   value)
                        _throw_error(detail, 422)
                    self.updated_items[parameter] = value
                    break

    def __holding(
            self,
            wr: Dict
    ) -> None:
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
                    # if match parameter - start
                    function = attributes['function'].replace("decode_", "add_")
                    reg_info = self.__register_width(address)

                    # disable updates of the minor byte of a register as a
                    # register can only be updated as a whole
                    if reg_info['pos_byte'] == 2:
                        detail = "Parameter '{0}': updates disabled for " \
                                 "the minor byte of a register" \
                            .format(parameter)
                        _throw_error(detail, 422)
                    if "_int" in function or "_uint" in function:
                        multiplier = attributes.get('multiplier', 1)
                        offset = attributes.get('offset', 0)
                        value = int((value - offset) / multiplier)
                    elif "_string" in function \
                            and len(value) > (2 * reg_info['width']):
                        detail = "'{0}' too long for parameter '{1}'" \
                            .format(value, parameter)
                        _throw_error(detail, 422)
                    elif "_bits" in function \
                            and (len(value) / 16) > reg_info['width']:
                        detail = "'{0}' too long for parameter '{1}'" \
                            .format(value, parameter)
                        _throw_error(detail, 422)

                    getattr(builder, function)(value)
                    payload = builder.to_registers()

                    if self.__client.write_registers(
                        address=reg_info['start'],
                        values=payload,
                        slave=UNIT
                    ).isError():
                        detail = "Error writing holding register at " \
                                 "address '{0}' with payload '{1}'" \
                            .format(reg_info['start'],
                                    payload)
                        _throw_error(detail, 422)
                    self.updated_items[parameter] = value
                    builder.reset()  # reset builder
                    break
                    # if match parameter - end

    def register_readout(self) -> List:
        """
        reads the coil discrete input, input, or holding registers according
        to their length defined in key and decodes them accordingly. The
        list of dictionary/ies is appended to the result
        :return: List
        """
        f = None
        decoded = list()

        for key in self.__register_maps.keys():
            reg_info = self.__register_width(key)
            # read appropriate register(s)
            match self._entity:
                case '0':
                    f = "read_coils"
                case '1':
                    f = "read_discrete_inputs"
                case '3':
                    f = "read_input_registers"
                case '4':
                    f = "read_holding_registers"

            result = getattr(self.__client, f)(
                address=reg_info['start'],
                count=reg_info['width'],
                slave=UNIT
            )
            if result.isError():
                detail = "Error reading register at address '{0}' and " \
                         "width '{1}' for MODBUS class '{2}'". \
                    format(reg_info['start'],
                           reg_info['width'],
                           self._entity)
                _throw_error(detail)

            # decode and append to list
            if self._entity in ['0', '1']:
                decoded = decoded + self.__formatter_bit(
                    decoder=result.bits,
                    register=key
                )
            elif self._entity in ['3', '4']:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    registers=result.registers,
                    byteorder=self.__endianness["byteorder"],
                    wordorder=self.__endianness["wordorder"]
                )
                # skip major byte, if key = "xxxxx/2"
                if reg_info['pos_byte'] == 2:
                    decoder.skip_bytes(nbytes=1)
                decoded = decoded + self.__formatter(
                    decoder=decoder,
                    register=key,
                    no_bytes=reg_info['no_bytes']
                )

        return decoded

    def register_write(
            self,
            wr: Dict
    ) -> None:
        """
        call coil or holding register writes
        :param wr: dictionary with {parameter: value} pairs
        :return:
        """
        self.updated_items.clear()  # reset

        match self._entity:
            case '4':
                self.__holding(wr=wr)
            case '0':
                self.__coil(wr=wr)
            # when attempting to writing to a read-only register, issue error
            case _:
                for parameter, value in wr.items():
                    for address, attributes in self.__register_maps.items():
                        if attributes['parameter'] == parameter:
                            detail = "Parameter '{0}' of MODBUS register " \
                                     "class '{1}' is not appropriate!" \
                                .format(parameter,
                                        self._entity)
                            _throw_error(detail, 202)
