import os

# import logging
settings_file = os.path.abspath("{}/settings.toml".format(os.path.dirname(__file__)))
os.environ["SETTINGS_MODULE_FOR_DYNACONF"] = settings_file
os.environ["ENVVAR_PREFIX_FOR_DYNACONF"] = "MBCLIENT"

from dynaconf import settings
