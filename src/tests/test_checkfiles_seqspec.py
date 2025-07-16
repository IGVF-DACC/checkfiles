from checkfiles.checkfiles import seqspec_file_check


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


def test_seqspec_file_check_invalid_read_id():
    file_path = 'src/tests/data/seqspec_invalid_read_id.yaml.gz'
    error = seqspec_file_check(file_path)
    seqspec_error = error['seqspec_error']
    assert seqspec_error == [
        {'error_type': 'check_schema',
            'error_message': "'FI1165AJSO' does not match '^IGVF.*' in spec['sequence_spec'][0]['read_id']", 'error_object': "'read_id'"}
    ]
