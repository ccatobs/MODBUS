FROM ubuntu:22.04

RUN apt-get update  \
    && apt-get install python3.10 -y \
    && apt-get install python3-pip -y

WORKDIR MODBUS

COPY modbusClient/ modbusClient/
COPY modbusServerSimulator/ modbusServerSimulator/
COPY Docker/ServerSimulator/python_wrapper.sh .
COPY RestAPI/mb_client_RestAPI.py RestAPI/
COPY requirements.txt .

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN ["chmod", "+x", "python_wrapper.sh"]

ENV PYTHONPATH .
ENV PORT ${PORT}
ENV HOST ${HOST}
ENV ServerPort ${ServerPort}
ENV Debug ${Debug}

CMD  ./python_wrapper.sh