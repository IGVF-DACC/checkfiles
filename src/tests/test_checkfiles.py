from checkfiles.checkfiles import is_file_gzipped, check_valid_gzipped_file_format


def test_is_file_gzipped_gzipped(blob_fastq_gz_small):
    is_gzipped = is_file_gzipped(blob_fastq_gz_small)
    assert is_gzipped == True


def test_is_file_gzipped_not_gzipped(blob_tsv):
    is_gzipped = is_file_gzipped(blob_tsv)
    assert is_gzipped == False


def test_check_valid_gzipped_file_format_no_error():
    errors = {}
    check_valid_gzipped_file_format(errors, True, 'tsv')
    assert errors == {}


def test_check_valid_gzipped_file_format_error_zip():
    errors = {}
    check_valid_gzipped_file_format(errors, True, 'bai')
    assert errors == {'gzip': 'bai file should not be gzipped'}


def test_check_valid_gzipped_file_format_error_unzip():
    errors = {}
    check_valid_gzipped_file_format(errors, False, 'bam')
    assert errors == {'gzip': 'bam file should be gzipped'}
