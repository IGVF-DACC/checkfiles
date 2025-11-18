from frictionless import Check, errors


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


class GuideRnaSequencesCheck(Check):
    Errors = [errors.ConstraintError]

    def validate_row(self, row):
        targeting = row.get('targeting')

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
                note = f"{field_name} is required when targeting is not False"
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name=field_name,
                )

        genomic_element = row.get('genomic_element')
        guide_type = row.get('type')

        if guide_type == 'positive control' and genomic_element in {
            'enhancer',
            'insulator',
            'silencer',
            'distal element',
            'splice site',
        }:
            value = row.get('putative_target_genes')
            if _is_missing(value) or value == []:
                note = (
                    "putative_target_genes is required when type is 'positive control' "
                    f"and genomic_element is '{genomic_element}'"
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name='putative_target_genes',
                )
