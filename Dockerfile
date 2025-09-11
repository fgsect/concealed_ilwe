FROM ubuntu:22.04

RUN apt-get update && apt install -y python3-pip sqlite3

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

WORKDIR /service
COPY regression.py sampler.py plot.py init.sql .
#RUN sqlite3 /service/data/runs.db ".read /service/init.sql"
RUN mkdir /service/db && sqlite3 /service/db/default.db ".read /service/init.sql"

RUN echo "run" > status

CMD test -f /service/data/runs.db || echo "db does not exist yet, copying default db" && cp /service/db/default.db  /service/data/runs.db; python3 regression.py
