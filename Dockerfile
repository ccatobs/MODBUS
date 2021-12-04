FROM ubuntu:18.04

RUN apt-get update && apt-get upgrade \
    && apt-get install python3.8 -y \
    && apt-get install python3-pip -y
#    && apt-get install -y net-tools

WORKDIR /code

COPY src/ /code
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN ["chmod", "+x", "python_wrapper.sh"]

cmd ./python_wrapper.sh
