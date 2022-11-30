import pytest
from google.cloud import storage

PROJECT_ID = 'igvf-file-validation'
BUCKET_NAME = 'igvf-file-validation_test_files'


@pytest.fixture
def blob_fastq_gz_small():
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob('ENCFF594AYI.fastq.gz')
    return blob


@pytest.fixture
def blob_tsv():
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob('ENCFF080HPN.tsv')
    return blob
