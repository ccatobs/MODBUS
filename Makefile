# Makefile for building and running the Docker container

# Name of the Docker container
CONTAINER_NAME = modbus_client

# Docker build command
build:
	docker build -t $(CONTAINER_NAME) .

# Docker run command
run:
	docker run -p 4000:80 $(CONTAINER_NAME)

# Docker stop and remove container
stop:
	docker stop $(CONTAINER_NAME)
	docker rm $(CONTAINER_NAME)

# Docker remove image
clean:
	docker rmi $(CONTAINER_NAME)
