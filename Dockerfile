FROM ubuntu:20.04


WORKDIR /checkfiles
RUN mkdir -p /s3
# default aws buckdet is the test folder: checkfiles-test in igvf-dev
ARG AWS_BUCKET_NAME
ENV AWS_BUCKET_NAME=${AWS_BUCKET_NAME:-checkfiles-test}
ENV AWS_DATA_DIR /s3
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    curl \
    zlib1g-dev \
    libsqlite3-dev \
    fuse

RUN pip3 install awscli
RUN curl -sS -L -o /usr/local/bin/goofys https://github.com/kahing/goofys/releases/download/v0.24.0/goofys \
    && chmod +x /usr/local/bin/goofys

COPY src/ src/

# Collect pip requirements
COPY requirements.txt .
COPY entrypoint.sh /
# Install pip requirements

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["sh", "/entrypoint.sh"]
