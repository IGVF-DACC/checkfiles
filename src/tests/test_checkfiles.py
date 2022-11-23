from checkfiles.checkfiles import is_file_gzipped


def test_is_file_gzipped_gzipped(blob_fastq_gz_small):
    is_gzipped = is_file_gzipped(blob_fastq_gz_small)
    assert is_gzipped == True
