FROM python:3.9-slim

# FIXME use wheels and multistage to reduce size
RUN apt update \
 && apt install --no-install-recommends -y \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

ADD requirements.txt /
RUN pip install -r requirements.txt

WORKDIR /app
ADD snail /app/snail
ADD cli.py /app/

ENTRYPOINT [ "python", "-u", "/app/cli.py" ]
