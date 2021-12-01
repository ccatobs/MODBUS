from flask import Flask, jsonify, request, Response, g, abort
import mb_client_writer
import mb_client_reader
import logging
import os
import json
from threading import Lock
from timeit import default_timer as timer

app = Flask(__name__)


class LockGroup(object):
    """
    Returns a lock object, unique for each unique value of param.
    The first call with a given value of param creates a new lock, subsequent
    calls return the same lock.
    source:
    https://stackoverflow.com/questions/37624289/value-based-thread-lock
    """

    def __init__(self):
        self.lock_dict = {}
        self.__lock = Lock()

    def __call__(self, param: str = None):
        with self.__lock:
            if param not in self.lock_dict:
                self.lock_dict[param] = Lock()
            return self.lock_dict[param]


lock_mb_client = LockGroup()


@app.teardown_request
def teardown_request(error=None):
    if error:
        logging.error(
            "Teardown_request: cleaning up...: {0}".format(str(error))
        )
    if lock_mb_client(g.name).locked():
        logging.warning(
            "Release lock for: {0}".format(g.name)
        )
        lock_mb_client(g.name).release()


@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404


@app.errorhandler(501)
def not_implemented(e):
    return jsonify(error=str(e)), 501


@app.route('/<name>/write', methods=['PUT'])
def write(name: str = None) -> json:
    _start_time = timer()
    g.name = name
    payload = request.json
    try:
        lock_mb_client(name).acquire()
        initial = mb_client_writer.initialize(name=name)
        mb_client_writer.writer(init=initial,
                                wr=payload)
        mb_client_writer.close(client=initial["client"])
        lock_mb_client(name).release()
    except SystemExit as e:
        abort(int(str(e)))
    logging.info("Time consumed to process modbus writer: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    return Response(response=json.dumps(payload),
                    status=201)


@app.route('/<name>/read', methods=['GET'])
def read(name: str = None) -> json:
    _start_time = timer()
    result = dict()
    g.name = name
    try:
        lock_mb_client(name).acquire()
        initial = mb_client_reader.initialize(name=name)
        result = mb_client_reader.retrieve(init=initial)
        mb_client_reader.close(client=initial["client"])
        lock_mb_client(name).release()
    except SystemExit as e:
        abort(int(str(e)))
    logging.info("Time consumed to process modbus reader: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    return jsonify(result)


if __name__ == '__main__':

    myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: " \
               "%(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
    logging.basicConfig(format=myformat,
                        level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger().setLevel(logging.INFO)

    logging.info("PID: {0}".format(os.getpid()))

    try:
        app.run(host='127.0.0.1',
                port=5000,
                threaded=True)
    except:
        logging.error("Unable to open port")
        exit(1)
