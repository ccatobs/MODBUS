FROM python:3.10

WORKDIR /code

COPY modbusClient/ /code/modbusClient/
COPY modbusServerSimulator/ /code/modbusServerSimulator/
COPY requirements.txt /code/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT python -u modbusClient/src/mb_client_RestAPI.py --host '0.0.0.0' --port 5090