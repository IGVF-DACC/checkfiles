import argparse
import gzip
import hashlib
import json
import logging
import os
import requests
import shutil
import subprocess
import sys
import tempfile
import traceback

import pyfastx
import pysam

from FastaValidator import fasta_validator

from frictionless import system
from frictionless import validate


KEY = os.getenv('KEY')
MD5SUM = os.getenv('MD5SUM')
FILE_FORMAT = os.getenv('FILE_FORMAT')
FILE_FORMAT_TYPE = os.getenv('FILE_FORMAT_TYPE')
OUTPUT_TYPE = os.getenv('OUTPUT_TYPE')
UUID = os.getenv('UUID')
FILE_SIZE = int(os.getenv('FILE_SIZE', 0))
ASSEMBLY = os.getenv('ASSEMBLY')
NUMBER_OF_READS = int(os.getenv('NUMBER_OF_READS', 0))
READ_LENGTH = int(os.getenv('READ_LENGTH', 0))
ENCODE_ACCESS_KEY = os.getenv('ENCODE_ACCESS_KEY', '')
ENCODE_SECRET_KEY = os.getenv('ENCODE_SECRET_KEY', '')
DATA_DIR = '/s3/'
CONTENT_MD5SUM_URL = 'https://www.encodeproject.org/search/?type=File&format=json&content_md5sum='

SCHEMA_DIR = 'src/schemas/'
CHROM_INFO_DIR = SCHEMA_DIR + 'genome_builds'
CHUNK_SIZE = 128*6400
MAX_NUM_ERROR_FOR_TABULAR_FILE = 10

ZIP_FILE_FORMAT = [
    'bam',
    'fastq',
    'txt',
    'tsv',
    'bed',
    'bedpe',
    'fasta',
]

TABULAR_FORMAT = [
    'txt',
    'tsv',
]

TABULAR_FILE_SCHEMAS = {
    'element quantifications': 'src/schemas/table_schemas/element_quant.json'
}

VALIDATE_FILES_ARGS = {
    ('bed', 'bed3'): ['-type=bed3'],
    ('bed', 'CRISPR element quantifications'): ['-type=bed3+22', '-as=src/schemas/file_formats/as/element_quant_format.as'],
    ('bed', 'bed3+'): ['-tab', '-type=bed3+'],
    ('bed', 'bedGraph'): ['-type=bedGraph'],
    ('bedpe', None): ['-type=bed3+'],
    ('bigBed', 'bed3'): ['-type=bigBed3'],
    ('bigBed', 'bed3+'): ['-tab', '-type=bigBed3+'],
    ('bigWig', None): ['-type=bigWig'],
    ('bigInteract', None): ['-type=bigBed5+13', '-as=src/schemas/file_formats/as/interact.as'],

}

HUMAN_ASSEMBLIES = ['GRCh38', 'hg19']

RODENT_ASSEMBLIES = ['GRCm39', 'GRCm38', 'MGSCv37']


FASTA_VALIDATION_INFO = {
    0: 'this is a valid fasta file',
    1: 'the first line does not start with a > (rule 1 violated).',
    2: 'there are duplicate sequence identifiers in the file (rule 7 violated)',
    4: 'there are characters in a sequence line other than [A-Za-z]'
}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            'asctime': self.formatTime(record, self.datefmt),
            'levelname': record.levelname,
            'message': record.getMessage(),
        }
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = ''.join(
                    traceback.format_exception(*record.exc_info))
            if record.exc_text:
                data['exc_text'] = record.exc_text.splitlines()
        return json.dumps(data)


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def file_validation(relative_path, uuid, submitted_md5sum, file_format, output_type, submitted_file_size_bytes, number_of_reads, read_length, file_format_type, assembly):
    logger.info(f'Checking file uuid {uuid}')
    local_file_path = get_local_file_path(relative_path)
    true_file_size_bytes = os.path.getsize(local_file_path)
    errors = {}
    is_gzipped = is_file_gzipped(local_file_path)
    error = check_valid_gzipped_file_format(is_gzipped, file_format)
    errors.update(error)
    error = check_file_size(submitted_file_size_bytes, true_file_size_bytes)
    errors.update(error)
    error = check_md5sum(submitted_md5sum, local_file_path)
    errors.update(error)

    if is_gzipped:
        error = check_content_md5sum(local_file_path)
        errors.update(error)

    if file_format == 'bam':
        error = bam_pysam_check(local_file_path, number_of_reads)
        errors.update(error)
    elif file_format == 'fastq':
        error = validate_files_fastq_check(local_file_path)
        errors.update(error)
        error = fastq_check(local_file_path, number_of_reads, read_length)
        errors.update(error)
    elif file_format in ['bed', 'bigWig', 'bigInteract', 'bigBed', 'bedpe']:
        error = validate_files_check(
            local_file_path, file_format, file_format_type, assembly)
        errors.update(error)
    elif file_format == 'fasta':
        error = fasta_check(local_file_path, is_gzipped)
        errors.update(error)
    elif file_format in TABULAR_FORMAT:
        error = tabular_file_check(output_type, local_file_path)
        errors.update(error)
    logger.info(f'Completed file validation for file uuid {uuid}.')

    if errors:
        return {
            'uuid': uuid,
            'validation_result': 'failed',
            'errors': errors
        }
    else:
        return {
            'uuid': uuid,
            'validation_result': 'pass'
        }


