FROM python:3.10

WORKDIR /code

COPY modbusClient/ modbusClient/
COPY RestAPI/mb_client_RestAPI.py .
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT python -u mb_client_RestAPI.py --host '0.0.0.0' --port 5090