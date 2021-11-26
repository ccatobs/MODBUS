from flask import Flask, jsonify, request, Response
import modbus_writer
import modbus_client
import logging
import os
import json
from timeit import default_timer as timer

app = Flask(__name__)


@app.route('/write', methods=['PUT'])
def write():
    _start_time = timer()

    payload = request.json
    initial = modbus_writer.initialize()
    modbus_writer.writer(init=initial,
                         wr=payload)
    modbus_writer.close(client=initial["client"])

    logging.info("Time consumed to process modbus writer: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    return Response(response=json.dumps(payload),
                    status=201)


@app.route('/read', methods=['GET'])
def read():
    _start_time = timer()

    initial = modbus_client.initialize()
    result = modbus_client.retrieve(init=initial)
    modbus_client.close(client=initial["client"])

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
