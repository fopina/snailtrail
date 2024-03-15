test:
	pytest --doctest-modules --cov

doctest:
	pytest --doctest-modules cli snail

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
	pytest integration_tests --cov snail

lint:
	isort .
	black .