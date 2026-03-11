.PHONY: build install clean test

BINARY_NAME=prom-fetcher
INSTALL_PATH=$(HOME)/.local/bin

build:
	go mod tidy
	go build -o $(BINARY_NAME) .

install: build
	mkdir -p $(INSTALL_PATH)
	cp $(BINARY_NAME) $(INSTALL_PATH)/
	@echo "Installed to $(INSTALL_PATH)/$(BINARY_NAME)"
	@echo "Make sure $(INSTALL_PATH) is in your PATH"

clean:
	rm -f $(BINARY_NAME)

test:
	go test -v ./...

# Development build with debug info
build-dev:
	go build -gcflags="all=-N -l" -o $(BINARY_NAME) .

# Static binary build for distribution
build-static:
	CGO_ENABLED=0 GOOS=linux go build -a -ldflags '-extldflags "-static"' -o $(BINARY_NAME) .
