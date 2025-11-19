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


# ENSEMBL gene ID: ENSG + 11 digits (GENCODE v43-style)
ENSEMBL_GENE_RE = re.compile(r'^ENSG[0-9]{11}$')

# Coordinates: chr1:3691430-3691731
COORD_RE = re.compile(r'^chr[0-9A-Za-z._-]+:[0-9]+-[0-9]+$')

# SPDI: e.g. NC_000007.14:117548628:TT:TTT
SPDI_RE = re.compile(
    r'^[A-Z]{2}_[0-9]+(?:\.[0-9]+)?:[0-9]+:[ACGTN\-]+:[ACGTN\-]+$'
)


class GuideRnaSequencesCheck(Check):
    Errors = [errors.ConstraintError]

    def __init__(self, **options):
        super().__init__(**options)
        self._guide_id_to_spacer = {}
        self._spacer_to_guide_id = {}

    def validate_row(self, row):

        # ---------- 1) Enforce guide_id <-> spacer 1-to-1 ----------
        guide_id = row.get('guide_id')
        spacer = row.get('spacer')

        if not _is_missing(guide_id) and not _is_missing(spacer):
            existing_spacer = self._guide_id_to_spacer.get(guide_id)
            if existing_spacer is None:
                self._guide_id_to_spacer[guide_id] = spacer
            elif existing_spacer != spacer:
                note = (
                    f'guide_id {
                        guide_id} is associated with multiple spacers: '
                    f'{existing_spacer} and {spacer}; there must be a 1-to-1 '
                    'mapping between guide_id and spacer.'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='guide_id',
                )

            existing_guide_id = self._spacer_to_guide_id.get(spacer)
            if existing_guide_id is None:
                self._spacer_to_guide_id[spacer] = guide_id
            elif existing_guide_id != guide_id:
                note = (
                    f'spacer {spacer} is associated with multiple guide_id: '
                    f'{existing_guide_id} and {
                        guide_id}; there must be a 1-to-1 '
                    'mapping between guide_id and spacer.'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='spacer',
                )

        targeting = row.get('targeting')
        guide_type = row.get('type')

        # ---------- 2) targeting/type relationship ----------
        if not _is_missing(guide_type) and targeting is not None:
            non_targeting_types = {
                'non-targeting',
                'safe-targeting',
                'negative control',
            }
            targeting_types = {
                'targeting',
                'positive control',
                'variant',
            }

            if guide_type in non_targeting_types and targeting is not False:
                note = (
                    f'targeting must be False when type is {guide_type}.'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='targeting',
                )

            if guide_type in targeting_types and targeting is not True:
                note = (
                    f'targeting must be True when type is {guide_type}.'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='targeting',
                )

        # ---------- 3) Conditionally required fields for targeting guides ----------
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

        # ---------- 4) putative_target_genes requirement for positive controls ----------
        genomic_element = row.get('genomic_element')

        if guide_type == 'positive control' and genomic_element in {
            'enhancer',
            'insulator',
            'silencer',
            'distal element'
        }:
            value = row.get('putative_target_genes')
            if _is_missing(value) or value == []:
                note = (
                    'putative_target_genes is required when type is positive control '
                    f'and genomic_element is {genomic_element}'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='putative_target_genes',
                )

        # ---------- 5) intended_target_name format by genomic_element ----------
        intended_target_name = row.get('intended_target_name')
        if _is_missing(genomic_element) or _is_missing(intended_target_name):
            return

        if genomic_element == 'variant':
            if not SPDI_RE.match(intended_target_name):
                note = (
                    'intended_target_name must be a normalized SPDI identifier '
                    'when genomic_element == variant, e.g. '
                    'NC_000007.14:117548628:TTTTTTT:TTTTTTTTT'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='intended_target_name',
                )

        elif genomic_element in {'promoter', 'gene', 'splice site'}:
            if not ENSEMBL_GENE_RE.match(intended_target_name):
                note = (
                    'intended_target_name must be an ENSEMBL gene ID '
                    f'when genomic_element == {genomic_element}, '
                    'e.g. ENSG00000123456'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='intended_target_name',
                )

        elif genomic_element in {
            'enhancer',
            'insulator',
            'silencer',
            'distal element',
        }:
            if not COORD_RE.match(intended_target_name):
                note = (
                    'intended_target_name must be genomic coordinates '
                    'when genomic_element is an enhancer/insulator/silencer/'
                    'distal element, e.g. chr1:3691430-3691731'
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='intended_target_name',
                )