def get_local_file_path(relative_path):
    file_path = DATA_DIR + relative_path
    return file_path


def is_file_gzipped(file_path):
    try:
        gzip.GzipFile(filename=file_path).read(1)
        return True
    except gzip.BadGzipFile:
        return False


def check_valid_gzipped_file_format(is_gzipped, file_format, zip_file_format=ZIP_FILE_FORMAT):
    error = {}
    if file_format in zip_file_format and not is_gzipped:
        error = {'gzip': f'{file_format} file should be gzipped'}
    elif file_format not in zip_file_format and is_gzipped:
        error = {'gzip': f'{file_format} file should not be gzipped'}
    return error


def get_file_size_bytes(file_path):
    return os.path.getsize()


def check_file_size(file_size, size_in_cloud_storage):
    error = {}
    if size_in_cloud_storage != file_size:
        error = {
            'file_size': f'submitted file zise {str(file_size)} does not mactch file zise {str(size_in_cloud_storage)} in cloud storage'}
    return error


def calculate_md5sum(file_path, unzip=False, chunk_size=CHUNK_SIZE):
    md5 = hashlib.md5()
    if unzip:
        open_func = gzip.open
    else:
        open_func = open
    with open_func(file_path, 'rb') as fp:
        while chunk := fp.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()


def calculate_content_md5sum(file_path):
    return calculate_md5sum(file_path, unzip=True)


def check_md5sum(expected_md5sum, file_path, chunk_size=CHUNK_SIZE):
    error = {}
    calculated_md5sum = calculate_md5sum(file_path)
    if expected_md5sum != calculated_md5sum:
        error = {
            'md5sum': f'submitted file md5sum {expected_md5sum} does not match calculated md5sum {calculated_md5sum}.'}
    return error


def check_content_md5sum(file_path, chunk_size=CHUNK_SIZE, base_url=CONTENT_MD5SUM_URL, username=ENCODE_ACCESS_KEY, password=ENCODE_SECRET_KEY):
    error = {}
    content_md5sum = calculate_content_md5sum(file_path)
    logger.info(f'content md5sum is {content_md5sum}')
    url = base_url + content_md5sum
    session = requests.Session()
    session.auth = (username, password)
    conflict_files = session.get(url).json()['@graph']
    if conflict_files:
        accessions = []
        for file in conflict_files:
            accessions.append(file['accession'])
        error = {
            'content_md5sum': f"content md5sum {content_md5sum} conflicts with content md5sum of existing file(s): {', '.join(accessions)}"}
    return error


def bam_pysam_check(file_path, number_of_reads):
    error = {}
    try:
        pysam.quickcheck(file_path)
        result = pysam.stats(file_path)
        if 'SN\tis sorted:\t0' in result:
            error = {'bam_error': 'the bam file is not sorted'}
        else:
            samfile = pysam.AlignmentFile(file_path, 'rb')
            count = samfile.count(until_eof=True)
            logger.info(f'the number of reads: {count}')
            if count != number_of_reads:
                error = {
                    'bam_error': f'sumbitted number of reads {number_of_reads} does not match number of reads {count} in cloud storage'}
            samfile.close()
    except pysam.utils.SamtoolsError as e:
        error = {
            'bam_error': f'file is not valid bam file by SamtoolsError: {str(e)}'}
    return error


