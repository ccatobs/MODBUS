#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
enums required in sync and async client (no difference)
"""

from enum import Enum, EnumMeta


class MODBUS2FUNCTION(str, Enum):
    read_coils = '0'
    read_discrete_inputs = '1'
    read_input_registers = '3'
    read_holding_registers = '4'


class _MyMeta(EnumMeta):
    def __contains__(self, other) -> bool:
        try:
            self(other)
        except ValueError:
            return False
        else:
            return True


class MODBUS2AVRO(
    str,
    Enum,
    metaclass=_MyMeta
):
    A = ("decode_bits", "boolean", 8, True)
    B = ("decode_8bit_int", "int", 8, True)
    C = ("decode_8bit_uint", "int", 8, True)
    D = ("decode_16bit_int", "int", 16, True)
    E = ("decode_16bit_uint", "int", 16, True)
    F = ("decode_16bit_float", "float", 16, True)
    G = ("decode_32bit_int", "int", 32, True)
    H = ("decode_32bit_uint", "int", 32, True)
    J = ("decode_32bit_float", "float", 32, True)
    K = ("decode_64bit_int", "long", 64, True)
    L = ("decode_64bit_uint", "long", 64, True)
    M = ("decode_64bit_float", "double", 64, True)
    N = ("decode_string", "string", 16, False)

    def __new__(
            cls,
            key,
            datatype,
            no_bit,
            supersede
    ) -> Enum:
        obj = str.__new__(cls, [str])
        obj._value_ = key
        obj.datatype = datatype
        obj.no_bit = no_bit
        obj.supersede = supersede
        return obj

    @classmethod
    def no_bytes(cls, key) -> int: return int(cls(key).no_bit/8)
    @classmethod
    def width(cls, key) -> int: return max(int(cls(key).no_bit/16), 1)
