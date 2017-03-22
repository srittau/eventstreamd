FROM python:3.6

# Prepare virtualenv
RUN mkdir /app
WORKDIR /app
RUN mkdir ./run
RUN python3.6 -m venv ./virtualenv
RUN ./virtualenv/bin/pip install --upgrade pip setuptools

# Install dependencies
COPY ./requirements.txt .
RUN ./virtualenv/bin/pip install -r requirements.txt

# Install application
COPY README.md setup.py ./
COPY bin/ ./bin
COPY evtstrd/ ./evtstrd
COPY evtstrd_test/ ./evtstrd_test
RUN ./virtualenv/bin/pip install .
RUN rm -r requirements.txt README.md setup.py evtstrd evtstrd_test bin

# Install configuration
COPY docker.conf ./

# Start eventstreamd
EXPOSE 8888
CMD ["/app/virtualenv/bin/eventstreamd", "-c", "/app/docker.conf"]
