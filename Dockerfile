FROM python:3.10.16

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install -r requirements.txt

COPY start.sh /code/
RUN chmod +x /code/start.sh
CMD ["/code/start.sh"]


