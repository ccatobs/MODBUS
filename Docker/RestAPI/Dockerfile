FROM python:3.10

WORKDIR MODBUS

COPY modbusClient/ modbusClient/
COPY RestAPI/mb_client_RestAPI.py RestAPI/
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PYTHONPATH .

ENTRYPOINT python -u RestAPI/mb_client_RestAPI.py --host ${HOST} --port ${PORT}