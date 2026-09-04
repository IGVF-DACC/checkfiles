from frictionless import Check, errors


PROMOTER = 'promoter'


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == '':
            return True
        if stripped.lower() == 'nan':
            return True
        if stripped.upper() == 'N/A':
            return True
    return False


def _row_field_names(row):
    field_names = getattr(row, 'field_names', None)
    if field_names:
        return list(field_names)
    if hasattr(row, 'keys'):
        return list(row.keys())
    return []


class RegulatorCheck(Check):
    Errors = [errors.ConstraintError]

    def validate_row(self, row):
        field_names = _row_field_names(row)
        if 'genomic_element_1' in field_names or 'gene_1' in field_names:
            yield from self._check_promoter_genes(row, 1)
            yield from self._check_promoter_genes(row, 2)
            return
        yield from self._check_gene_program_regulator_genes(row)

    def _check_promoter_genes(self, row, index):
        genomic_element = row.get(f'genomic_element_{index}')
        if _is_missing(genomic_element):
            return
        if str(genomic_element).strip().lower() != PROMOTER:
            return

        for field_name in (f'gene_{index}', f'gene_{index}_symbol'):
            if _is_missing(row.get(field_name)):
                yield errors.ConstraintError.from_row(
                    row,
                    note=(
                        f'{field_name} is required when genomic_element_{index} '
                        'is promoter'
                    ),
                    field_name=field_name,
                )

    def _check_gene_program_regulator_genes(self, row):
        if not self._is_promoter_regulator(row):
            return
        for field_name in ('gene', 'gene_symbol'):
            if _is_missing(row.get(field_name)):
                yield errors.ConstraintError.from_row(
                    row,
                    note=(
                        f'{field_name} is required for promoter-targeting '
                        'regulators'
                    ),
                    field_name=field_name,
                )

    def _is_promoter_regulator(self, row):
        genomic_element = row.get('genomic_element')
        if (
            not _is_missing(genomic_element)
            and str(genomic_element).strip().lower() == PROMOTER
        ):
            return True
        return not _is_missing(row.get('promoter_coordinates'))
