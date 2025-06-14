# Use the official Python image.
FROM python:3.11-slim

# Set the working directory in the container.
WORKDIR /app

# Install git for the churn checker plugin
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the check script and all plugins into the container.
COPY run_checks.py .
COPY plugins/ /app/plugins/

# The entrypoint is the script that runs the checks.
# The actual repo and output directories will be mounted at runtime.
ENTRYPOINT ["python", "run_checks.py"]
