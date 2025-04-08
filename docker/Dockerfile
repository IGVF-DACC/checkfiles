FROM ubuntu:22.04

ENV PYTHONDONTWRITEBYTECODE 1

ENV PYTHONUNBUFFERED 1

ENV VIRTUAL_ENV=/opt/venv

RUN useradd -u 1444 -m checkfiles

# default aws buckdet is the test folder: lattice-files
ARG AWS_BUCKET_NAME
ENV AWS_BUCKET_NAME=${AWS_BUCKET_NAME:lattice-files}
ENV AWS_DATA_DIR /s3
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    curl \
    zlib1g-dev \
    libsqlite3-dev \
    fuse \
    build-essential \
    libbz2-dev \
    liblzma-dev

RUN pip3 install awscli
RUN curl -sS -L -o /usr/local/bin/goofys https://github.com/kahing/goofys/releases/download/v0.24.0/goofys \
    && chmod +x /usr/local/bin/goofys

RUN curl -sS -L -o /usr/local/bin/validateFiles https://raw.githubusercontent.com/IGVF-DACC/validateFiles/main/validateFiles \
    && chmod +x /usr/local/bin/validateFiles

RUN mkdir -p /s3
RUN chmod 777 /s3

RUN python3 -m venv $VIRTUAL_ENV

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN chown -R  checkfiles:checkfiles $VIRTUAL_ENV

WORKDIR /scripts

COPY --chown=checkfiles:checkfiles scripts .

RUN chmod -R +x /scripts

WORKDIR /checkfiles

COPY --chown=checkfiles:checkfiles src/checkfiles .

USER checkfiles

# RUN python -m pip  install --upgrade pip
RUN python -m pip install wheel

RUN python -m pip install -r requirements.txt

ENTRYPOINT ["/scripts/entrypoint.sh"]

CMD ["python", "/checkfiles/checkfiles.py"]
