FROM ubuntu:22.04

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv

# Add build arguments for IGVF API credentials
ARG IGVF_API_KEY=""
ARG IGVF_SECRET_KEY=""

# Set as environment variables
ENV IGVF_API_KEY=$IGVF_API_KEY
ENV IGVF_SECRET_KEY=$IGVF_SECRET_KEY

# Create non-root user
RUN useradd -u 1444 -m checkfiles

# Install base system packages and Python 3.12
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    build-essential \
    libbz2-dev \
    liblzma-dev \
    curl \
    zlib1g-dev \
    libsqlite3-dev \
    jq \
    wget \
    git \
    cmake \
    libboost-all-dev \
    libncurses-dev \
    libcurl4-openssl-dev \
    rustc \
    cargo \
    && rm -rf /var/lib/apt/lists/*

# Install samtools
RUN wget https://github.com/samtools/samtools/releases/download/1.20/samtools-1.20.tar.bz2 \
    && tar xvjf samtools-1.20.tar.bz2 \
    && cd samtools-1.20/ \
    && make \
    && make install \
    && cd .. \
    && rm -rf samtools-1.20*

# Install vcf_assembly_checker
RUN wget https://github.com/EBIvariation/vcf-validator/releases/download/v0.10.0/vcf_assembly_checker_linux \
    && chmod 755 vcf_assembly_checker_linux \
    && cp vcf_assembly_checker_linux /usr/bin/vcf_assembly_checker \
    && rm vcf_assembly_checker_linux

# Install fastq_stats
RUN git clone https://github.com/IGVF-DACC/fastq_stats.git \
    && cd fastq_stats \
    && cargo build --release \
    && cp target/release/fastq_stats /usr/bin \
    && chmod 755 /usr/bin/fastq_stats \
    && cd .. \
    && rm -rf fastq_stats

# Install validateFiles
RUN curl -sS -L -o /usr/local/bin/validateFiles https://raw.githubusercontent.com/IGVF-DACC/validateFiles/main/validateFiles \
    && chmod +x /usr/local/bin/validateFiles

# Set up Python virtual environment
RUN python3.12 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN chown -R  checkfiles:checkfiles $VIRTUAL_ENV

RUN mkdir -p /scripts

COPY --chown=checkfiles:checkfiles scripts/entrypoint.sh /scripts/entrypoint.sh

RUN chmod +x /scripts/entrypoint.sh

# Create the base directory structure
WORKDIR /checkfiles

# Copy entire src directory to maintain repository structure
COPY --chown=checkfiles:checkfiles src/ /checkfiles/src/

# Change working directory to checkfiles module
WORKDIR /checkfiles/src/checkfiles

# Install Python dependencies
RUN python -m pip install -r requirements.txt

# Download reference files for VCF validation to the correct location
RUN python utils/download_ref_files.py --local-dir /checkfiles/src/checkfiles/supporting_files/

# Change ownership of all files to checkfiles user
RUN chown -R checkfiles:checkfiles /checkfiles/

USER checkfiles

WORKDIR /checkfiles

ENTRYPOINT ["/scripts/entrypoint.sh"]
