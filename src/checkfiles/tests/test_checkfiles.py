from checkfiles.checkfiles import check_valid_gzipped_file_format, fasta_check
from checkfiles.checkfiles import check_md5sum, check_content_md5sum, bam_pysam_check, fastq_get_average_read_length_and_number_of_reads, file_validation
from checkfiles.checkfiles import get_chrom_info_file, get_validate_files_args, validate_files_check, validate_files_fastq_check
from checkfiles.checkfiles import PortalAuth
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
        'fastq_number_of_reads': 25,
        'fastq_read_length': 58
    }


def test_get_chrom_info_file_human():
    file = get_chrom_info_file('GRCh38')
    assert file == 'src/schemas/genome_builds/human/GRCh38/chrom.sizes'


def test_get_chrom_info_file_rodent():
    file = get_chrom_info_file('GRCm39')
    assert file == 'src/schemas/genome_builds/rodent/GRCm39/chrom.sizes'


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


def test_main_fastq():
    portal_url = 'https://www.encodeproject.org'
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
    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result == {
        'uuid': 'a3b754b6-0213-4ed4-a5f3-124f90273561',
        'validation_result': 'failed',
        'info': {
            'calculated_md5sum': '3e814f4af7a4c13460584b26fbe32dc4',
            'content_md5sum': '1fa9f74aa895c4c938e1712bedf044ec',
            'file_size': 1371,
            'fastq_number_of_reads': 25,
            'fastq_read_length': 58
        },
        'errors': {'content_md5sum_error': 'content md5sum 1fa9f74aa895c4c938e1712bedf044ec conflicts with content md5sum of existing file(s): ENCFF594AYI'}
    }


def test_main_bam(mocker):
    portal_url = 'https://www.encodeproject.org'
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

    mock_response_session = mocker.Mock()
    mock_response_session.json.return_value = {
        '@graph': []
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_session)

    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result == {
        'uuid': '5b887ab3-65d3-4965-97bd-42bea7358431',
        'info': {
            'calculated_md5sum': '2d3b7df013d257c7052c084d93ff9026',
            'content_md5sum': '9095bad36672afefd7bf9165d89b4eb5',
            'file_size': 118126,
            'bam_number_of_reads': 1709
        },
        'validation_result': 'pass'
    }


def test_main_tabular(mocker):
    portal_url = 'https//www.encodeproject.org'
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

    mock_response_get_local_file_path = mocker.Mock()
    mock_response_get_local_file_path.json.return_value = {
        '@graph': []
    }
    mocker.patch('checkfiles.checkfiles.requests.Session.get',
                 return_value=mock_response_get_local_file_path)

    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result == {
        'uuid': '5b887ab3-65d3-4965-97bd-42bea7358431',
        'validation_result': 'failed',
        'info': {
            'calculated_md5sum': '4b0b3c68fafc5a26d0fc6150baadaa5b',
            'file_size': 22585},
        'errors': {
            'gzip': 'tsv file should be gzipped',
            'tabular_file_error': [[None, 1, 'incorrect-label', ''], [None, 2, 'incorrect-label', ''], [None, 3, 'incorrect-label', ''], [60, 24, 'type-error', "type is \"boolean/default\""], [61, 24, 'type-error', "type is \"boolean/default\""]]
        }
    }


def test_main_bed(mocker):
    portal_url = 'https://www.encodeproject.org'
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

    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly)
    assert result == {
        'uuid': 'a3c64b51-5838-4ad2-a6c3-dc289786f626',
        'validation_result': 'failed',
        'info': {
            'calculated_md5sum': 'd1bae8af8fec54424cff157134652d26',
            'content_md5sum': '16a792c57f2de7877b1a09e5bef7cb5c',
            'file_size': 5751
        },
        'errors': {'content_md5sum_error': 'content md5sum 16a792c57f2de7877b1a09e5bef7cb5c conflicts with content md5sum of existing file(s): ENCFF597JNC'}
    }
