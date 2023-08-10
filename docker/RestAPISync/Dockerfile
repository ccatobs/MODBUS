FROM python:3.10

WORKDIR MODBUS

COPY modbusClientSync/ modbusClientSync/
COPY RestAPISync/mb_client_RestAPISync.py RestAPISync/
COPY requirements.txt .
# needs to be adapted according to the device class
COPY DeviceClassConfigs/mb_client_config_test.json modbusClient/configFiles/

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    rm -f requirements.txt

ENV PYTHONPATH .

ENTRYPOINT python -u RestAPISync/mb_client_RestAPISync.py --host ${HOST} --port ${PORT}