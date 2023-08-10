FROM python:3.10

WORKDIR MODBUS

COPY modbusClientAsync/ modbusClientAsync/
COPY RestAPIAsync/mb_client_RestAPIAsync.py RestAPIAsync/
COPY requirements.txt .
# needs to be adapted according to the device class
COPY DeviceClassConfigs/mb_client_config_test.json modbusClientAsync/configFiles/

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    rm -f requirements.txt

ENV PYTHONPATH .

ENTRYPOINT python -u RestAPIAsync/mb_client_RestAPIAsync.py --host ${HOST} --port ${PORT}