# Variables
IMAGE_NAME = fcolista/alpine-package-monitor
TAG ?= latest

# Build the Docker image
build:
	docker build -t $(IMAGE_NAME):$(TAG) .

# Push the Docker image to Docker Hub
push:
	docker push $(IMAGE_NAME):$(TAG)

# Build and push the Docker image
build-push: build push

# Tag the Docker image with a version
tag:
	docker tag $(IMAGE_NAME):$(TAG) $(IMAGE_NAME):$(VERSION)

# Build, tag, and push the Docker image with a version
build-tag-push: build tag push
