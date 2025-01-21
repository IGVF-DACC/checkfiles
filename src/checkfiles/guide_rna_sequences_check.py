from frictionless import Check, errors


class GuideRnaSequencesCheck(Check):
    Errors = [errors.ConstraintError]

    def validate_row(self, row):
        if row['targeting'] == True:
            if not row['guide_chr']:
                note = 'guide_chr is required when targeting is True'
                yield errors.ConstraintError.from_row(row, note=note, field_name='guide_chr')
            if not row['guide_start']:
                note = 'guide_start is required when targeting is True'
                yield errors.ConstraintError.from_row(row, note=note, field_name='guide_start')
            if not row['guide_end']:
                note = 'guide_end is required when targeting is True'
                yield errors.ConstraintError.from_row(row, note=note, field_name='guide_end')
            if not row['strand']:
                note = 'strand is required when targeting is True'
                yield errors.ConstraintError.from_row(row, note=note, field_name='strand')
            if not row['pam']:
                note = 'pam is required when targeting is True'
                yield errors.ConstraintError.from_row(row, note=note, field_name='pam')
