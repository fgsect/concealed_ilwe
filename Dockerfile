FROM ubuntu:22.04

RUN apt-get update && apt install -y python3-pip sqlite3

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

WORKDIR /service
RUN mkdir data
COPY regression.py sampler.py plot.py init.sql .
RUN sqlite3 /service/data/runs.db ".read /service/init.sql"

RUN echo "run" > status

CMD ["python3", "regression.py"]
