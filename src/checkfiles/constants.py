
ASSEMBLY = ['GRCh38', 'GRCm39']

ASSEMBLY_REPORT_FILE_PATH = {
    # this file is downloaded here:https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/405/GCF_000001405.40_GRCh38.p14/GCF_000001405.40_GRCh38.p14_assembly_report.txt
    'GRCh38': 'src/checkfiles/supporting_files/GCF_000001405.40_GRCh38.p14_assembly_report.txt',
    # this file is downloaded here: https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/635/GCF_000001635.27_GRCm39/GCF_000001635.27_GRCm39_assembly_report.txt
    'GRCm39': 'src/checkfiles/supporting_files/GCF_000001635.27_GRCm39_assembly_report.txt',
}

ASSEMBLY_TO_CHROMINFO_PATH_MAP = {
    'GRCh38': 'src/schemas/genome_builds/chrom_sizes/GRCh38.chrom.sizes',
    'GRCm39': 'src/schemas/genome_builds/chrom_sizes/mm39.chrom.sizes',
}


ASSEMBLY_TO_SEQUENCE_FILE_MAP = {
    'GRCh38': 'src/checkfiles/supporting_files/grch38.fa',
    'GRCm39': 'src/checkfiles/supporting_files/grcm39.fa',
}

FASTA_VALIDATION_INFO = {
    0: 'this is a valid fasta file',
    1: 'the first line does not start with a > (rule 1 violated).',
    2: 'there are duplicate sequence identifiers in the file (rule 7 violated)',
    4: 'there are characters in a sequence line other than [A-Za-z]'
}

GZIP_CHECK_IGNORED_FILE_FORMAT = [
    'cram',
    'crai',
]

MAX_NUM_DETAILED_ERROR_FOR_TABULAR_FILE = 2

MAX_NUM_ERROR_FOR_TABULAR_FILE = 1000

NO_HEADER_CONTENT_TYPE = [
    'fragments'
]

TABULAR_FILE_SCHEMAS = {
    'guide RNA sequences': 'src/schemas/table_schemas/guide_rna_sequences.json',
    'MPRA sequence designs': 'src/schemas/table_schemas/mpra_sequence_designs.json',
    'prime editing guide RNA sequences': 'src/schemas/table_schemas/prime_editing_guide_rna_sequences.json',
    'reporter elements': 'src/schemas/table_schemas/reporter_elements.json',
    'reporter experiment': 'src/schemas/table_schemas/reporter_experiment.json',
    'reporter genomic element effects': 'src/schemas/table_schemas/reporter_genomic_element_effects.json',
    'reporter genomic variant effects': 'src/schemas/table_schemas/reporter_genomic_variant_effects.json',
    'reporter variants': 'src/schemas/table_schemas/reporter_variants.json',
}

TABULAR_FORMAT = [
    'tsv',
    'csv',
]

VALIDATE_FILES_ARGS = {
    ('bed', 'bed3'): ['-type=bed3'],
    ('bed', 'bed3+'): ['-tab', '-type=bed3+'],
    ('bed', 'bed5'): ['-type=bed5'],
    ('bed', 'bed6'): ['-type=bed6'],
    ('bed', 'bed6+'): ['-tab', '-type=bed6+'],
    ('bed', 'bed9'): ['-type=bed9'],
    ('bed', 'bed9+'): ['-tab', '-type=bed9+'],
    ('bed', 'bed12'): ['-type=bed12'],
    ('bed', 'bedGraph'): ['-type=bedGraph'],
    ('bed', 'mpra_starr'): ['-type=bed6+5', '-as=src/schemas/as/mpra_starr.as'],
    ('bedpe', None): ['-type=bed3+'],
    ('bigBed', 'bed3'): ['-type=bigBed3'],
    ('bigBed', 'bed3+'): ['-tab', '-type=bigBed3+'],
    ('bigWig', None): ['-type=bigWig'],
    ('bigInteract', None): ['-type=bigBed5+13', '-as=src/schemas/as/interact.as'],

}

SEQSPEC_FILE_VERSION = '0.3.0'

ZIP_FILE_FORMAT = [
    'bam',
    'bed',
    'bedpe',
    'csfasta',
    'csqual',
    'csv',
    'dat',
    'fasta',
    'fastq',
    'gaf',
    'gds',
    'gff',
    'gtf',
    'mtx',
    'obo',
    'owl',
    'tagAlign',
    'tar',
    'tbi',
    'tsv',
    'txt',
    'vcf',
    'wig',
    'xml',
    'yaml',
]
