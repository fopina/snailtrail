#!/bin/sh

# burp CE won't allow changing to LISTEN ON ALL INTERFACES via CLI - use socat to proxy
socat TCP4-LISTEN:8081,fork,reuseaddr TCP4:127.0.0.1:8080 &
# answer "yes" to terms of agreement
yes | java -Djava.awt.headless=true -jar burp.jar burp.StartBurp
