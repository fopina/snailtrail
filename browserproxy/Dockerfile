ARG BASESLIM=python:3.9-slim

# Chrome dockerfile based on https://github.com/justinribeiro/dockerfiles/blob/master/chrome-headless/Dockerfile
FROM  ${BASESLIM}

# FIXME use wheels and multistage to reduce size
RUN apt update \
 && apt install --no-install-recommends -y \
    chromium-driver \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
COPY main.py /entry.py

ENTRYPOINT [ "python", "-u", "/entry.py" ]
