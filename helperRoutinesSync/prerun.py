import os
import sys


class PreRun(object):
    if os.environ.get('PYTHONPATH') is None:
        sys.path.append("{0}{1}".format(
            os.path.dirname(
                os.path.realpath(__file__)
            ),
            "/../")
        )