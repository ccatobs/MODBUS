from flask import Flask, jsonify, request, Response, g
import modbus_writer
import modbus_client
import logging
import os
import json
from threading import Lock
from timeit import default_timer as timer

app = Flask(__name__)

# ToDo
config = {"lhx": {
    "mapping": "file1",
    "config": "file2"
}}


class LockGroup(object):
    """
    source:
    https://stackoverflow.com/questions/37624289/value-based-thread-lock
    """
    def __init__(self):
        self.lock_dict = {}
        self.__lock = Lock()

    # Returns a lock object, unique for each unique value of param.
    # The first call with a given value of param creates a new lock, subsequent
    # calls return the same lock.
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


@app.route('/<name>/write', methods=['PUT'])
def write(name: str = None) -> json:
    _start_time = timer()
    g.name = name

    lock_mb_client(name).acquire()
    payload = request.json
    initial = modbus_writer.initialize()
    modbus_writer.writer(init=initial,
                         wr=payload)
    modbus_writer.close(client=initial["client"])
    lock_mb_client(name).release()

    logging.info("Time consumed to process modbus writer: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    return Response(response=json.dumps(payload),
                    status=201)


@app.route('/<name>/read', methods=['GET'])
def read(name: str = None) -> json:
    _start_time = timer()
    g.name = name
    
    lock_mb_client(name).acquire()
    initial = modbus_client.initialize()
    result = modbus_client.retrieve(init=initial)
    modbus_client.close(client=initial["client"])
    lock_mb_client(name).release()

    logging.info("Time consumed to process modbus reader: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    return jsonify(result)


if __name__ == '__main__':
    form = "%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s"
    logging.basicConfig(format=form,
                        level=logging.INFO,
                        datefmt="%H:%M:%S")
    logging.getLogger().setLevel(logging.INFO)

    logging.info("PID: {0}".format(os.getpid()))

    try:
        app.run(host='127.0.0.1',
                port=5000,
                threaded=False)
    except:
        logging.error("Unable to open port")
        exit(1)
