FROM python:3.10

WORKDIR /code

COPY modbusClient/ /code/modbusClient/
COPY modbusServerSimulator/ /code/modbusServerSimulator/
COPY requirements.txt /code/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT python -u src/mb_client_RestAPI.py