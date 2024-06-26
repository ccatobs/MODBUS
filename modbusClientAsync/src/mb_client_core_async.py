#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MODBUS core class
"""

from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
import json
import re
import logging
from typing import Dict, List, Any
import asyncio
# internal
from .mb_client_aux_async import _throw_error, defined_kwargs
from .mb_client_enums_async import MODBUS2AVRO, MODBUS2FUNCTION

UNIT = 0x1
FEATURE_EXCLUDE_SET = {
    'map',
    'function',
    'multiplier',
    'offset',
    'min',
    'max',
    'unit'
}
FEATURE_ALLOWED_SET = {
    'parameter',
    'function',
    'description',
    'alias',
    'unit',
    'defaultValue',
    'map',
    'isTag',
    'min',
    'max',
    'multiplier',
    'offset'
}


class _ObjectTypeAsync(object):

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
        # select mapping for each entity and sort by register number
        self.__register_maps = {
            k: v for k, v in
            sorted(init["mapping"].items()) if k[0] == self._entity
        }
        # parameter updated in registers after write to date, needs reset
        self.updated_items = dict()

    @property
    def entity(self) -> str: return self._entity

    def __register_width(
            self,
            address: str
    ) -> Dict[str, int]:
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

        function = self.__register_maps[address].get('function')
        if function:
            if MODBUS2AVRO(function).supersede:
                width = MODBUS2AVRO.width(function)
                no_bytes = MODBUS2AVRO.no_bytes(function)
        result = {
            "start": start,
            "width": width,
            "no_bytes": no_bytes,
            "pos_byte": pos_byte
        }
        logging.debug("register:{0} -> {1}".format(address,
                                                   json.dumps(result)))

        return result

    def __decode_byte(
            self,
            register: str,
            value: List[bool],
            function: str
    ) -> List[Dict[str, bool | str]]:
        """
        decode payload messages from a modbus reponse message and enrich with
        add. parameters from input mapping
        :param register: string - key in dictionary mapping
        :param value: List[bool] - result from payload decoder method
        :param function: string - decoder method
        :return: List of Dict for each parameter_alt
        """
        optional = dict()
        one_map_entry = False
        register_maps = self.__register_maps[register]
        desc = register_maps.get('description')
        alias = register_maps.get('alias')
        maps = register_maps.get('map')

        if not maps:
            _throw_error("Register {} lacks bit map feature".format(register))
        if len(maps) == 1:
            one_map_entry = True
            # if only one entry in map, add optional parameters, no otherwise
            optional = {
                k: register_maps[k]
                for k in register_maps
                if k not in FEATURE_EXCLUDE_SET
            }

        return [
            {
                "parameter": register_maps['parameter'],
                "value": value[k.split("0b")[1][::-1].index('1')],
                "datatype": MODBUS2AVRO(function).datatype
            } |
            defined_kwargs(
                parameter_alt=v if not one_map_entry else None,
                value_alt=v if one_map_entry else None,
                description=desc if not one_map_entry else None,
                alias=alias if not one_map_entry else None,
            ) |
            optional
            for k, v in maps.items()
        ]

    def __decode_prop(
            self,
            register: str,
            value: str | int | float,
            function: str
    ) -> List[Dict[str, Any]]:
        """
        decode payload messages from a modbus reponse message and enrich with
        add. parameters from input mapping
        :param register: string - key in dictionary mapping
        :param value: str | int | float - result from payload decoder method
        :param function: string - decoder method
        :return: List of Dict for each parameter
        """
        register_maps = self.__register_maps[register]
        maps = register_maps.get('map')
        datatype = MODBUS2AVRO(function).datatype
        optional = {
            k: register_maps[k]
            for k in register_maps
            if k not in FEATURE_EXCLUDE_SET
        }

        if datatype in ['int', 'long'] and not maps:
            # multiplier and/or offset make sense for int data types and when
            # no map is defined
            value = (value
                     * register_maps.get('multiplier', 1)
                     + register_maps.get('offset', 0))
            if isinstance(value, float):
                datatype = "float"  # to serve AVRO schema
        di = {
            "value": value,
            "datatype": datatype
        }
        # add "value_alt" if feature map provided and other optional features
        # pass on min & max to output for int & float
        di.update(**defined_kwargs(
            value_alt=maps.get(str(round(value)),
                               "corresponding value not found in map")
            if maps is not None else None,
            min=register_maps.get('min'),
            max=register_maps.get('max')
        )
                  )

        return [di | optional]

    def __formatter(
            self,
            decoder: BinaryPayloadDecoder,
            register: str,
            no_bytes: int
    ) -> List[Dict[str, Any]]:
        """
        format the output dictionary and append by scanning through the mapping
        of the registers. If gaps in the mappings are detected they are skipped
        by the number of bytes.
        :param decoder: A deferred response handle from the register readings
        :param register: str
        :param no_bytes: int - no of bytes to decode for strings
        :return: List of Dict
        """
        function = self.__register_maps[register].get('function')

        match function:
            case 'decode_bits':
                return self.__decode_byte(register=register,
                                          value=getattr(decoder, function)(),
                                          function=function)
            case "decode_string":
                # Pending: characters to be removed?
                # value = re.sub(r'[^\x01-\x7F]+', r'', encod.decode())
                value = ""
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
    ) -> List[Dict[str, bool | str]]:
        """
        indexes the result array of bits by the keys found in the mapping
        :param decoder: A deferred response handle from the register readings
        :param register: str
        :return: List of Dict
        """
        return [
            {
                k: v for k, v in self.__register_maps[register].items()
                if k not in FEATURE_EXCLUDE_SET
            } |
            {
                "datatype": MODBUS2AVRO("decode_bits").datatype,
                "value": decoder[0]
            }
        ]

    async def __coil(
            self,
            wr: Dict
    ) -> None:
        """
        dictionary with "parameter: value" pairs to be changed in coil and
        holding registers
        :param wr: dictionary with {parameter: value} pairs
        :return:
        """
        async def write_coil(
                parm: str,
                add: str,
                val: Any
        ) -> None:
            rr = await self.__client.write_coil(
                address=int(add),
                value=val,
                slave=UNIT
            )
            if rr.isError():
                detail = (("Error writing coil register at address "
                           "'{0}' with payload '{1}'")
                          .format(int(add), val))
                _throw_error(detail, 422)
            self.updated_items[parm] = val
        # end nested function

        coros = list()
        for parameter, value in wr.items():
            for address, attributes in self.__register_maps.items():
                # coil register updates one-by-one in async mode
                if attributes['parameter'] == parameter:
                    coros.append(
                        write_coil(
                            parm=parameter,
                            add=address,
                            val=value)
                    )
                    break
        for _ in await asyncio.gather(*coros):
            continue

    async def __holding(
            self,
            wr: Dict
    ) -> None:
        """
        dictionary with "parameter: value" pairs to be changed in coil and
        holding registers
        :param wr: dictionary with {parameter: value, ...} pair(s) to be updated
        :return:
        """

        def test_min_max() -> None:
            minimum = attributes.get('min')
            maximum = attributes.get('max')
            if minimum:
                if value < minimum:
                    _throw_error(
                        ("Error encountered for '{2}' when writing value: "
                         "{0} < {1} (min)".format(value, minimum, parameter)),
                        422
                    )
            if maximum:
                if value > maximum:
                    _throw_error(
                        ("Error encountered for '{2}' when writing value: "
                         "{0} > {1} (max)".format(value, maximum, parameter)),
                        422
                    )

        async def write_holding(
                add: int,
                values: Any,
                val: Any,
                parm: str
        ) -> None:
            rr = await self.__client.write_registers(
                    address=add,
                    values=values,
                    slave=UNIT
            )
            if rr.isError():
                detail = (("Error writing to holding "
                           "register address '{0}' with payload '{1}'")
                          .format(add, values))
                _throw_error(detail, 422)
            self.updated_items[parm] = val
        # end nested functions

        builder = BinaryPayloadBuilder(
            byteorder=self.__endianness['byteorder'],
            wordorder=self.__endianness['wordorder']
        )

        coros = list()
        for parameter, value in wr.items():
            for address, attributes in self.__register_maps.items():
                if attributes['parameter'] == parameter:
                    # if match parameter - start
                    function = attributes['function'].replace("decode_", "add_")
                    reg_info = self.__register_width(address=address)

                    # disable update of solely a register's minor byte
                    if reg_info['pos_byte'] == 2:
                        detail = (("Parameter '{0}': updates disabled for "
                                   "the minor byte of a register")
                                  .format(parameter))
                        _throw_error(detail, 422)

                    # test min or max exceeded
                    if re.match(".+_(int|uint|float)$", function):
                        test_min_max()

                    # apply multiplier and/or offset
                    if re.match(".+_(int|uint)$", function):
                        value = int(
                            (value - attributes.get('offset', 0))
                            / attributes.get('multiplier', 1)
                        )

                    elif "_string" in function:
                        # printability
                        try:
                            if not value.isprintable():
                                raise ValueError
                        except (AttributeError, ValueError) as e:
                            detail = ("'{0}' seems not printable for "
                                      "parameter '{1}' with error: {2}"
                                      .format(value,
                                              parameter,
                                              str(e)))
                            _throw_error(detail, 422)
                        # test max length of string
                        if len(value) > (2 * reg_info['width']):
                            detail = ("'{0}' too long for parameter '{1}'"
                                      .format(value,
                                              parameter))
                            _throw_error(detail, 422)

                    # test max length of bit list
                    elif ("_bits" in function
                          and (len(value) / 16) > reg_info['width']):
                        detail = ("'{0}' too long for parameter '{1}'"
                                  .format(value,
                                          parameter))
                        _throw_error(detail, 422)

                    try:
                        getattr(builder, function)(value)
                    except Exception as e:
                        detail = ("Error in BinaryPayloadBuilder: {}"
                                  .format(str(e)))
                        _throw_error(detail, 422)
                    payload = builder.to_registers()
                    coros.append(
                        write_holding(
                            add=reg_info['start'],
                            values=payload,
                            val=value,
                            parm=parameter
                        )
                    )
                    builder.reset()  # reset builder
                    break
                # if match parameter - end

        for _ in await asyncio.gather(*coros):
            continue

    async def register_readout(self) -> List[Dict[str, Any]]:
        """
        reads the coil discrete input, input, or holding registers according
        to their length defined in key and decodes them accordingly. The
        list of dictionary/ies is appended to the result
        :return: List
        """

        async def acquire(register: str) -> List[Dict[str, Any]]:
            reg_info = self.__register_width(address=register)
            result = await getattr(self.__client,
                                   MODBUS2FUNCTION(self._entity).name)(
                address=reg_info['start'],
                count=reg_info['width'],
                slave=UNIT
            )
            if result.isError():
                detail = (
                    ("Error reading register at address '{0}' and width "
                     "'{1}' for MODBUS class '{2}'")
                    .format(reg_info['start'],
                            reg_info['width'],
                            self._entity))
                _throw_error(detail)

            # decode and append to list
            if self._entity in ['0', '1']:
                return self.__formatter_bit(
                    decoder=result.bits,
                    register=register
                )
            else:  # self._entity in ['3', '4']
                decoder = BinaryPayloadDecoder.fromRegisters(
                    registers=result.registers,
                    byteorder=self.__endianness["byteorder"],
                    wordorder=self.__endianness["wordorder"]
                )
                if reg_info['pos_byte'] == 2:  # skip major byte: key="xxxxx/2"
                    decoder.skip_bytes(nbytes=1)
                return self.__formatter(
                    decoder=decoder,
                    register=register,
                    no_bytes=reg_info['no_bytes']
                )
        # end nested function

        decoded: List = list()
        coros = [acquire(register) for register in self.__register_maps.keys()]
        for item in await asyncio.gather(*coros):
            decoded += item  # item comprises multiple elements if map

        return [  # sort by feature
            {k: v for k, v in sorted(item.items())} for item in decoded
        ]

    async def register_write(
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
                await self.__holding(wr=wr)
            case '0':
                await self.__coil(wr=wr)
            # when attempting to writing to a read-only register, issue error
            case _:
                for parameter, value in wr.items():
                    for address, attributes in self.__register_maps.items():
                        if attributes['parameter'] == parameter:
                            detail = (("Parameter '{0}' of MODBUS register "
                                       "class '{1}' is not appropriate!")
                                      .format(parameter,
                                              self._entity))
                            _throw_error(detail, 202)
