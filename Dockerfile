FROM ubuntu:20.04


WORKDIR /checkfiles
RUN mkdir -p /s3 && mkdir -p /google
ENV AWS_BUCKET_NAME checkfile-mingjie
ENV AWS_DATA_DIR /s3
ENV GOOGLE_BUCKET_NAME igvf-file-validation_test_files
ENV GOOGLE_DATA_DIR /google
ENV GOOGLE_APPLICATION_CREDENTIALS key.json
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    curl \
    fuse
RUN pip3 install awscli
RUN curl -sS -L -o /usr/local/bin/goofys https://github.com/kahing/goofys/releases/download/v0.24.0/goofys \
    && chmod +x /usr/local/bin/goofys

COPY entrypoint.sh /
CMD ["sh", "/entrypoint.sh"]
