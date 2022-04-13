#!/usr/bin/env python
"""
Flask REST API for multiple MODBUS reader and writer.

run: python3 mb_client_rest_api.py --host <host> (default: 127.0.0.1) --port
<port> (default: 5000)

version 1.1 - 2021/12/11

For a detailed description, see https://github.com/ccatp/MODBUS

Copyright (C) 2021 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""
from flask import Flask, jsonify, Response, g, abort
from flask_restx import Api, Resource, reqparse
import mb_client_writer
import mb_client_reader
import logging
import os
import json
from threading import Lock
from timeit import default_timer as timer
import argparse

"""
change history
2021/12/02 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.0 
    * initial version
2021/12/11 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.1 
    * included flask_restplus aka flask_restx
"""

__author__ = "Dr. Ralf Antonius Timmermann"
__copyright__ = "Copyright (C) Dr. Ralf Antonius Timmermann, AIfA, " \
                "University Bonn"
__credits__ = ""
__license__ = "BSD"
__version__ = "1.1"
__maintainer__ = "Dr. Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "Dev"

print(__doc__)

flask_app = Flask(__name__)
api = Api(app=flask_app,
          version='1.0',
          title="CCATp API For Device Management",
          description="(C) Ralf A. Timmermann, AIfA, University Bonn",
          license="license: BSD")

ns = api.namespace(
    'modbus',
    description="APIs for reading from/writing to various MODBUS devices"
)

# main parser
parser = reqparse.RequestParser()
# branch parser
parser_write = parser.copy()
parser_write.add_argument(name='payload',
                          required=True,
                          help="argument is of JSON format")


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


lock_mb_client = LockGroup()


@flask_app.teardown_request
def teardown_request(error=None):
    if error:
        logging.error(
            "Teardown_request: cleaning up...: {0}".format(str(error))
        )
    # if name exists
    try:
        if lock_mb_client(g.name).locked():
            logging.warning(
                "Release lock for: {0}".format(g.name)
            )
            lock_mb_client(g.name).release()
    except AttributeError:
        pass


@flask_app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404


@flask_app.errorhandler(500)
def server_error(e):
    return jsonify(error=str(e)), 500


@flask_app.errorhandler(503)
def service_unavailable(e):
    return jsonify(error=str(e)), 503


@ns.route("/write/<id>")
@ns.doc(params={"id": "deviceID"})
@api.expect(parser_write)
class WriteClass(Resource):
    @api.response(201, 'Success')
    @api.response(500, 'Server Error')
    @api.response(503, 'Service Unavailable')
    @api.response(404, 'Not Found')
    def put(self, id: str):
        _start_time = timer()
        g.name = id
        payload = json.loads(parser_write.parse_args()['payload'])
        if not payload:
            abort(404)
        try:
            lock_mb_client(id).acquire()
            initial = mb_client_writer.initialize(name=id)
            mb_client_writer.writer(init=initial,
                                    wr=payload)
            mb_client_writer.close(client=initial["client"])
            lock_mb_client(id).release()
        except SystemExit as e:
            abort(int(str(e)))
        logging.info(
            "Time consumed to process modbus writer: {0:.1f} ms".format(
                (timer() - _start_time) * 1000)
        )

        return Response(response=json.dumps(payload),
                        status=201)


@ns.route("/read/<id>")
@ns.doc(params={"id": "deviceID"})
class ReadClass(Resource):
    @api.response(200, 'Success')
    @api.response(500, 'Server Error')
    @api.response(503, 'Service Unavailable')
    @api.response(404, 'Not Found')
    def get(self, id: str):
        _start_time = timer()
        result = dict()
        g.name = id
        try:
            lock_mb_client(id).acquire()
            initial = mb_client_reader.initialize(name=id)
            result = mb_client_reader.retrieve(init=initial)
            mb_client_reader.close(client=initial["client"])
            lock_mb_client(id).release()
        except SystemExit as e:
            abort(int(str(e)))
        logging.info(
            "Time consumed to process modbus reader: {0:.1f} ms".format(
                (timer() - _start_time) * 1000)
        )

        return jsonify(result)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(
        description="REST API for Housekeeping and Device Control")
    argparser.add_argument(
        '--host',
        required=False,
        help='IP address for REST API (default: "127.0.0.1")',
        default='127.0.0.1'
    )
    argparser.add_argument(
        '--port',
        required=False,
        help='Port (default: 5000)',
        default=5000
    )

    myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: " \
               "%(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
    logging.basicConfig(format=myformat,
                        level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger().setLevel(logging.INFO)

    logging.info("PID: {0}".format(os.getpid()))

    print("Host: {0}, Port: {1}".format(
        argparser.parse_args().host,
        argparser.parse_args().port)
    )

    flask_app.run(host=argparser.parse_args().host,
                  port=argparser.parse_args().port,
                  threaded=True)
