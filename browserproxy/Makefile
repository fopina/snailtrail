browserpub: VERSION := $(shell git log --oneline -- . | wc -l | tr -d ' ')
browserpub:
	docker buildx build \
	              --platform linux/amd64,linux/arm64 \
				  --build-arg VERSION=$(VERSION) \
				  -t fopina/random:snailtrail-browser-$(VERSION) \
				  -t fopina/random:snailtrail-browser \
				  --push browserproxy
