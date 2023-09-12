FROM python:3.10

COPY . MODBUS/

WORKDIR MODBUS

RUN pip install --upgrade pip && \
    pip install -U -e . && \
    rm -f requirements.txt


CMD ["mb_client_rest_api"]   