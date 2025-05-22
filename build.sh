#!/bin/bash

# Build the image
docker build -t ajpio/troubleshoot-llm:latest .

# Push to registry
docker push ajpio/troubleshoot-llm:latest 