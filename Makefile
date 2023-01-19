test:
	pytest --doctest-modules --cov

all: test pub deploy

build:
	docker build -t x .

pub:
	docker buildx build \
	              --platform linux/amd64,linux/arm64 \
				  --build-arg VERSION=$(shell git log --oneline . | wc -l | tr -d ' ') \
				  --cache-from type=registry,ref=fopina/random:snailtrail-build-cache \
				  --cache-to type=registry,ref=fopina/random:snailtrail-build-cache,mode=max \
				  -t fopina/random:snailtrail-$(shell git log --oneline . | wc -l | tr -d ' ') \
				  -t fopina/random:snailtrail \
				  --push .

deploy:
	# add portainer service webhook to portainer.conf
	curl $(shell cat portainer.conf) -d tag=snailtrail-$(shell git log --oneline . | wc -l | tr -d ' ')

sit:
	pytest integration_tests --allow-hosts=127.0.0.1 --cov snail

burppub: VERSION := $(shell git log --oneline -- burpdocker | wc -l | tr -d ' ')
burppub:
	docker buildx build \
	              --platform linux/amd64,linux/arm64 \
				  --build-arg VERSION=$(VERSION) \
				  -t fopina/random:snailtrail-burp-$(VERSION) \
				  -t fopina/random:snailtrail-burp \
				  --push burpdocker

browserpub: VERSION := $(shell git log --oneline -- browserproxy | wc -l | tr -d ' ')
browserpub:
	docker buildx build \
	              --platform linux/amd64,linux/arm64 \
				  --build-arg VERSION=$(VERSION) \
				  -t fopina/random:snailtrail-browser-$(VERSION) \
				  -t fopina/random:snailtrail-browser \
				  --push browserproxy

gotlspub: VERSION := $(shell git log --oneline -- gotlsproxy | wc -l | tr -d ' ')
gotlspub:
	docker buildx build \
	              --platform linux/amd64,linux/arm64 \
				  --build-arg VERSION=$(VERSION) \
				  -t fopina/random:snailtrail-gotls-$(VERSION) \
				  -t fopina/random:snailtrail-gotls \
				  --push gotlsproxy
