# Use an official Debian image for ARMv7 architecture, which is compatible with Raspberry Pi 3/4
FROM arm32v7/python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Install system-level dependencies required by OpenCV and the project
# - ffmpeg: For video stream processing
# - libsm6, libxext6: Common dependencies for OpenCV's GUI functions
# - git: Good practice to have for versioning
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    git \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copy the entire project into the container's working directory
COPY . .

# Make the installation script executable
RUN chmod +x v2/deployment/install.sh

# Set the default command to run the installation script.
# This will be the main test.
# Note: The install script is interactive and will require user input for the username.
# For a fully automated test, you could modify the install script to accept a username as an argument.
CMD ["/bin/bash", "-c", "./v2/deployment/install.sh && sleep infinity"]
