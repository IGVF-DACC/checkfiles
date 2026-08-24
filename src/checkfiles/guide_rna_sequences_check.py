from frictionless import Check, errors
import re


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == '':
            return True
        if stripped.lower() == 'nan':
            return True
    return False


# ENSEMBL gene ID: ENSG + 11 digits (GENCODE 43 and GENCODE M36)
ENSEMBL_GENE_RE = re.compile(r'^(ENSG[0-9]{11}|ENSMUSG[0-9]{11})(\.[0-9]+)?$')

# ENSEMBL exon ID: ENSE + 11 digits (human) or ENSMUSE + 11 digits (mouse)
ENSEMBL_EXON_RE = re.compile(r'^(ENSE[0-9]{11}|ENSMUSE[0-9]{11})(\.[0-9]+)?$')

# Coordinates: chr1:3691430-3691731
COORD_RE = re.compile(r'^chr[0-9A-Za-z._-]+:[0-9]+-[0-9]+$')

# SPDI: e.g. NC_000007.14:117548628:TT:TTT
SPDI_RE = re.compile(
    r'^[A-Z]{2}_[0-9]+(?:\.[0-9]+)?:[0-9]+:[ACGTN\-]+:[ACGTN\-]+$'
)

COORDINATE_GENOMIC_ELEMENTS = {
    'enhancer',
    'insulator',
    'silencer',
    'distal element',
    'intron',
}


def _row_field_names(row):
    field_names = getattr(row, 'field_names', None)
    if field_names:
        return list(field_names)
    if hasattr(row, 'keys'):
        return list(row.keys())
    return []


def _has_prime_editing_fields(row):
    field_names = _row_field_names(row)
    return (
        'primer_binding_sequence' in field_names
        or 'rt_template_sequence' in field_names
    )


def _normalized_optional(value):
    if _is_missing(value):
        return None
    return value


