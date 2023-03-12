#!/usr/bin/env python3

"""
auxiliary functions
"""

from timeit import default_timer
from functools import wraps
from threading import Lock
import logging
from typing import Callable


class LockGroup(object):
    """
    Returns a lock object, unique for each unique value of param.
    The first call with a given value of param creates a new lock, subsequent
    calls return the same lock.
    source:
    https://stackoverflow.com/questions/37624289/value-based-thread-lock
    """

    def __init__(self):
        self.__lock_dict = {}
        self.__lock = Lock()

    def __call__(self, param: str = None):
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
    works for decorated non-staticmethod functions in classes,
    because args[0] = self | cls.
    :param supersede: string (default=None)
    :return: Callable - function wrapped
    """

    def _decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
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
