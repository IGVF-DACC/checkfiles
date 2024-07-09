import datetime

from checkfiles.checkfiles import check_valid_gzipped_file_format, fasta_check
from checkfiles.checkfiles import make_content_md5sum_search_url, check_md5sum, check_content_md5sum, bam_pysam_check, fastq_get_average_read_length_and_number_of_reads, file_validation
from checkfiles.checkfiles import get_validate_files_args, validate_files_check, validate_files_fastq_check, tabular_file_check
from checkfiles.checkfiles import PortalAuth
from checkfiles.checkfiles import upload_credentials_are_expired
from checkfiles.file import File
from checkfiles.file import FileValidationRecord
from checkfiles.file import get_file


def test_check_valid_gzipped_file_format_no_error():
    error = check_valid_gzipped_file_format(True, 'tsv')
    assert error == {}


def test_check_valid_gzipped_file_format_error_zip():
    error = check_valid_gzipped_file_format(True, 'bai')
    assert error == {'gzip': 'bai file should not be gzipped'}


def test_check_valid_gzipped_file_format_error_unzip():
    error = check_valid_gzipped_file_format(False, 'bam')
    assert error == {'gzip': 'bam file should be gzipped'}


def test_bam_pysam_check_invalid_bam_file():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    error = bam_pysam_check(file_path)
    assert error == {'bam_error': "file is not valid bam file by SamtoolsError: 'samtools returned with error 8: stdout=, stderr=src/tests/data/ENCFF594AYI.fastq.gz had no targets in header.\\n'"}


def test_bam_pysam_check_number_of_read():
    file_path = 'src/tests/data/ENCFF206HGF.bam'
    result = bam_pysam_check(file_path)
    assert result == {'bam_number_of_reads': 1709}


def test_fastq_get_average_read_length_and_number_of_reads():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    result = fastq_get_average_read_length_and_number_of_reads(file_path)
    assert result == {
        'read_count': 25,
        'mean_read_length': 58,
        'maximum_read_length': 58,
        'minimum_read_length': 58
    }


def test_fastq_get_average_read_length_and_number_of_reads_invalid_fastq():
    file_path = 'does/not/exist'
    result = fastq_get_average_read_length_and_number_of_reads(file_path)
    assert result == {}


def test_get_validate_files_args():
    args = get_validate_files_args(
        'bed', 'bed3+', 'src/schemas/genome_builds/human/GRCh38/chrom.sizes')
    assert args == [
        '-tab',
        '-type=bed3+',
        'chromInfo=src/schemas/genome_builds/human/GRCh38/chrom.sizes',
    ]


def test_validate_files_check_pass():
    file_path = 'src/tests/data/ENCFF597JNC.bed.gz'
    file_format = 'bed'
    file_format_type = 'bed3'
    assembly = 'GRCh38'
    error = validate_files_check(
        file_path, file_format, file_format_type, assembly)
    assert error == {}


def test_validate_files_check_invalid_chrom():
    file_path = 'src/tests/data/invalid_chrom.bed'
    file_format = 'bed'
    file_format_type = 'bed3'
    assembly = 'GRCh38'
    error = validate_files_check(
        file_path, file_format, file_format_type, assembly)
    assert error == {
        'validate_files': 'Error [file=src/tests/data/invalid_chrom.bed, line=1]: chrom chr1xxx not found [chr1xxx\t0\t10000]\nAborting ... found error.'}


def test_validate_files_check_invalid_size():
    file_path = 'src/tests/data/invalid_size.bed'
    file_format = 'bed'
    file_format_type = 'bed3'
    assembly = 'GRCh38'
    error = validate_files_check(
        file_path, file_format, file_format_type, assembly)
    assert error == {
        'validate_files': 'Error [file=src/tests/data/invalid_size.bed, line=1]: bed->chromEnd[348956422] > chromSize[248956422] [chr1\t0\t348956422]'}


def test_fasta_check_pass():
    file_path = 'src/tests/data/ENCFF329FTG.fasta.gz'
    is_gzipped = True
    error = fasta_check(file_path, is_gzipped)
    assert error == {}