class GuideRnaSequencesCheck(Check):
    Errors = [errors.ConstraintError]

    def __init__(self, **options):
        super().__init__(**options)
        self._guide_id_to_design = {}
        self._design_to_guide_id = {}

    def validate_row(self, row):
        # 1) guide_id must map to a single guide design
        for error in self._check_guide_design_mapping(row):
            yield error

        targeting = row.get('targeting')
        guide_type = row.get('type')
        genomic_element = row.get('genomic_element')

        # 2) targeting/type relationship
        for error in self._check_targeting_type_relationship(
            row,
            targeting=targeting,
            guide_type=guide_type,
        ):
            yield error

        # 3) required fields for targeting guides (skip if targeting is False)
        for error in self._check_required_fields_for_targeting(
            row,
            targeting=targeting,
        ):
            yield error

        # 4) putative_target_genes requirement for positive controls
        for error in self._check_putative_target_genes(
            row,
            guide_type=guide_type,
            genomic_element=genomic_element,
        ):
            yield error

        # 5) intended_target_name format rules
        for error in self._check_intended_target_name_format(
            row,
            genomic_element=genomic_element,
        ):
            yield error

    def _design_key(self, row, spacer):
        if _has_prime_editing_fields(row):
            return (
                spacer,
                _normalized_optional(row.get('primer_binding_sequence')),
                _normalized_optional(row.get('rt_template_sequence')),
            )
        return (spacer,)

    def _check_guide_design_mapping(self, row):
        guide_id = row.get('guide_id')
        spacer = row.get('spacer')

        if _is_missing(guide_id) or _is_missing(spacer):
            return

        prime_editing = _has_prime_editing_fields(row)
        design = self._design_key(row, spacer)

        existing_design = self._guide_id_to_design.get(guide_id)
        if existing_design is None:
            self._guide_id_to_design[guide_id] = design
        elif existing_design != design:
            if prime_editing:
                note = (
                    f'guide_id {guide_id} is associated with multiple guide designs: '
                    f'{existing_design} and {design}; '
                    'each guide_id must be associated with a single guide design '
                    'defined by spacer, primer_binding_sequence, and '
                    'rt_template_sequence.'
                )
            else:
                existing_spacer = existing_design[0]
                note = (
                    f'guide_id {guide_id} is associated with multiple spacers: '
                    f'{existing_spacer} and {spacer}; '
                    'there must be a 1-to-1 mapping between guide_id and spacer.'
                )
            yield errors.ConstraintError.from_row(
                row,
                note=note,
                field_name='guide_id',
            )

        existing_guide_id = self._design_to_guide_id.get(design)
        if existing_guide_id is None:
            self._design_to_guide_id[design] = guide_id
        elif existing_guide_id != guide_id:
            if prime_editing:
                note = (
                    f'guide design {design} is associated with multiple guide_ids: '
                    f'{existing_guide_id} and {guide_id}; '
                    'the same spacer may only be reused when '
                    'primer_binding_sequence and/or rt_template_sequence differ.'
                )
            else:
                note = (
                    f'spacer {spacer} is associated with multiple guide_ids: '
                    f'{existing_guide_id} and {guide_id}; '
                    'there must be a 1-to-1 mapping between guide_id and spacer.'
                )
            yield errors.ConstraintError.from_row(
                row,
                note=note,
                field_name='spacer',
            )

    def _check_targeting_type_relationship(self, row, targeting, guide_type):
        if _is_missing(guide_type) or targeting is None:
            return

        non_targeting_types = {
            'non-targeting',
            'safe-targeting',
        }
        targeting_types = {
            'targeting',
            'positive control',
            'variant',
        }

        if guide_type in non_targeting_types and targeting is not False:
            note = f'targeting must be False when type is {guide_type}'
            yield errors.ConstraintError.from_row(
                row,
                note=note,
                field_name='targeting',
            )

        if guide_type in targeting_types and targeting is not True:
            note = f'targeting must be True when type is {guide_type}'
            yield errors.ConstraintError.from_row(
                row,
                note=note,
                field_name='targeting',
            )

    def _check_required_fields_for_targeting(self, row, targeting):
        if targeting is False:
            return

        required_when_not_false = [
            'guide_chr',
            'guide_start',
            'guide_end',
            'strand',
            'pam',
            'genomic_element',
            'intended_target_name',
            'intended_target_chr',
            'intended_target_start',
            'intended_target_end',
        ]

        for field_name in required_when_not_false:
            value = row.get(field_name)
            if _is_missing(value):
                note = f'{field_name} is required when targeting is not False'
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name=field_name,
                )

    def _check_putative_target_genes(self, row, guide_type, genomic_element):
        if guide_type != 'positive control':
            return

        if genomic_element not in {
            'enhancer',
            'insulator',
            'silencer',
            'distal element',
        }:
            return

        putative_target_genes = row.get('putative_target_genes')
        if _is_missing(putative_target_genes) or putative_target_genes == []:
            note = (
                'putative_target_genes is required when type is positive control '
                f'and genomic_element is {genomic_element}'
            )
            yield errors.ConstraintError.from_row(
                row,
                note=note,
                field_name='putative_target_genes',
            )
            return

        # Enforce ENSEMBL gene ID format on each entry
        if isinstance(putative_target_genes, list):
            genes = putative_target_genes
        else:
            genes = [putative_target_genes]

        for gene in genes:
            if _is_missing(gene):
                continue
            if not ENSEMBL_GENE_RE.match(gene):
                note = (
                    'putative_target_genes entries must be ENSEMBL gene IDs '
                    f'(e.g. ENSG00000123456), but got {gene}'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='putative_target_genes',
                )

    def _check_intended_target_name_format(self, row, genomic_element):
        intended_target_name = row.get('intended_target_name')

        if _is_missing(genomic_element) or _is_missing(intended_target_name):
            return

        if genomic_element == 'variant':
            if not SPDI_RE.match(intended_target_name):
                note = (
                    'intended_target_name must be a normalized SPDI identifier when '
                    'genomic_element is variant, e.g. '
                    'NC_000007.14:117548628:TTTTTTT:TTTTTTTTT'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='intended_target_name',
                )
            return

        if genomic_element in {
            'promoter',
            'gene',
            'splice site'
        }:
            if not ENSEMBL_GENE_RE.match(intended_target_name):
                note = (
                    f'intended_target_name must be an ENSEMBL gene ID when '
                    f'genomic_element is promoter/gene/splice site, e.g. ENSG00000123456'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='intended_target_name',
                )
            return

        if genomic_element == 'exon':
            if not ENSEMBL_EXON_RE.match(intended_target_name):
                note = (
                    'intended_target_name must be an ENSEMBL exon ID when '
                    'genomic_element is exon, e.g. ENSE00001623794'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='intended_target_name',
                )
            return

        if genomic_element in COORDINATE_GENOMIC_ELEMENTS:
            if not COORD_RE.match(intended_target_name):
                if genomic_element == 'intron':
                    note = (
                        'intended_target_name must be genomic coordinates when '
                        'genomic_element is intron, e.g. chr1:3691430-3691731'
                    )
                else:
                    note = (
                        'intended_target_name must be genomic coordinates when '
                        'genomic_element is an enhancer/insulator/silencer/'
                        'distal element, e.g. chr1:3691430-3691731'
                    )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='intended_target_name',
                )
