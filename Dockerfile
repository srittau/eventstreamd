FROM python:3.11-bullseye

# Prepare virtualenv
RUN mkdir /app
WORKDIR /app
RUN mkdir ./run
RUN python3 -m venv ./virtualenv

# Install eventstreamd
RUN ./virtualenv/bin/pip install eventstreamd

# Install application
COPY README.md NEWS.md ./

# Install configuration
COPY docker.conf ./

# Start eventstreamd
EXPOSE 8888
COPY start.sh ./
CMD ["/app/start.sh"]
