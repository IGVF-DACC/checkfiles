from checkfiles.checkfiles import is_file_gzipped, check_valid_gzipped_file_format, check_file_size
from checkfiles.checkfiles import check_md5sum, check_content_md5sum, bam_pysam_check


def test_is_file_gzipped_gzipped():
    is_gzipped = is_file_gzipped('src/tests/data/ENCFF594AYI.fastq.gz')
    assert is_gzipped == True


def test_is_file_gzipped_not_gzipped():
    is_gzipped = is_file_gzipped('src/tests/data/ENCFF080HPN.tsv')
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


def test_check_file_size_pass():
    errors = {}
    file_size = 100
    size_in_cloud_storage = 80
    check_file_size(errors, file_size, size_in_cloud_storage)
    assert errors == {
        'file_size': 'submitted file zise 100 does not mactch file zise 80 in cloud storage'}


def test_check_file_size_fail():
    errors = {}
    file_size = 100
    size_in_cloud_storage = 100
    check_file_size(errors, file_size, size_in_cloud_storage)
    assert errors == {}


def test_check_md5sum_pass():
    errors = {}
    md5sum = '3e814f4af7a4c13460584b26fbe32dc4'
    md5_base64 = 'PoFPSvekwTRgWEsm++MtxA=='
    check_md5sum(errors, md5sum, md5_base64)
    assert errors == {}


def test_check_md5sum_fail():
    errors = {}
    md5sum = '3e814f4af7a4c13460584b26fbe32dc4'
    md5_base64 = '5K7DItBBxvmH4X28+To0ZQ=='
    check_md5sum(errors, md5sum, md5_base64)
    assert errors == {
        'md5sum': 'submitted file md5sum 3e814f4af7a4c13460584b26fbe32dc4 does not mactch file md5sum e4aec322d041c6f987e17dbcf93a3465 in cloud storage'}


def test_check_content_md5sum_fail():
    errors = {}
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    check_content_md5sum(errors, file_path)
    assert errors == {
        'content_md5sum': 'content md5sum conflicts with content md5sum of existing file(s): ENCFF594AYI'}


def test_bam_pysam_check_invalid_bam_file():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    errors = {}
    number_of_reads = 158
    bam_pysam_check(errors, file_path, number_of_reads)
    assert errors == {'bam_error': "file is not valid bam file by SamtoolsError: 'samtools returned with error 8: stdout=, stderr=src/tests/data/ENCFF594AYI.fastq.gz had no targets in header.\\n'"}


def test_bam_pysam_check_number_of_read():
    file_path = 'src/tests/data/ENCFF206HGF.bam'
    errors = {}
    number_of_reads = 158
    bam_pysam_check(errors, file_path, number_of_reads)
    assert errors == {
        'bam_error': 'sumbitted number of reads 158 does not match number of reads 1709 in cloud storage'}
