FROM python:3.12

RUN apt-get update
RUN apt-get -qq install libgeos++-dev libgeos-dev libgeos-c1v5 libgeos-dev libgeos-doc

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY mapper.py .

CMD [ "python", "mapper.py"]
