from checkfiles.checkfiles import tabular_file_check, file_validation
from checkfiles.file import FileValidationRecord
from checkfiles.file import get_file
from checkfiles.version import get_checkfiles_version


def test_main_tabular_tsv(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/guide_rna_sequences_invalid.tsv.gz'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '01018bd73d949934bbc015977d3cc40c'
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
        'file_size': 472,
        'content_md5sum': '01018bd73d949934bbc015977d3cc40c'
    }
    errors = result.errors['tabular_file_error']
    assert errors['schema'] == 'src/schemas/table_schemas/guide_rna_sequences.json'
    assert errors['error_number_limit'] == 1000
    assert errors['number_of_errors'] == 108
    assert errors['constraint-error']['count'] == 58
    assert 'constraint-error' in errors['error_types']


def test_main_tabular_csv(mocker):
    portal_url = 'url_to_portal'
    file_path = 'src/tests/data/guide_rna_sequences_invalid.csv.gz'
    uuid = '5b887ab3-65d3-4965-97bd-42bea7358431'
    md5sum = '519b8b076b19efa149045bd8abd4c8f3'
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
        'file_size': 1537,
        'content_md5sum': '519b8b076b19efa149045bd8abd4c8f3'
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
            {'row_number': 2, 'field_number': 4, 'note': 'constraint "enum" is "[\'targeting\', \'safe-targeting\', \'non-targeting\', \'positive control\', \'negative control\', \'variant\']"'}]
    }
    assert 'constraint-error' in errors['error_types']


def test_tabular_file_check_guide_rna_sequences_valid():
    file_path = 'src/tests/data/guide_rna_sequences_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'guide RNA sequences', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_guide_rna_sequences_invalid():
    file_path = 'src/tests/data/guide_rna_sequences_invalid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'guide RNA sequences', file_path, is_gzipped)
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
                                                                  {'row_number': 2, 'field_number': 4, 'note': 'constraint "enum" is "[\'targeting\', \'safe-targeting\', \'non-targeting\', \'positive control\', \'negative control\', \'variant\']"'}]}
    assert 'constraint-error' in tabular_file_error['error_types']


def test_tabular_file_check_guide_rna_sequences_custom_check():
    file_path = 'src/tests/data/guide_rna_sequences_custom_check.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'guide RNA sequences', file_path, is_gzipped)
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
                                                                   'is not False',
                                                                   'row_number': 33}]}
    assert 'constraint-error' in tabular_file_error['error_types']


def test_tabular_file_check_prime_editing_guide_rna_sequences_valid():
    file_path = 'src/tests/data/prime_editing_guide_rna_sequences_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'prime editing guide RNA sequences', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_prime_editing_guide_rna_sequences_invalid():
    file_path = 'src/tests/data/prime_editing_guide_rna_sequences_invalid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'prime editing guide RNA sequences', file_path, is_gzipped)
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


def test_tabular_file_check_extra_fields_valid():
    file_path = 'src/tests/data/guide_rna_sequences_extra_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'guide RNA sequences', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_extra_fields_invalid():
    file_path = 'src/tests/data/guide_rna_sequences_extra_invalid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'guide RNA sequences', file_path, is_gzipped)
    tabular_file_error = error['tabular_file_error']
    assert tabular_file_error['number_of_errors'] == 1
    assert 'constraint-error' in tabular_file_error['error_types']


def test_tabular_file_check_valid_grna_sequences_with_comment():
    file_path = 'src/tests/data/valid_grna_sequences_with_comment.tsv.gz'
    is_gzipped = True
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'guide RNA sequences', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_invalid_grna_sequences_with_comment():
    file_path = 'src/tests/data/invalid_grna_sequences_with_comment.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'guide RNA sequences', file_path, is_gzipped)
    tabular_file_error = error['tabular_file_error']
    assert tabular_file_error['number_of_errors'] == 1
    assert 'incorrect-label' in tabular_file_error['error_types']


def test_tabular_file_check_txt_filename():
    file_path = 'src/tests/data/guide_rna_sequences_invalid.txt.gz'
    is_gzipped = True
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'guide RNA sequences', file_path, is_gzipped)
    tabular_file_error = error['tabular_file_error']
    assert tabular_file_error['number_of_errors'] == 1
    assert 'incorrect-label' in tabular_file_error['error_types']
