FROM ubuntu:22.04

RUN apt-get update  \
    && apt-get install python3.10 -y \
    && apt-get install python3-pip -y
#    && apt-get install -y net-tools

WORKDIR /code

COPY modbusClient/ /code/modbusClient/
COPY modbusServerSimulator/ /code/modbusServerSimulator/
COPY python_wrapper.sh /code

RUN pip3 install --upgrade pip
RUN pip3 install -r modbusClient/requirements.txt
RUN ["chmod", "+x", "python_wrapper.sh"]

CMD ./python_wrapper.sh