def fastq_check(file_path, number_of_reads, read_length):
    error = {}
    temp_file = tempfile.NamedTemporaryFile()
    shutil.copyfile(file_path, temp_file.name)
    fq = pyfastx.Fastq(temp_file.name)
    count = len(fq)
    avg_len = int(fq.avglen)
    logger.info(f'number of reads is {count}')
    logger.info(f'read length is {avg_len}')
    if count != number_of_reads:
        error['fastq_number_of_reads'] = f'sumbitted number of reads {number_of_reads} does not match number of reads {count} in cloud storage'
    if avg_len != read_length:
        error['fastq_read_length'] = f'sumbitted read length {read_length} does not match read length {avg_len} in cloud storage'
    fxi_file_path = temp_file.name + '.fxi'
    if os.path.exists(fxi_file_path):
        os.remove(fxi_file_path)
    return error


def fasta_check(file_path, is_gzipped, info=FASTA_VALIDATION_INFO):
    error = {}
    if is_gzipped:
        with gzip.open(file_path, 'rb') as f_in:
            temp_file = tempfile.NamedTemporaryFile()
            with open(temp_file.name, 'wb') as f_out:
                temp_file = tempfile.NamedTemporaryFile()
                shutil.copyfileobj(f_in, f_out)
        file_path = temp_file.name
    try:
        code = fasta_validator(file_path)
        if code != 0:
            error['fasta_error'] = info[code]
    except Exception as e:
        error['fasta_error'] = str(e)
    return error


def tabular_file_check(output_type, file_path, schemas=TABULAR_FILE_SCHEMAS, max_error=MAX_NUM_ERROR_FOR_TABULAR_FILE):
    system.trusted = True
    error = {}
    schema_path = schemas.get(output_type)
    report = validate(file_path, schema=schema_path)
    if not report.valid:
        report = report.flatten(['rowNumber', 'fieldNumber', 'type', 'note'])
        if len(report) > max_error:
            report = report[0:max_error]
        error = {
            'tabular_file_error': report
        }
    return error


def validate_files_check(file_path, file_format, file_format_type, assembly):
    error = {}
    chrom_info_file = get_chrom_info_file(assembly)

    validate_args = get_validate_files_args(
        file_format, file_format_type, chrom_info_file)
    command = ['validateFiles'] + validate_args + [file_path]
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        error['validate_files'] = e.output.decode(
            errors='replace').rstrip('\n')
    return error


def validate_files_fastq_check(file_path):
    error = {}
    command = ['validateFiles'] + ['-type=fastq'] + [file_path]
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        error['validate_files'] = e.output.decode(
            errors='replace').rstrip('\n')
    return error


def get_validate_files_args(file_format, file_format_type, chrom_info_file, schema=VALIDATE_FILES_ARGS):
    args = schema.get((file_format, file_format_type))
    chrom_info_arg = 'chromInfo=' + chrom_info_file
    args.append(chrom_info_arg)
    return args


def get_chrom_info_file(assembly, chrom_info_dir=CHROM_INFO_DIR):
    if assembly in HUMAN_ASSEMBLIES:
        organism = 'human'
    elif assembly in RODENT_ASSEMBLIES:
        organism = 'rodent'

    return f'{chrom_info_dir}/{organism}/{assembly}/chrom.sizes'


def main():
    try:
        response = file_validation(KEY, UUID, MD5SUM, FILE_FORMAT, OUTPUT_TYPE,
                                   FILE_SIZE, NUMBER_OF_READS, READ_LENGTH, FILE_FORMAT_TYPE, ASSEMBLY)
        logging.info(json.dumps(response))
    except Exception as err:
        message = f'exception occurred when checking file uuid #{UUID}: {str(err)}'
        logger.exception(message)
        sys.exit(1)  # Retry Job Task by exiting the process


# Start script
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checkfiles argumentparser')
    parser.add_argument('--uuid', type=str,
                        help='UUID of the fileobject to be checked')
    parser.add_argument(
        '--server', type=str, help='igvf instance to check. https://api.sandbox.igvf.org for example')
    parser.add_argument('--portal-key-id', type=str, help='Portal key id')
    parser.add_argument('--portal-secret-key', type=str,
                        help='Portal secret key')

    args = parser.parse_args()
    main()
