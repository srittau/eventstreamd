FROM python:3.6

# Prepare virtualenv
RUN mkdir /app
WORKDIR /app
RUN python3.6 -m venv ./virtualenv
RUN ./virtualenv/bin/pip install --upgrade pip setuptools

# Install dependencies
COPY ./requirements.txt .
RUN ./virtualenv/bin/pip install -r requirements.txt

# Copy application
COPY README.md setup.py ./
COPY bin/ ./bin
COPY evtstrd/ ./evtstrd
COPY evtstrd_test/ ./evtstrd_test
RUN ./virtualenv/bin/pip install .

# Start eventstreamd
EXPOSE 8888
CMD ["/app/virtualenv/bin/python", "/app/bin/eventstreamd"]
