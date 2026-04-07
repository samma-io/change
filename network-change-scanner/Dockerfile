FROM python:3.12-slim

RUN apt-get update && apt-get install -y traceroute && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY code/ /code/

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /out

CMD ["python", "scan.py"]
