import datetime
import gzip
from io import BytesIO

from checkfiles.checkfiles import check_valid_gzipped_file_format, fasta_check, get_reference_file_path, vcf_sequence_check, seqspec_file_check, cram_pysam_check
from checkfiles.checkfiles import make_content_md5sum_search_url, bam_pysam_check, fastq_get_average_read_length_and_number_of_reads, file_validation
from checkfiles.checkfiles import get_validate_files_args, validate_files_check, validate_files_fastq_check, tabular_file_check
from checkfiles.checkfiles import PortalAuth
from checkfiles.checkfiles import upload_credentials_are_expired
from checkfiles.file import FileValidationRecord
from checkfiles.file import get_file
from checkfiles.version import get_checkfiles_version


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

def test_get_reference_file_path(mocker):
   
    reference_file = '/reference-files/TSTFI36924773/'
    portal_auth = None
    fasta_content = '>chr1\nACTG\n'
    gzipped_data = BytesIO()
    with gzip.GzipFile(fileobj=gzipped_data, mode='wb') as f:
        f.write(fasta_content.encode('utf-8'))
    gzipped_data.seek(0)
    # Mock requests.Session and .get()
    mock_session = mocker.Mock()
    mock_session.get.return_value.status_code = 200
    mock_session.get.return_value.content = gzipped_data.read()
    mocker.patch('checkfiles.checkfiles.requests.Session', return_value=mock_session)


    reference_file_path = get_reference_file_path(reference_file, portal_auth)
    assert reference_file_path == 'src/checkfiles/supporting_files/TSTFI36924773.fasta'
    
def test_cram_pysam_check_cram_valid(mocker):
    file_path = 'src/tests/data/cram_valid.cram'
    reference_file_path = 'mock_reference.fasta'

    # Mock the first Popen (samtools view)
    mock_p1 = mocker.MagicMock()
    mock_p1.__enter__.return_value.communicate.return_value = ("", "")
    mock_p1.__enter__.return_value.stdout = mocker.MagicMock()
    mock_p1.__enter__.return_value.stdout.close = mocker.Mock()

    # Mock the second Popen (samtools stats)
    mock_p2 = mocker.MagicMock()
    mock_p2.__enter__.return_value.communicate.return_value = ("SN\tis sorted:\t1", "")

    # Patch subprocess.Popen to return mock_p1 then mock_p2
    mocker.patch('checkfiles.checkfiles.subprocess.Popen', side_effect=[mock_p1, mock_p2])

    # Mock AlignmentFile and count
    mock_cram = mocker.Mock()
    mock_cram.count.return_value = 36142
    mock_alignment_file = mocker.patch('checkfiles.checkfiles.pysam.AlignmentFile')
    mock_alignment_file.return_value.__enter__.return_value = mock_cram

    result = cram_pysam_check(file_path, reference_file_path)

    assert result == {'read_count': 36142}
    


def test_bam_pysam_check_number_of_read():
    file_path = 'src/tests/data/ENCFF206HGF.bam'
    result = bam_pysam_check(file_path)
    assert result == {'read_count': 1709}


