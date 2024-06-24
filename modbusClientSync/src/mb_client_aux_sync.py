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


class MyException(Exception):
    def __init__(self,
                 status_code,
                 detail):
        super().__init__(status_code,
                         detail)
        self.status_code: int = status_code
        self.detail: str = detail


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

    def __call__(
            self,
            param: str = None
    ) -> Lock:
        with self.__lock:
            if param not in self.__lock_dict:
                self.__lock_dict[param] = Lock()
            return self.__lock_dict[param]


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


def _client_config(config_filename: str) -> Dict:
    config_device_class = None

    if config_filename:
        if os.path.exists(config_filename):
            config_device_class = config_filename
        else:
            detail = ("Optional client config file '{}' not found"
                      .format(config_filename))
            _throw_error(detail, 404)
    else:
        path_config = "{0}{1}".format(
            os.path.dirname(os.path.realpath(__file__)),
            "/../configFiles/"
        )
        dir_content = glob.glob1(path_config,
                                 "mb_client_config_*.json")
        if len(dir_content) != 1:
            detail = ("Client config file not found or multiple config "
                      "files found")
            _throw_error(detail, 404)
        else:
            config_device_class = "{0}{1}".format(
                path_config,
                dir_content[0]
            )
    logging.info("Config File: {0}".format(config_device_class))
    with open(config_device_class) as config_file:
        return json.load(config_file)


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
    def _decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = default_timer()
            result = func(*args, **kwargs)
            logging.debug(
                "Time utilized for '{0}' of '{1}': {2:.2f} ms".format(
                    func.__name__ if 'supersede' not in locals()
                                     or callable(supersede)
                                     or supersede is None else supersede,
                    args[0].__dict__.get('_ip', 'n.a.'),
                    (default_timer() - start_time) * 1_000
                )
            )

            return result

        return wrapper

    return _decorator(supersede) if callable(supersede) else _decorator


def defined_kwargs(**kwargs) -> Dict:
    return {k: v for k, v in kwargs.items() if v is not None}
