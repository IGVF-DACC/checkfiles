from checkfiles.checkfiles import is_file_gzipped, check_valid_gzipped_file_format, check_file_size
from checkfiles.checkfiles import check_md5sum, check_content_md5sum, bam_pysam_check, fastq_check, file_validation, get_local_file_path


def test_is_file_gzipped_gzipped():
    is_gzipped = is_file_gzipped('src/tests/data/ENCFF594AYI.fastq.gz')
    assert is_gzipped == True


def test_is_file_gzipped_not_gzipped():
    is_gzipped = is_file_gzipped('src/tests/data/ENCFF080HPN.tsv')
    assert is_gzipped == False


def test_check_valid_gzipped_file_format_no_error():
    error = check_valid_gzipped_file_format(True, 'tsv')
    assert error == {}


def test_check_valid_gzipped_file_format_error_zip():
    error = check_valid_gzipped_file_format(True, 'bai')
    assert error == {'gzip': 'bai file should not be gzipped'}


def test_check_valid_gzipped_file_format_error_unzip():
    error = check_valid_gzipped_file_format(False, 'bam')
    assert error == {'gzip': 'bam file should be gzipped'}


def test_check_file_size_pass():
    file_size = 100
    size_in_cloud_storage = 80
    error = check_file_size(file_size, size_in_cloud_storage)
    assert error == {
        'file_size': 'submitted file zise 100 does not mactch file zise 80 in cloud storage'}


def test_check_file_size_fail():
    file_size = 100
    size_in_cloud_storage = 100
    error = check_file_size(file_size, size_in_cloud_storage)
    assert error == {}


def test_check_md5sum_pass():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    md5sum = '3e814f4af7a4c13460584b26fbe32dc4'
    etag = None
    error = check_md5sum(md5sum, etag, file_path)
    assert error == {}


def test_check_md5sum_fail():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    md5sum = 'invalid_md5sum'
    etag = None
    error = check_md5sum(md5sum, etag, file_path)
    assert error == {
        'md5sum': 'submitted file md5sum invalid_md5sum does not mactch file md5sum 3e814f4af7a4c13460584b26fbe32dc4 in cloud storage'}


def test_check_content_md5sum_fail():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    error = check_content_md5sum(file_path)
    assert error == {
        'content_md5sum': 'content md5sum 1fa9f74aa895c4c938e1712bedf044ec conflicts with content md5sum of existing file(s): ENCFF594AYI'}


def test_bam_pysam_check_invalid_bam_file():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    number_of_reads = 158
    error = bam_pysam_check(file_path, number_of_reads)
    assert error == {'bam_error': "file is not valid bam file by SamtoolsError: 'samtools returned with error 8: stdout=, stderr=src/tests/data/ENCFF594AYI.fastq.gz had no targets in header.\\n'"}


def test_bam_pysam_check_number_of_read():
    file_path = 'src/tests/data/ENCFF206HGF.bam'
    number_of_reads = 158
    error = bam_pysam_check(file_path, number_of_reads)
    assert error == {
        'bam_error': 'sumbitted number of reads 158 does not match number of reads 1709 in cloud storage'}


def test_fastq_check_number_fail():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    number_of_reads = 1
    read_length = 1
    error = fastq_check(file_path, number_of_reads, read_length)
    assert error == {
        'fastq_number_of_reads': 'sumbitted number of reads 1 does not match number of reads 25 in cloud storage',
        'fastq_read_length': 'sumbitted read length 1 does not match read length 58 in cloud storage'
    }


def test_main_fastq(mocker):
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    bucket_name = 'checkfile-mingjie'
    key = '2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF594AYI.fastq.gz'
    uuid = 'a3b754b6-0213-4ed4-a5f3-124f90273561'
    md5sum = '3e814f4af7a4c13460584b26fbe32dc4'
    file_format = 'fastq'
    output_type = 'reads'
    file_size = 1371
    number_of_reads = 25
    read_length = 58
    mocker.patch('checkfiles.checkfiles.get_local_file_path',
                 return_value=file_path)
    mocker.patch('botocore.client.BaseClient._make_api_call',
                 return_value={
                     'ETag': '"3e814f4af7a4c13460584b26fbe32dc4"',
                     'ContentLength': 1371
                 })
    result = file_validation(bucket_name, key, uuid, md5sum,
                             file_format, output_type, file_size, number_of_reads, read_length)
    assert result == {
        'uuid': 'a3b754b6-0213-4ed4-a5f3-124f90273561',
        'validation_result': 'failed',
        'errors': {'content_md5sum': 'content md5sum 1fa9f74aa895c4c938e1712bedf044ec conflicts with content md5sum of existing file(s): ENCFF594AYI'}
    }


def test_main_bam(mocker):
    file_path = 'src/tests/data/ENCFF206HGF.bam'
    bucket_name = 'checkfile-mingjie'
    key = '2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF206HGF.bam'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '2d3b7df013d257c7052c084d93ff9026'
    file_format = 'bam'
    output_type = 'alignments'
    file_size = 118126
    number_of_reads = 1709
    read_length = 58

    mocker.patch('checkfiles.checkfiles.get_local_file_path',
                 return_value=file_path)

    mock_response_session = mocker.Mock()
    mock_response_session.json.return_value = {
        '@graph': []
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_session)

    mocker.patch('botocore.client.BaseClient._make_api_call',
                 return_value={
                     'ETag': '"2d3b7df013d257c7052c084d93ff9026"',
                     'ContentLength': 118126
                 })

    result = file_validation(bucket_name, key, uuid, md5sum,
                             file_format, output_type, file_size, number_of_reads, read_length)
    assert result == {
        'uuid': '5b887ab3-65d3-4965-97bd-42bea7358431',
        'validation_result': 'pass'
    }


def test_main_tabular(mocker):
    file_path = 'src/tests/data/ENCFF500IBL.tsv'
    bucket_name = 'checkfile-mingjie'
    key = '2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF500IBL.tsv'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '4b0b3c68fafc5a26d0fc6150baadaa5b'
    file_format = 'tsv'
    output_type = 'element quantifications'
    file_size = 118126
    number_of_reads = 1709
    read_length = 58

    mocker.patch('checkfiles.checkfiles.get_local_file_path',
                 return_value=file_path)

    mock_response_get_local_file_path = mocker.Mock()
    mock_response_get_local_file_path.json.return_value = {
        '@graph': []
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_get_local_file_path)

    mocker.patch('botocore.client.BaseClient._make_api_call',
                 return_value={
                     'ETag': '"4b0b3c68fafc5a26d0fc6150baadaa5b"',
                     'ContentLength': 118126
                 })

    result = file_validation(bucket_name, key, uuid, md5sum,
                             file_format, output_type, file_size, number_of_reads, read_length)
    assert result == {
        'uuid': '5b887ab3-65d3-4965-97bd-42bea7358431',
        'validation_result': 'failed',
        'errors': {
            'gzip': 'tsv file should be gzipped',
            'tabular_file_error': [[None, 1, 'incorrect-label', ''], [None, 2, 'incorrect-label', ''], [None, 3, 'incorrect-label', ''], [60, 24, 'type-error', "type is \"boolean/default\""], [61, 24, 'type-error', "type is \"boolean/default\""]]
        }
    }


def test_get_local_file_path():
    blob_name = 'ENCFF594AYI.fastq.gz'
    file_path = get_local_file_path(blob_name)
    assert file_path == '/s3/ENCFF594AYI.fastq.gz'
