FROM python:3
ADD requirements.txt /
RUN pip install -r requirements.txt

ADD run.py /

EXPOSE 8765

CMD [ "python", "./run.py" ]


