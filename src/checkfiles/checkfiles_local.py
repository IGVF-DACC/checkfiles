import argparse
import logging
import file
import logformatter
from pprint import pprint

from checkfiles import TABULAR_FORMAT, MAX_NUM_ERROR_FOR_TABULAR_FILE, vcf_sequence_check, seqspec_file_check
from version import get_checkfiles_version
from checkfiles import check_valid_gzipped_file_format, check_md5sum, bam_pysam_check, fastq_get_average_read_length_and_number_of_reads, fasta_check, tabular_file_check, validate_files_check, validate_files_fastq_check

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logformatter.JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def file_validation(input_file_path, validation_record: file.FileValidationRecord, submitted_md5sum, content_type, file_format_type, assembly, tabular_file_schema_path, max_tabular_file_errors):
    logger.info(f'Checking file: {input_file_path}')
    validation_record.update_info(
        {'checkfiles_version': get_checkfiles_version()})
    try:
        true_file_size_bytes = validation_record.file.size
        validation_record.update_info({'file_size': true_file_size_bytes})
        if true_file_size_bytes == 0:
            validation_record.update_errors(
                {'file_size': 'file has zero size'})
            return validation_record
    except FileNotFoundError:
        logger.warning(f'File not found at path {input_file_path}')
        validation_record.file_not_found = True
        return validation_record
    file_format = validation_record.file.file_format
    is_gzipped = validation_record.file.is_zipped
    gzipped_format_error = check_valid_gzipped_file_format(
        is_gzipped, file_format)
    validation_record.update_errors(gzipped_format_error)
    md5_sum_error = check_md5sum(
        submitted_md5sum, validation_record.file.md5sum)
    validation_record.update_errors(md5_sum_error)
    if file_format == 'bam':
        bam_check_result = bam_pysam_check(input_file_path)
        if 'bam_error' in bam_check_result:
            validation_record.update_errors(bam_check_result)
        else:
            validation_record.update_info(bam_check_result)
    elif file_format == 'fastq':
        validate_files_fastq_check_error = validate_files_fastq_check(
            input_file_path)
        validation_record.update_errors(validate_files_fastq_check_error)
        fastq_read_info = fastq_get_average_read_length_and_number_of_reads(
            input_file_path)
        validation_record.update_info(fastq_read_info)
    elif file_format in ['bed', 'bigWig', 'bigInteract', 'bigBed', 'bedpe']:
        validate_files_check_error = validate_files_check(
            input_file_path, file_format, file_format_type, assembly)
        validation_record.update_errors(validate_files_check_error)
    elif file_format == 'fasta':
        fasta_check_error = fasta_check(input_file_path, is_gzipped)
        validation_record.update_errors(fasta_check_error)
    elif file_format in TABULAR_FORMAT:
        if not content_type and not tabular_file_schema_path:
            logger.info(
                'file content type and tabular file schema are not provided for the tabular file, will only perform tabular file based checks')
        tabular_file_check_error = tabular_file_check(
            content_type, input_file_path, is_gzipped, schema_path=tabular_file_schema_path, max_error=max_tabular_file_errors, allow_additional_fields=True)
        validation_record.update_errors(tabular_file_check_error)
    elif file_format == 'vcf':
        vcf_check_error = vcf_sequence_check(input_file_path, assembly)
        validation_record.update_errors(vcf_check_error)
    elif content_type == 'seqspec':
        seqspec_check_error = seqspec_file_check(input_file_path)
        validation_record.update_errors(seqspec_check_error)

    if validation_record.errors:
        validation_record.validation_success = False
        return validation_record
    else:
        validation_record.validation_success = True
        return validation_record


def main(args):
    if args.assembly is None and args.file_format in ['bed', 'bigWig', 'bigInteract', 'bigBed', 'bedpe']:
        raise ValueError(
            'assembly is required for file formats: bed, bigWig, bigInteract, bigBed, bedpe')
    if args.file_format in ['bed', 'bigBed'] and args.file_format_type is None:
        raise ValueError(
            'file_format_type is required for bed and bigBed file')
    file_validation_record = file.FileValidationRecord(
        file.get_file(args.input_file_path, args.file_format))
    file_validation_complete_record = file_validation(args.input_file_path, file_validation_record,
                                                      args.md5sum, args.content_type, args.file_format_type, args.assembly, args.tabular_file_schema_path, args.max_tabular_file_errors)
    if not file_validation_complete_record.file_not_found:
        if file_validation_complete_record.errors:
            logger.info(
                f'file validation is completed and errors are found.')
        else:
            logger.info('file validation is completed and no error found.')
        print('\nFile info:')
        pprint(file_validation_complete_record.info)
        if file_validation_complete_record.errors:
            print('\nFile errors:')
            pprint(file_validation_complete_record.errors)


# Start script
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checkfiles argumentparser')
    parser.add_argument('--input_file_path', required=True,
                        help='path of the local file to be checked.')
    # assembly is required for some file formats: 'bed', 'bigWig', 'bigInteract', 'bigBed', 'bedpe'
    parser.add_argument(
        '--assembly', choices=['GRCh38', 'GRCm39'], help='assembly of the file to be checked.')
    parser.add_argument(
        '--content_type', help='content type of the file to be checked.')
    parser.add_argument('--file_format', choices=['bam', 'bed', 'bigWig', 'bigInteract', 'bigBed', 'bedpe',
                        'csv', 'fasta', 'fastq', 'mtx', 'tbi', 'tsv', 'txt', 'vcf', 'yaml'], required=True, help='file format of the file to be checked.')
    # file_format_type is required for bed file and bigBed file
    parser.add_argument('--file_format_type',
                        help='file format type of the file to be checked.')
    parser.add_argument('--md5sum', help='md5sum of the file to be checked.')
    parser.add_argument('--tabular_file_schema_path',
                        help='the relative path to the schema file of the tabular file.')
    parser.add_argument('--max_tabular_file_errors', type=int, default=MAX_NUM_ERROR_FOR_TABULAR_FILE,
                        help='maximum number of errors to be scaned for the tabular file.')

    args = parser.parse_args()
    main(args)