def test_fastq_get_average_read_length_and_number_of_reads():
    file_path = 'src/tests/data/ENCFF594AYI.fastq.gz'
    result = fastq_get_average_read_length_and_number_of_reads(file_path)
    assert result == {
        'read_count': 25,
        'mean_read_length': 58.0,
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
    is_gzipped = False
    error = tabular_file_check('guide RNA sequences', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_guide_rna_sequences_invalid():
    file_path = 'src/tests/data/guide_rna_sequences_invalid.tsv'
    is_gzipped = False
    error = tabular_file_check('guide RNA sequences', file_path, is_gzipped)
    tabular_file_error = error['tabular_file_error']
    assert tabular_file_error['schema'] == 'src/schemas/table_schemas/guide_rna_sequences.json'
    assert tabular_file_error['error_number_limit'] == 1000
    assert tabular_file_error['number_of_errors'] == 2
    assert tabular_file_error['constraint-error'] == {'count': 2,
                                                      'description': 'A field value '
                                                      'does not conform '
                                                      'to a constraint.',
                                                      'details': [{'field_number': 1,
                                                                   'note': 'constraint '
                                                                   '"required" '
                                                                   'is "True"',
                                                                   'row_number': 2},
                                                                  {'field_number': 4,
                                                                   'note': 'constraint '
                                                                   '"enum" is '
                                                                   '"[\'safe-targeting\', '
                                                                   "'non-targeting', "
                                                                   "'targeting', "
                                                                   "'positive "
                                                                   "control', "
                                                                   "'negative "
                                                                   "control', "
                                                                   '\'variant\']"',
                                                                   'row_number': 2}]}
    assert 'constraint-error' in tabular_file_error['error_types']


def test_tabular_file_check_guide_rna_sequences_custom_check():
    file_path = 'src/tests/data/guide_rna_sequences_custom_check.tsv'
    is_gzipped = False
    error = tabular_file_check('guide RNA sequences', file_path, is_gzipped)
    tabular_file_error = error['tabular_file_error']
    assert tabular_file_error['schema'] == 'src/schemas/table_schemas/guide_rna_sequences.json'
    assert tabular_file_error['error_number_limit'] == 1000
    assert tabular_file_error['number_of_errors'] == 1
    assert tabular_file_error['constraint-error'] == {'count': 1,
                                                      'description': 'A field value '
                                                      'does not conform '
                                                      'to a constraint.',
                                                      'details': [{'field_number': 5,
                                                                   'note': 'guide_chr '
                                                                   'is required '
                                                                   'when '
                                                                   'targeting '
                                                                   'is True',
                                                                   'row_number': 33}]}
    assert 'constraint-error' in tabular_file_error['error_types']


def test_tabular_file_check_mpra_sequence_designs_valid():
    is_gzipped = False
    file_path = 'src/tests/data/mpra_sequence_designs_valid.tsv'
    error = tabular_file_check('MPRA sequence designs', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_mpra_sequence_designs_invalid():
    file_path = 'src/tests/data/mpra_sequence_designs_invalid.tsv'
    is_gzipped = False
    error = tabular_file_check('MPRA sequence designs', file_path, is_gzipped)
    tabular_file_error = error['tabular_file_error']
    assert tabular_file_error['schema'] == 'src/schemas/table_schemas/mpra_sequence_designs.json'
    assert tabular_file_error['error_number_limit'] == 1000
    assert tabular_file_error['number_of_errors'] == 10
    assert tabular_file_error['constraint-error'] == {
        'count': 10,
        'description': 'A field value does not conform to a constraint.',
        'details': [
            {'row_number': 6, 'field_number': 1,
                'note': 'constraint "required" is "True"'},
            {'row_number': 6, 'field_number': 2,
                'note': 'constraint "required" is "True"'}
        ]
    }
    assert 'constraint-error' in tabular_file_error['error_types']


def test_tabular_file_check_prime_editing_guide_rna_sequences_valid():
    file_path = 'src/tests/data/prime_editing_guide_rna_sequences_valid.tsv'
    is_gzipped = False
    error = tabular_file_check(
        'prime editing guide RNA sequences', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_prime_editing_guide_rna_sequences_invalid():
    file_path = 'src/tests/data/prime_editing_guide_rna_sequences_invalid.tsv'
    is_gzipped = False
    error = tabular_file_check(
        'prime editing guide RNA sequences', file_path, is_gzipped)
    tabular_file_error = error['tabular_file_error']
    assert tabular_file_error['schema'] == 'src/schemas/table_schemas/prime_editing_guide_rna_sequences.json'
    assert tabular_file_error['error_number_limit'] == 1000
    assert tabular_file_error['number_of_errors'] == 2
    assert tabular_file_error['constraint-error'] == {
        'count': 2,
        'description': 'A field value does not conform to a constraint.',
        'details': [
            {'row_number': 2, 'field_number': 13,
                'note': 'constraint "required" is "True"'},
            {'row_number': 3, 'field_number': 10,
                'note': 'constraint "required" is "True"'}
        ]
    }
    assert 'constraint-error' in tabular_file_error['error_types']


def test_seqspec_file_check_valid():
    file_path = 'src/tests/data/seqspec_valid.yaml.gz'
    error = seqspec_file_check(file_path)
    assert error == {}


def test_seqspec_file_check_valid_for_igvf():
    file_path = 'src/tests/data/seqspec_valid_for_igvf.yaml.gz'
    error = seqspec_file_check(file_path)
    assert error == {}


def test_seqspec_file_check_invalid():
    file_path = 'src/tests/data/seqspec_invalid.yaml.gz'
    error = seqspec_file_check(file_path)
    assert error == {
        'seqspec_error':  [{'error_message': "'atac-illumina_p5' sequence 'AATGATACGGCGACCACCGAGATCTACAC' has length 29, expected range (30, 30)", 'error_object': 'region', 'error_type': 'check_sequence_lengths'}]} != {'seqspec_error': ["[error 1] 'atac-illumina_p5' sequence 'AATGATACGGCGACCACCGAGATCTACAC' has length 29, expected range (30, 30)"]
                                                                                                                                                                                                                           }


def test_seqspec_file_check_skip_onlist_valid():
    file_path = 'src/tests/data/seqspec_valid_ignore_onlist.yaml.gz'
    error = seqspec_file_check(file_path, validate_onlist_files=False)
    assert error == {}


def test_seqspec_file_check_onlist_invalid():
    file_path = 'src/tests/data/seqspec_valid_ignore_onlist.yaml.gz'
    error = seqspec_file_check(file_path)
    assert error == {
        'seqspec_error': [{'error_message': 'IGVFFI7587TJLC.tsv.gz does not exist',
                           'error_object': 'onlist',
                           'error_type': 'check_onlist_files_exist'}]
    }


def test_seqpec_file_check_old_version():
    file_path = 'src/tests/data/seqspec_old_version.yaml.gz'
    error = seqspec_file_check(file_path)
    assert error == {
        'seqspec_error': 'The seqspec file version is 0.2.0, while version 0.3.0 is required.'
    }


def test_tabular_file_check_extra_fields_valid():
    file_path = 'src/tests/data/guide_rna_sequences_extra_valid.tsv'
    is_gzipped = False
    error = tabular_file_check('guide RNA sequences', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_extra_fields_invalid():
    file_path = 'src/tests/data/guide_rna_sequences_extra_invalid.tsv'
    is_gzipped = False
    error = tabular_file_check('guide RNA sequences', file_path, is_gzipped)
    tabular_file_error = error['tabular_file_error']
    assert tabular_file_error['number_of_errors'] == 1
    assert 'constraint-error' in tabular_file_error['error_types']


def test_tabular_file_check_fragments_valid():
    file_path = 'src/tests/data/fragments_valid.tsv'
    is_gzipped = False
    error = tabular_file_check('fragments', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_valid_grna_sequences_with_comment():
    file_path = 'src/tests/data/valid_grna_sequences_with_comment.tsv.gz'
    is_gzipped = True
    error = tabular_file_check('guide RNA sequences', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_invalid_grna_sequences_with_comment():
    file_path = 'src/tests/data/invalid_grna_sequences_with_comment.tsv'
    is_gzipped = False
    error = tabular_file_check('guide RNA sequences', file_path, is_gzipped)
    tabular_file_error = error['tabular_file_error']
    assert tabular_file_error['number_of_errors'] == 1
    assert 'incorrect-label' in tabular_file_error['error_types']


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
    reference_files = None

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
                             md5sum, output_type, file_format_type, assembly, reference_files)
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
    reference_files = None

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
                             md5sum, output_type, file_format_type, assembly, reference_files)

    assert result.validation_success == False
    assert result.original_etag == 'foobar'
    assert result.info == {
        'checkfiles_version': get_checkfiles_version(),
        'content_md5sum': '1fa9f74aa895c4c938e1712bedf044ec',
        'file_size': 1371,
        'read_count': 25,
        'mean_read_length': 58.0,
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
    reference_files = None

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
                             md5sum, output_type, file_format_type, assembly, reference_files)
    assert result.validation_success == True
    assert result.info == {
        'checkfiles_version': get_checkfiles_version(),
        'content_md5sum': '9095bad36672afefd7bf9165d89b4eb5',
        'file_size': 118126,
        'read_count': 1709
    }


def test_main_crai_uncompressed():
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/uncompressed.crai'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '154e39d90e082c5a9d0946ce581fb2f3'
    file_format = 'crai'
    output_type = None
    file_format_type = None
    assembly = None
    portal_auth = None
    reference_files = None
    file = get_file(file_path, file_format)
    validation_record = FileValidationRecord(file, uuid)
    validation_record.original_etag = 'foobar'

    result = file_validation(portal_url, portal_auth, validation_record,
                             md5sum, output_type, file_format_type, assembly, reference_files)
    assert result.validation_success == True
    assert result.info == {
        'checkfiles_version': get_checkfiles_version(),
        'file_size': 282843,
    }


def test_main_crai_gzipped(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/gzipped.crai'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '0bcf7eefc757d75a50d3e3dbf06c7a27'
    file_format = 'crai'
    output_type = None
    file_format_type = None
    assembly = None
    portal_auth = None
    reference_files = None

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
                             md5sum, output_type, file_format_type, assembly, reference_files)
    assert result.validation_success == True
    assert result.info == {
        'checkfiles_version': get_checkfiles_version(),
        'file_size': 129671,
        'content_md5sum': '154e39d90e082c5a9d0946ce581fb2f3'
    }


def test_main_tabular_tsv(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/guide_rna_sequences_invalid.tsv'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '4b0b3c68fafc5a26d0fc6150baadaa5b'
    file_format = 'tsv'
    output_type = 'guide RNA sequences'
    file_format_type = None
    assembly = None
    portal_auth = None
    reference_files = None

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
                             md5sum, output_type, file_format_type, assembly, reference_files)
    assert result.validation_success == False
    assert result.uuid == '5b887ab3-65d3-4965-97bd-42bea7358431'
    assert result.info == {
        'checkfiles_version': get_checkfiles_version(),
        'file_size': 4517
    }
    errors = result.errors['tabular_file_error']
    assert errors['schema'] == 'src/schemas/table_schemas/guide_rna_sequences.json'
    assert errors['error_number_limit'] == 1000
    assert errors['number_of_errors'] == 2
    assert errors['constraint-error'] == {
        'count': 2,
        'description': 'A field value does not conform to a constraint.',
        'details': [
            {'row_number': 2, 'field_number': 1,
                'note': 'constraint "required" is "True"'},
            {'row_number': 2, 'field_number': 4, 'note': 'constraint "enum" is "[\'safe-targeting\', \'non-targeting\', \'targeting\', \'positive control\', \'negative control\', \'variant\']"'}]
    }
    assert 'constraint-error' in errors['error_types']


def test_main_tabular_csv(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/guide_rna_sequences_invalid.csv'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '23d15f36b2d8d5f70f3632c086173f46'
    file_format = 'csv'
    output_type = 'guide RNA sequences'
    file_format_type = None
    assembly = None
    portal_auth = None
    reference_files = None

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
                             md5sum, output_type, file_format_type, assembly, reference_files)
    assert result.validation_success == False
    assert result.uuid == '5b887ab3-65d3-4965-97bd-42bea7358431'
    assert result.info == {
        'checkfiles_version': get_checkfiles_version(),
        'file_size': 4556
    }
    errors = result.errors['tabular_file_error']
    assert errors['schema'] == 'src/schemas/table_schemas/guide_rna_sequences.json'
    assert errors['error_number_limit'] == 1000
    assert errors['number_of_errors'] == 2
    assert errors['constraint-error'] == {
        'count': 2,
        'description': 'A field value does not conform to a constraint.',
        'details': [
            {'row_number': 2, 'field_number': 1,
                'note': 'constraint "required" is "True"'},
            {'row_number': 2, 'field_number': 4, 'note': 'constraint "enum" is "[\'safe-targeting\', \'non-targeting\', \'targeting\', \'positive control\', \'negative control\', \'variant\']"'}]
    }
    assert 'constraint-error' in errors['error_types']


def test_main_tabular_skip_type_error(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/skip_error_test_file.csv'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '5ff9fc3dbbd206cf4abb8164015c67e5'
    file_format = 'csv'
    output_type = 'test'
    file_format_type = None
    assembly = None
    portal_auth = None
    reference_files = None

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
                             md5sum, output_type, file_format_type, assembly, reference_files)
    assert result.validation_success == False
    assert result.uuid == '5b887ab3-65d3-4965-97bd-42bea7358431'
    assert result.errors == {'gzip': 'csv file should be gzipped'}


def test_main_vcf_sequence_check_valid(mocker):
    mocker.patch('checkfiles.checkfiles.ASSEMBLY_TO_SEQUENCE_FILE_MAP', {
        'GRCh38': 'src/tests/data/chrY_sample.fa',
        'GRCm39': 'src/checkfiles/supporting_files/grcm39.fa',
    })
    file_path = 'src/tests/data/chry_variants_sample_valid.vcf.gz'
    assembly = 'GRCh38'
    error = vcf_sequence_check(file_path, assembly)
    assert error == {}


def test_main_vcf_sequence_check_invalid(mocker):
    mocker.patch('checkfiles.checkfiles.ASSEMBLY_TO_SEQUENCE_FILE_MAP', {
        'GRCh38': 'src/tests/data/chrY_sample.fa',
        'GRCm39': 'src/checkfiles/supporting_files/grcm39.fa',
    })
    file_path = 'src/tests/data/chry_variants_sample_invalid.vcf'
    assembly = 'GRCh38'
    error = vcf_sequence_check(file_path, assembly)
    assert error == {
        'vcf_error': '[info] Reading from input VCF file...\n'
        '[info] Reading from input FASTA file...\n'
        '[info] Reading from input FASTA index file...\n'
        '[info] Number of matches: 9/10\n'
        '[info] Percentage of matches: 90%'
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
    reference_files = None

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
                             md5sum, output_type, file_format_type, assembly, reference_files)
    assert result.validation_success == False
    assert result.uuid == 'a3c64b51-5838-4ad2-a6c3-dc289786f626'
    assert result.info == {
        'checkfiles_version': get_checkfiles_version(),
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
