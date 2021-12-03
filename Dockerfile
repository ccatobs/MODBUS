FROM ubuntu:18.04

RUN apt-get update && apt-get upgrade \
    && apt-get install python3.8 -y \
    && apt-get install python3-pip -y

WORKDIR /code
COPY src/ .

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

RUN ["chmod", "+x", "/code/docker_wrapper.sh"]

cmd ./python_wrapper.sh

#RUN apt-get update && apt-get install -y net-tools
#CMD netstat -tunlp
#RUN HOSTIP=`ip -4 addr show scope global dev eth0 | grep inet | awk '{print \$2}' | cut -d / -f 1`
#RUN echo $HOSTIP
#ENTRYPOINT python -u modbus_server.py

# command to run on container start
# python [-u] forces the stdout and stderr streams to be unbuffered.
# ENTRYPOINT python -u mb_client_rest_api.py --host 0.0.0.0 --port 5000
