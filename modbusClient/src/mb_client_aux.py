#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
auxiliary functions
"""

from timeit import default_timer
from functools import wraps
from threading import Lock
import os
import glob
import json
import logging
from typing import Callable, Any, Dict
from enum import Enum, EnumMeta


class MyException(Exception):
    def __init__(self,
                 status_code,
                 detail):
        super().__init__(status_code,
                         detail)
        self.status_code = status_code
        self.detail = detail


def _throw_error(detail: str,
                 status_code: int = 400) -> None:
    """
    internal: throws a logging error plus raises an exception
    :param detail: error message
    :param status_code: http status code (default: 400)
    :return:
    """
    logging.error(detail)
    raise MyException(status_code=status_code,
                      detail=detail)


def _client_config() -> Dict:
    path_config = "{0}{1}".format(
        os.path.dirname(os.path.realpath(__file__)),
        "/../configFiles/"
    )
    dir_content = glob.glob1(path_config,
                             "mb_client_config_*.json")
    if len(dir_content) != 1:
        detail = "Client config file not found or multiple config files found."
        _throw_error(detail, 404)
    else:
        config_device_class = "{0}{1}".format(
            path_config,
            dir_content[0]
        )
        logging.info("Config File: {0}".format(config_device_class))
        with open(config_device_class) as config_file:
            return json.load(config_file)


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


class LockGroup(object):
    """
    Returns a lock object, unique for each unique value of param.
    The first call with a given value of param creates a new lock, subsequent
    calls return the same lock.
    source:
    https://stackoverflow.com/questions/37624289/value-based-thread-lock
    """

    def __init__(self):
        self.__lock_dict = dict()
        self.__lock = Lock()

    def __call__(self,
                 param: str = None) -> Lock:
        with self.__lock:
            if param not in self.__lock_dict:
                self.__lock_dict[param] = Lock()
            return self.__lock_dict[param]


def mytimer(supersede: Callable | str = None) -> Callable:
    """
    wrapper around function for which the consumed time is measured in
    DEBUG mode. Call either via mytimer, mytimer(), or
    mytimer("<supersede function name>").
    Caveat:
    works for decorated non-static method functions in classes,
    because args[0] = self | cls.
    :param supersede: string (default=None)
    :return: Callable - function wrapped
    """
    def _decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = default_timer()
            result = func(*args, **kwargs)
            logging.debug(
                "Time utilized for '{0}' of '{1}': {2:.2f} ms".format(
                    func.__name__ if 'supersede' not in locals()
                                     or callable(supersede)
                                     or supersede is None else supersede,
                    args[0].__dict__.get('_MODBUSClient__device', 'n.a.'),
                    (default_timer() - start_time) * 1_000
                )
            )

            return result

        return wrapper

    return _decorator(supersede) if callable(supersede) else _decorator


def defined_kwargs(**kwargs) -> Dict:
    return {k: v for k, v in kwargs.items() if v is not None}
