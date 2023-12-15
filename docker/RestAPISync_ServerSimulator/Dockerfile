FROM ubuntu:22.04

RUN apt-get update  \
    && apt-get install python3.10 -y \
    && apt-get install python3-pip -y

WORKDIR MODBUS

COPY modbusClientSync/ modbusClientSync/
COPY modbusServerSimulator/ modbusServerSimulator/
COPY docker/ServerSimulator/python_wrapper.sh .
COPY RestAPISync/mb_client_RestAPISync.py RestAPISync/
COPY requirements.txt .
# needs to be adapted according to the device class
COPY DeviceClassConfigs/mb_client_config_test.json modbusClient/configFiles/

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    rm -f requirements.txt
RUN ["chmod", "+x", "python_wrapper.sh"]

ENV PYTHONPATH .
ENV PORT ${PORT}
ENV HOST ${HOST}
ENV SERVERPORT ${SERVERPORT}
ENV DEBUG ${DEBUG}

CMD  ./python_wrapper.sh