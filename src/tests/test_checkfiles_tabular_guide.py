from frictionless import Resource
from checkfiles.checkfiles import tabular_file_check, file_validation
from checkfiles.file import FileValidationRecord
from checkfiles.file import get_file
from checkfiles.version import get_checkfiles_version
from checkfiles.guide_rna_sequences_check import GuideRnaSequencesCheck


def run_guide_check_on_rows(path, row_numbers):
    """
    Run GuideRnaSequencesCheck across the entire file but only collect
    ConstraintErrors for the specified 1-based row_numbers.
    Header is row 1, first data row is 2.
    Returns a list of (row_number, error) tuples.
    """
    resource = Resource(path, format='tsv')
    check = GuideRnaSequencesCheck()
    collected = []

    for row in resource.read_rows():
        row_errors = list(check.validate_row(row))
        if row.row_number in row_numbers:
            collected.extend((row.row_number, e) for e in row_errors)

    return collected


def test_main_tabular_tsv(mocker, freeze_checkfiles_time):
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
        'checkfiles_timestamp': freeze_checkfiles_time.isoformat(),
        'file_size': 472,
        'content_md5sum': '01018bd73d949934bbc015977d3cc40c'
    }
    errors = result.errors['tabular_file_error']
    assert errors['schema'] == 'src/schemas/table_schemas/guide_rna_sequences.json'
    assert errors['error_number_limit'] == 1000
    assert errors['number_of_errors'] == 108
    assert errors['constraint-error']['count'] == 58
    assert 'constraint-error' in errors['error_types']


def test_main_tabular_csv(mocker, freeze_checkfiles_time):
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
        'checkfiles_timestamp': freeze_checkfiles_time.isoformat(),
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


def test_guide_id_spacer_one_to_one():
    """
    New check:
      - guide_id <-> spacer must be one-to-one across the file.

    Row 3 reuses guide_id 'BASE_VALID' with a different spacer.
    Row 4 reuses spacer 'AAAAAAAAAAAAAAAAAAAA' with a different guide_id.
    Both should produce constraint errors with the 1-to-1 mapping message.
    """
    file_path = 'src/tests/data/guide_rna_sequences_targets_invalid.tsv'

    errors = run_guide_check_on_rows(file_path, row_numbers={3, 4})

    notes_row3 = [e.note for rn, e in errors if rn == 3]
    assert any(
        'guide_id BASE_VALID is associated with multiple spacers' in note
        and 'there must be a 1-to-1 mapping between guide_id and spacer' in note
        for note in notes_row3
    )

    notes_row4 = [e.note for rn, e in errors if rn == 4]
    assert any(
        'spacer AAAAAAAAAAAAAAAAAAAA is associated with multiple guide_ids' in note
        and 'there must be a 1-to-1 mapping between guide_id and spacer' in note
        for note in notes_row4
    )


def test_targeting_type_relationship():
    """
    New check:
      - non-targeting/safe-targeting/negative control -> targeting must be False
      - targeting/positive control/variant -> targeting must be True
    """
    file_path = 'src/tests/data/guide_rna_sequences_targets_invalid.tsv'

    errors = run_guide_check_on_rows(file_path, row_numbers={5, 6})

    # Row 5: type = non-targeting, targeting = TRUE
    notes_row5 = [e.note for rn, e in errors if rn == 5]
    assert any(
        'targeting must be False when type is non-targeting' in note
        for note in notes_row5
    )

    # Row 6: type = targeting, targeting = FALSE
    notes_row6 = [e.note for rn, e in errors if rn == 6]
    assert any(
        'targeting must be True when type is targeting' in note
        for note in notes_row6
    )


def test_positive_control_putative_target_genes():
    """
    New check:
      - For positive control guides with enhancer/insulator/silencer/distal element,
        putative_target_genes is required and must be ENSEMBL gene IDs.
    """
    file_path = 'src/tests/data/guide_rna_sequences_targets_invalid.tsv'

    errors = run_guide_check_on_rows(file_path, row_numbers={7, 8})

    # Row 7: positive control + enhancer with missing putative_target_genes
    notes_row7 = [e.note for rn, e in errors if rn == 7]
    assert any(
        'putative_target_genes is required when type is positive control '
        'and genomic_element is enhancer' in note
        for note in notes_row7
    )

    # Row 8: positive control + enhancer with invalid gene ID
    notes_row8 = [e.note for rn, e in errors if rn == 8]
    assert any(
        'putative_target_genes entries must be ENSEMBL gene IDs' in note
        and 'NOT_A_GENE_ID' in note
        for note in notes_row8
    )


