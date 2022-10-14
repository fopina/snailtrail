FROM openjdk:11.0.2-jre-slim

RUN apt update || true \
 && apt install -y \
    curl \
    socat \
 && rm -rf /var/lib/apt/lists/*

RUN curl 'https://portswigger-cdn.net/burp/releases/download?product=community&version=2022.8.5&type=Jar' -o /burp.jar

COPY entrypoint.sh /entrypoint.sh

EXPOSE 8081

ENTRYPOINT [ "/entrypoint.sh" ]
