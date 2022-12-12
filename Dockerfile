FROM debian@sha256:a288aa7ad0e4d443e86843972c25a02f99e9ad6ee589dd764895b2c3f5a8340b
WORKDIR /checkfiles
ENV UID 42
RUN useradd -u ${UID} -m checkfilesuser

ENV VENV /opt/venv
# set running environments
# COPY key.json .
ENV GOOGLE_APPLICATION_CREDENTIALS key.json
ENV BUCKET_NAME igvf-file-validation_test_files

ENV DATA_DIR /mnt
RUN chown ${UID}:${UID} /mnt
ENV GOOGLE_COMPUTE_ZONE us-south1-b
ENV GOOGLE_PROJECT_ID igvf-file-validation

RUN apt-get update && apt-get install -y gnupg lsb-release curl
RUN export GCSFUSE_REPO=gcsfuse-`lsb_release -c -s` \
    && echo "deb http://packages.cloud.google.com/apt $GCSFUSE_REPO main" | tee /etc/apt/sources.list.d/gcsfuse.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    gcsfuse

RUN python3 -m venv ${VENV}
ENV PATH="$VENV/bin:$PATH"
RUN chown -R checkfilesuser:checkfilesuser $VENV
RUN chmod 755 -R /checkfiles
USER checkfilesuser
COPY src/ .

# Collect pip requirements
COPY requirements.txt .
COPY entrypoint.sh /
# Install pip requirements

RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt

CMD ["sh", "/entrypoint.sh"]
