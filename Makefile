build:
	docker build -t x .

pub:
	docker buildx build \
	              --platform linux/amd64,linux/arm64 \
				  -t fopina/random:snailtrail-$(shell git log --oneline . | wc -l | tr -d ' ') \
				  -t fopina/random:snailtrail \
				  --push .
