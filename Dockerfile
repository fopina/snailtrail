FROM python:3.9-slim as builder

RUN apt update \
 && apt install --no-install-recommends -y \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

ADD requirements.txt /

RUN --mount=type=cache,target=/wheels \
    cp /requirements.txt /wheels \
 && pip wheel -r /requirements.txt --wheel-dir=/wheels \
 && rm -fr /root/.cache/pip/


FROM python:3.9-slim

# crazy noop to force buildkit to build previous stage
COPY --from=builder /etc/passwd /etc/passwd

RUN --mount=type=cache,target=/wheels \
    pip install --find-links=/wheels -r /wheels/requirements.txt \
 && rm -fr /root/.cache/pip/

WORKDIR /app
ADD snail /app/snail
ADD scommon /app/scommon
ADD cli /app/cli
ADD main.py /app/

ARG VERSION dev
ENV SNAILBOT_VERSION=${VERSION}

ENTRYPOINT [ "python", "-u", "/app/main.py" ]
