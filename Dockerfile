FROM python:3.7-alpine

RUN apk add --no-cache --virtual .build-deps gcc g++ musl-dev
RUN pip install cython

ADD run.py /
ADD requirements.txt /

RUN pip install -r requirements.txt
RUN apk del .build-deps gcc musl-dev

EXPOSE 8765

CMD [ "python", "./run.py" ]


