import json
import logging
import sys
from timeit import default_timer as timer

import click

# Import your MODBUSClientSync and MyException classes
from .mb_client_sync import MODBUSClientSync, MyException, __version__


@click.group()
def modbus():
    """Universal MODBUS CLI"""


@modbus.command("writer")
@click.option("--host", required=True, type=str, help="MODBUS Server Device IP/Name")
@click.option("--port", default=502, type=int, help="MODBUS Server Port (default: 502)")
@click.option(
    "--debug", is_flag=True, default=False, help="Debug Mode (default: False)"
)
@click.option("--config_filename", default="", type=str, help="path to config file")
@click.option(
    "--payload",
    required=True,
    type=str,
    help="Payload ('{parameter1: value1, parameter2: value2, ...}')",
)
def main(host, port, debug, config_filename, payload):
    """Universal MODBUS Writer"""
    _start_time = timer()
    try:
        mb_client = MODBUSClientSync(
            host=host, port=port, debug=debug, config_filename=config_filename
        )
        to_monitoring = mb_client.write_register(json.loads(payload))
        mb_client.close()
    except MyException as e:
        logging.error("Code=%s, detailoggingl=%s", e.status_code, e.detail)
        sys.exit(1)

    logging.info(json.dumps(to_monitoring, indent=2))
    logging.info(
        "Time consumed to process the MODBUS writer: %.1f ms",
        (timer() - _start_time) * 1000,
    )
    sys.exit(0)


@modbus.command("reader")
@click.option("--host", required=True, type=str, help="MODBUS Server Device IP/Name")
@click.option("--port", default=502, type=int, help="MODBUS Server Port (default: 502)")
@click.option(
    "--debug", is_flag=True, default=False, help="Debug Mode (default: False)"
)
@click.option("--config_filename", default="", type=str, help="path to config file")
@click.option(
    "--bulk_read", is_flag=True, default=False, help="toggle bulk read default: False"
)
def mb_client_reader(host, port, debug, config_filename, bulk_read):
    _start_time = timer()
    try:
        mb_client = MODBUSClientSync(
            host=host, port=port, debug=debug, config_filename=config_filename
        )
        if bulk_read:
            to_housekeeping = mb_client.read_register_bulk()
        else:
            to_housekeeping = mb_client.read_register()
        mb_client.close()
    except MyException as e:
        print("Code={0}, detail={1}".format(e.status_code, e.detail))
        sys.exit(1)

    print(json.dumps(to_housekeeping, indent=2))
    print(
        "Time consumed to process MODBUS interface: {0:.1f} ms".format(
            (timer() - _start_time) * 1000
        )
    )
    sys.exit(0)
