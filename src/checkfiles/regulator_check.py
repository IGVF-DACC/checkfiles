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
            yield from self._check_promoter_genes(row, '_1')
            yield from self._check_promoter_genes(row, '_2')
            return
        yield from self._check_promoter_genes(row, '')

    def _check_promoter_genes(self, row, suffix):
        genomic_element_field = f'genomic_element{suffix}'
        genomic_element = row.get(genomic_element_field)
        if _is_missing(genomic_element):
            return
        if str(genomic_element).strip().lower() != PROMOTER:
            return

        if suffix:
            gene_fields = (f'gene{suffix}', f'gene{suffix}_symbol')
        else:
            gene_fields = ('gene', 'gene_symbol')

        for field_name in gene_fields:
            if _is_missing(row.get(field_name)):
                yield errors.ConstraintError.from_row(
                    row,
                    note=(
                        f'{field_name} is required when {genomic_element_field} '
                        'is promoter'
                    ),
                    field_name=field_name,
                )