def test_intended_target_name_formats():
    """
    intended_target_name format rules:
      - variant -> SPDI
      - promoter/gene/splice site -> ENSEMBL gene ID
      - enhancer/insulator/silencer/distal element -> genomic coordinates
      - exon -> ENSEMBL exon ID
      - intron -> genomic coordinates
    """
    file_path = 'src/tests/data/guide_rna_sequences_targets_invalid.tsv'

    variant_row = 9
    gene_row = 10
    enhancer_row = 11
    exon_row = 14
    intron_row = 15

    errors = run_guide_check_on_rows(
        file_path,
        row_numbers={variant_row, gene_row, enhancer_row, exon_row, intron_row},
    )

    notes = [e.note for _, e in errors]

    # Variant: SPDI requirement
    assert any(
        'intended_target_name must be a normalized SPDI identifier when '
        'genomic_element is variant' in note
        for note in notes
    )

    # Gene: ENSEMBL requirement
    assert any(
        'intended_target_name must be an ENSEMBL gene ID when '
        'genomic_element is promoter/gene/splice site' in note
        for note in notes
    )

    # Enhancer: coordinate requirement
    assert any(
        'intended_target_name must be genomic coordinates when '
        'genomic_element is an enhancer/insulator/silencer/'
        'distal element' in note
        for note in notes
    )

    notes_exon = [e.note for rn, e in errors if rn == exon_row]
    assert any(
        'intended_target_name must be an ENSEMBL exon ID when '
        'genomic_element is exon' in note
        for note in notes_exon
    )

    notes_intron = [e.note for rn, e in errors if rn == intron_row]
    assert any(
        'intended_target_name must be genomic coordinates when '
        'genomic_element is intron' in note
        for note in notes_intron
    )


def test_mouse_genes_valid_against_regex():
    """
    ENSEMBL regex:
      - ENSG########### (human) and ENSMUSG########### (mouse) are allowed.
    Row 13 has genomic_element = gene and intended_target_name = ENSMUSG...,
    which should pass the ENSEMBL_GENE_RE and not raise format errors.
    """
    file_path = 'src/tests/data/guide_rna_sequences_targets_invalid.tsv'

    errors = run_guide_check_on_rows(file_path, row_numbers={13})

    # Row 13 should not produce any ConstraintErrors at all
    assert errors == []


def test_exon_and_intron_intended_target_names_valid():
    """
    Valid exon and intron identifiers should not raise format errors:
      - human ENSE and mouse ENSMUSE exon IDs
      - intron coordinates
    """
    file_path = 'src/tests/data/guide_rna_sequences_targets_invalid.tsv'

    errors = run_guide_check_on_rows(file_path, row_numbers={16, 17, 18})

    assert errors == []


def test_prime_editing_spacer_reuse_across_designs():
    """
    Prime editing guide designs are defined by spacer + PBS + RT template.
    The same spacer may be reused when PBS and/or RT template differ.
    """
    file_path = 'src/tests/data/prime_editing_guide_rna_sequences_designs_invalid.tsv'

    errors = run_guide_check_on_rows(file_path, row_numbers={2, 3})

    assert errors == []


def test_prime_editing_guide_design_uniqueness():
    """
    Prime editing uniqueness:
      - the same (spacer, PBS, RT) design may not map to multiple guide_ids
      - the same guide_id may not map to multiple designs
    """
    file_path = 'src/tests/data/prime_editing_guide_rna_sequences_designs_invalid.tsv'

    errors = run_guide_check_on_rows(file_path, row_numbers={4, 5})

    notes_row4 = [e.note for rn, e in errors if rn == 4]
    assert any(
        'guide design' in note
        and 'is associated with multiple guide_ids' in note
        and 'the same spacer may only be reused when' in note
        for note in notes_row4
    )

    notes_row5 = [e.note for rn, e in errors if rn == 5]
    assert any(
        'guide_id PE_BASE is associated with multiple guide designs' in note
        and 'each guide_id must be associated with a single guide design' in note
        for note in notes_row5
    )
