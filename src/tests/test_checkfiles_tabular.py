from checkfiles.checkfiles import tabular_file_check, file_validation
from checkfiles.file import FileValidationRecord
from checkfiles.file import get_file
from checkfiles.version import get_checkfiles_version


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


def test_tabular_file_check_mpra_sequence_designs_valid():
    is_gzipped = False
    file_path = 'src/tests/data/mpra_sequence_designs_valid.tsv'
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'MPRA sequence designs', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_mpra_sequence_designs_invalid():
    file_path = 'src/tests/data/mpra_sequence_designs_invalid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'MPRA sequence designs', file_path, is_gzipped)
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


def test_tabular_file_check_fragments_valid():
    file_path = 'src/tests/data/fragments_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(file_format, 'fragments', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_reporter_experiment_valid():
    file_path = 'src/tests/data/reporter_experiment_valid.tsv.gz'
    is_gzipped = True
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'reporter experiment', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_reporter_elements_valid():
    file_path = 'src/tests/data/reporter_elements_valid.tsv.gz'
    is_gzipped = True
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'reporter elements', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_reporter_variants_valid():
    file_path = 'src/tests/data/reporter_variants_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'reporter variants', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_barcode_to_sample_mapping_valid():
    file_path = 'src/tests/data/barcode_to_sample_mapping_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'barcode to sample mapping', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_barcode_to_sample_mapping_invalid():
    file_path = 'src/tests/data/barcode_to_sample_mapping_invalid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'barcode to sample mapping', file_path, is_gzipped)
    assert error['tabular_file_error']['number_of_errors'] == 2
    assert 'constraint-error' in error['tabular_file_error']['error_types']
    assert error['tabular_file_error']['constraint-error']['count'] == 2


def test_tabular_file_check_barcode_to_sample_mapping_three_columns_valid():
    file_path = 'src/tests/data/barcode_to_sample_mapping_three_columns_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'barcode to sample mapping', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_barcode_to_sample_mapping_four_columns_invalid():
    file_path = 'src/tests/data/barcode_to_sample_mapping_four_columns_invalid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'barcode to sample mapping', file_path, is_gzipped)
    assert error['tabular_file_error'] == 'barcode to sample mapping file should have 6 or 3 columns, but found 4 columns'


def test_tabular_file_check_caqtl_valid():
    file_path = 'src/tests/data/caqtl_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(file_format, 'caQTL', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_element_to_gene_interactions_valid():
    file_path = 'src/tests/data/element_to_gene_interactions_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'element to gene interactions', file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_element_to_gene_interactions_invalid():
    file_path = 'src/tests/data/element_to_gene_interactions_invalid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'element to gene interactions', file_path, is_gzipped)
    assert error['tabular_file_error']['number_of_errors'] == 1
    assert 'constraint-error' in error['tabular_file_error']['error_types']


def test_tabular_file_check_gene_universe_valid():
    file_path = 'src/tests/data/gene_universe_valid.csv'
    is_gzipped = False
    file_format = 'csv'
    content_type = 'gene universe'
    error = tabular_file_check(
        file_format, content_type, file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_gene_programs_valid():
    file_path = 'src/tests/data/gene_programs_valid.csv'
    is_gzipped = False
    file_format = 'csv'
    content_type = 'gene programs'
    error = tabular_file_check(
        file_format, content_type, file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_gene_program_regulators_valid():
    file_path = 'src/tests/data/gene_program_regulators_valid.csv'
    is_gzipped = False
    file_format = 'csv'
    content_type = 'gene program regulators'
    error = tabular_file_check(
        file_format, content_type, file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_cell_annotations_valid():
    file_path = 'src/tests/data/cell_annotations_valid.csv'
    is_gzipped = False
    file_format = 'csv'
    content_type = 'cell annotations'
    error = tabular_file_check(
        file_format, content_type, file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_marker_genes_valid():
    file_path = 'src/tests/data/marker_genes_valid.tsv'
    is_gzipped = False
    file_format = 'tsv'
    content_type = 'marker genes'
    error = tabular_file_check(
        file_format, content_type, file_path, is_gzipped)
    assert error == {}


def test_tabular_file_check_encoding_invalid():
    """tabular_file_check rejects non-UTF-8 encodings and returns tabular_file_error."""
    file_path = 'src/tests/data/tabular_file_encoding.tsv'
    is_gzipped = False
    file_format = 'tsv'
    error = tabular_file_check(
        file_format, 'guide RNA sequences', file_path, is_gzipped)
    assert 'tabular_file_error' in error
    assert error['tabular_file_error'] == "exception occurred when checking tabular file: 'utf-8' codec can't decode byte 0xca in position 196: invalid continuation byte"
