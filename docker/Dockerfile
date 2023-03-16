FROM --platform=linux/amd64 ubuntu:20.04

ENV PYTHONDONTWRITEBYTECODE 1

ENV PYTHONUNBUFFERED 1

ENV VIRTUAL_ENV=/opt/venv

RUN useradd -u 1444 -m checkfiles

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    build-essential \
    libbz2-dev \
    liblzma-dev \
    curl \
    zlib1g-dev \
    libsqlite3-dev 


RUN curl -sS -L -o /usr/local/bin/validateFiles https://raw.githubusercontent.com/IGVF-DACC/validateFiles/main/validateFiles \
    && chmod 755 /usr/local/bin/validateFiles

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
