FROM python:3

COPY tools/apt-install-base /
RUN /apt-install-base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . /code/

ENV PYTHONPATH="/code/:/code/moka"

CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 \
    --threads 8 --timeout 0 config.wsgi:application \
    # -c /code/moka/config/gunicorn_conf.py \ # Enable opentelemetry
    # --preload # Without reload
    # --reload # With reload