import os
import sys


class PreRun(object):
    sys.path.append(os.environ.get('PYTHONPATH',
                                   "{0}{1}".format(os.path.dirname(
                                       os.path.realpath(__file__)),
                                       "/../")
                                   )
                    )