def test_fasta_check_invalid_start():
    file_path = 'src/tests/data/fasta_invalid_start.fasta'
    is_gzipped = False
    error = fasta_check(file_path, is_gzipped)
    assert error == {
        'fasta_error': 'the first line does not start with a > (rule 1 violated).'}


def test_fasta_check_invalid_seq():
    file_path = 'src/tests/data/fasta_invalid_seq.fasta'
    is_gzipped = False
    error = fasta_check(file_path, is_gzipped)
    assert error == {
        'fasta_error': 'there are characters in a sequence line other than [A-Za-z]'}


def test_fasta_check_duplicate():
    file_path = 'src/tests/data/fasta_duplicate.fasta'
    is_gzipped = False
    error = fasta_check(file_path, is_gzipped)
    assert error == {
        'fasta_error': 'there are duplicate sequence identifiers in the file (rule 7 violated)'}


def test_validate_files_fastq_check_invalid_quality():
    file_path = 'src/tests/data/fastq_invalid_quality.fastq'
    error = validate_files_fastq_check(file_path)
    assert error == {
        'validate_files': 'Error [file=src/tests/data/fastq_invalid_quality.fastq, line=4]: quality not as long as sequence (58 bases) [AGAA...<.<<G<<.<<.GGAGGGGGAGGAGGAGG..<.GGA.<A.]\nAborting .. found 1 error', }


def test_validate_files_fastq_check_invalid_seq():
    file_path = 'src/tests/data/fastq_invalid_seq.fastq'
    error = validate_files_fastq_check(file_path)
    assert error == {
        'validate_files': 'Error [file=src/tests/data/fastq_invalid_seq.fastq, line=2]: invalid DNA chars in sequence(TGCTTCTGTGTA5TTTTTATTTGAAGATATTTTCTTTTCAATCATAGGGCAGATCGGA)\nAborting .. found 1 error'}


def test_validate_files_fastq_check_pass():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    error = validate_files_fastq_check(file_path)
    assert error == {}


def test_tabular_file_check_guide_rna_sequences_valid():
    file_path = 'src/tests/data/guide_rna_sequences_valid.tsv'
    error = tabular_file_check('guide RNA sequences', file_path)
    assert error == {}


def test_tabular_file_check_guide_rna_sequences_invalid():
    file_path = 'src/tests/data/guide_rna_sequences_invalid.tsv'
    error = tabular_file_check('guide RNA sequences', file_path)
    assert error == {
        'tabular_file_error': [
            [2, 1, 'constraint-error', 'constraint "required" is "True"'],
            [2, 3, 'constraint-error', 'constraint "enum" is "[\'safe-targeting\', '"'non-targeting', 'targeting', 'positive control', "'\'negative control\', \'variant\']"'],
            [2, 5, 'type-error', 'type is "integer/default"'],
            [2, 7, 'constraint-error', 'constraint "enum" is "[\'+\', \'-\']"'],
            [2, 14, 'type-error', 'type is "array/default"']
        ]
    }


