test:
	pytest --doctest-modules --cov

all: test pub deploy

build:
	docker build -t x .

pub:
	docker buildx build \
	              --platform linux/amd64,linux/arm64 \
				  --build-arg VERSION=$(shell git log --oneline . | wc -l | tr -d ' ') \
				  -t fopina/random:snailtrail-$(shell git log --oneline . | wc -l | tr -d ' ') \
				  -t fopina/random:snailtrail \
				  --push .

deploy:
	# add portainer service webhook to portainer.conf
	curl $(shell cat portainer.conf) -d tag=snailtrail-$(shell git log --oneline . | wc -l | tr -d ' ')

sit:
	pytest integration_tests --allow-hosts=127.0.0.1 --cov snail
