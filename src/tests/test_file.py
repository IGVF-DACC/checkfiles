import pytest

from checkfiles.file import File
from checkfiles.file import FileValidationRecord


def get_gzipped_file():
    return File('src/tests/data/ENCFF594AYI.fastq.gz', 'fastq')


def get_non_gzipped_file():
    return File('src/tests/data/ENCFF080HPN.tsv', 'tsv')


def test_is_zipped():
    fastq = get_gzipped_file()
    assert fastq.is_zipped


def test_is_not_zipped():
    tsv = get_non_gzipped_file()
    assert not tsv.is_zipped


def test_content_md5_on_non_zipped_raises_error():
    tsv = get_non_gzipped_file()
    with pytest.raises(TypeError):
        tsv.content_md5sum


def test_md5sum():
    fastq = get_gzipped_file()
    assert fastq.md5sum == '3e814f4af7a4c13460584b26fbe32dc4'


def test_content_md5sum():
    fastq = get_gzipped_file()
    assert fastq.content_md5sum == '1fa9f74aa895c4c938e1712bedf044ec'


def test_update_errors():
    file = get_gzipped_file()
    record = FileValidationRecord(file, uuid='abc')
    assert record.errors == {}
    error = {'validationerror': 'validation failed'}
    record.update_errors(error)
    assert 'validationerror' in record.errors