def test_main_empty_file(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/empty_file.txt'
    key = '2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/empty_file.txt'
    uuid = 'a3b754b6-0213-4ed4-a5f3-124f90273561'
    md5sum = '3e814f4af7a4c13460584b26fbe32dc4'
    file_format = 'txt'
    output_type = 'reads'
    file_format_type = None
    assembly = None
    portal_auth = None

    file = get_file(file_path, file_format)
    validation_record = FileValidationRecord(file, uuid)
    validation_record.original_etag = 'foobar'
    mock_response_session = mocker.Mock()
    mock_response_session.json.return_value = {
        '@graph': [
            {
                'accession': 'ENCFF123ABC'
            }
        ]
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_session)
    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result.errors == {'file_size': 'file has zero size'}


def test_main_fastq(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    key = '2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF594AYI.fastq.gz'
    uuid = 'a3b754b6-0213-4ed4-a5f3-124f90273561'
    md5sum = '3e814f4af7a4c13460584b26fbe32dc4'
    file_format = 'fastq'
    output_type = 'reads'
    file_format_type = None
    assembly = None
    portal_auth = None

    file = get_file(file_path, file_format)
    validation_record = FileValidationRecord(file, uuid)
    validation_record.original_etag = 'foobar'
    mock_response_session = mocker.Mock()
    mock_response_session.json.return_value = {
        '@graph': [
            {
                'accession': 'ENCFF594AYI'
            }
        ]
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_session)
    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)

    assert result.validation_success == False
    assert result.original_etag == 'foobar'
    assert result.info == {
        'content_md5sum': '1fa9f74aa895c4c938e1712bedf044ec',
        'file_size': 1371,
        'read_count': 25,
        'mean_read_length': 58,
        'minimum_read_length': 58,
        'maximum_read_length': 58
    }
    assert result.errors == {
        'content_md5sum_error': 'content md5sum 1fa9f74aa895c4c938e1712bedf044ec conflicts with content md5sum of existing file(s): ENCFF594AYI'
    }


def test_main_bam(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/ENCFF206HGF.bam'
    key = '2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF206HGF.bam'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '2d3b7df013d257c7052c084d93ff9026'
    file_format = 'bam'
    output_type = 'alignments'
    file_format_type = None
    assembly = None
    portal_auth = None

    file = get_file(file_path, file_format)
    validation_record = FileValidationRecord(file, uuid)
    validation_record.original_etag = 'foobar'

    mock_response_session = mocker.Mock()
    mock_response_session.json.return_value = {
        '@graph': []
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_session)

    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result.validation_success == True
    assert result.info == {
        'content_md5sum': '9095bad36672afefd7bf9165d89b4eb5',
        'file_size': 118126,
        'bam_number_of_reads': 1709
    }


def test_main_tabular_tsv(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/ENCFF500IBL.tsv'
    key = '2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF500IBL.tsv'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '4b0b3c68fafc5a26d0fc6150baadaa5b'
    file_format = 'tsv'
    output_type = 'element quantifications'
    file_format_type = None
    assembly = None
    portal_auth = None

    file = get_file(file_path, file_format)
    validation_record = FileValidationRecord(file, uuid)
    validation_record.original_etag = 'foobar'

    mock_response_get_local_file_path = mocker.Mock()
    mock_response_get_local_file_path.json.return_value = {
        '@graph': []
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_get_local_file_path)

    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result.validation_success == False
    assert result.uuid == '5b887ab3-65d3-4965-97bd-42bea7358431'
    assert result.info == {
        'file_size': 22585
    }
    assert result.errors == {
        'gzip': 'tsv file should be gzipped',
        'tabular_file_error': [[None, 1, 'incorrect-label', ''], [None, 2, 'incorrect-label', ''], [None, 3, 'incorrect-label', ''], [60, 24, 'type-error', "type is \"boolean/default\""], [61, 24, 'type-error', "type is \"boolean/default\""]]
    }


def test_main_tabular_csv(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/ENCFF194CFN.csv'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '57946a79da3f1651b21b1c84681abc51'
    file_format = 'csv'
    output_type = 'element quantifications'
    file_format_type = None
    assembly = None
    portal_auth = None

    file = get_file(file_path, file_format)
    validation_record = FileValidationRecord(file, uuid)
    validation_record.original_etag = 'foobar'

    mock_response_get_local_file_path = mocker.Mock()
    mock_response_get_local_file_path.json.return_value = {
        '@graph': []
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_get_local_file_path)

    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result.validation_success == False
    assert result.uuid == '5b887ab3-65d3-4965-97bd-42bea7358431'
    assert result.info == {
        'file_size': 13535
    }
    assert result.errors == {
        'gzip': 'csv file should be gzipped',
        'tabular_file_error': [[None, 4, 'missing-label', ''], [None, 5, 'missing-label', ''], [None, 6, 'missing-label', ''], [None, 7, 'missing-label', ''], [None, 8, 'missing-label', ''], [None, 9, 'missing-label', ''], [None, 10, 'missing-label', ''], [None, 11, 'missing-label', ''], [None, 12, 'missing-label', ''], [None, 13, 'missing-label', ''], ],
    }


def test_main_tabular_txt(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/ENCFF583VAI.txt.gz'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '6c86ca5de2569bf49287cb21196d760d'
    file_format = 'txt'
    output_type = 'element quantifications'
    file_format_type = None
    assembly = None
    portal_auth = None

    file = get_file(file_path, file_format)
    validation_record = FileValidationRecord(file, uuid)
    validation_record.original_etag = 'foobar'

    mock_response_get_local_file_path = mocker.Mock()
    mock_response_get_local_file_path.json.return_value = {
        '@graph': []
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_get_local_file_path)

    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result.validation_success == True
    assert result.uuid == '5b887ab3-65d3-4965-97bd-42bea7358431'
    assert result.info == {
        'file_size': 64,
        'content_md5sum': 'eda02672669cbbbdbb895cbb4ea2507f'
    }


def test_main_bed(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/ENCFF597JNC.bed.gz'
    key = '2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF597JNC.bed.gz'
    uuid = 'a3c64b51-5838-4ad2-a6c3-dc289786f626'
    md5sum = 'd1bae8af8fec54424cff157134652d26'
    file_format = 'bed'
    output_type = 'exclusion list regions'
    file_format_type = 'bed3'
    assembly = 'GRCh38'
    portal_auth = None

    file = get_file(file_path, file_format)
    validation_record = FileValidationRecord(file, uuid)
    validation_record.original_etag = 'foobar'

    mock_response_session = mocker.Mock()
    mock_response_session.json.return_value = {
        '@graph': [
            {
                'accession': 'ENCFF597JNC'
            }
        ]
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_session)
    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result.validation_success == False
    assert result.uuid == 'a3c64b51-5838-4ad2-a6c3-dc289786f626'
    assert result.info == {
        'content_md5sum': '16a792c57f2de7877b1a09e5bef7cb5c',
        'file_size': 5751
    }
    assert result.errors == {
        'content_md5sum_error': 'content md5sum 16a792c57f2de7877b1a09e5bef7cb5c conflicts with content md5sum of existing file(s): ENCFF597JNC'
    }


def test_upload_credentials_are_expired_expired(mocker):
    patched_current_time = mocker.patch(
        'checkfiles.checkfiles.get_current_utc_time')
    patched_current_time.return_value = datetime.datetime(
        2023, 5, 26, 20, 20, 0, 0, tzinfo=datetime.timezone.utc)
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        '@graph':
            [
                {
                    'upload_credentials':
                        {
                            'expiration': '2023-05-24T08:20:16+00:00'
                        }
                }
            ]
    }
    mocker.patch('checkfiles.checkfiles.requests.get',
                 return_value=mock_response)
    assert upload_credentials_are_expired(
        'uri_to_portal', 'file_uuid', PortalAuth('fake', 'creds')) == True


def test_upload_credentials_are_expired_not_expired(mocker):
    patched_current_time = mocker.patch(
        'checkfiles.checkfiles.get_current_utc_time')
    patched_current_time.return_value = datetime.datetime(
        2023, 5, 26, 20, 20, 0, 0, tzinfo=datetime.timezone.utc)
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        '@graph':
            [
                {
                    'upload_credentials':
                        {
                            'expiration': '2023-06-26T08:20:16+00:00'
                        }
                }
            ]
    }
    mocker.patch('checkfiles.checkfiles.requests.get',
                 return_value=mock_response)
    assert upload_credentials_are_expired(
        'uri_to_portal', 'file_uuid', PortalAuth('fake', 'creds')) == False


def test_make_content_md5sum_search_url():
    portal_url = 'https://api.data.igvf.org'
    content_md5sum = '123456'
    uuid = 'unique-id-123'
    search_url = make_content_md5sum_search_url(
        content_md5sum, uuid, portal_url)
    assert search_url == 'https://api.data.igvf.org/search/?type=File&format=json&status!=replaced&status!=deleted&uuid!=unique-id-123&content_md5sum=123456'
