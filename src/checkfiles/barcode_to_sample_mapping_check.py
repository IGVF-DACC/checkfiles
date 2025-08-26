from frictionless import Check, errors


class BarcodeToSampleMappingCheck(Check):
    Errors = [errors.RowConstraintError]

    def validate_row(self, row):
        # for row position, parse barcode type and well, if any of them is not empty, then the other two must not be empty
        if (row['position'] and row['parse barcode type'] and row['well']) or (not row['position'] and not row['parse barcode type'] and not row['well']):
            pass
        else:
            note = 'position, parse barcode type and well must be all empty or all not empty'
            yield errors.RowConstraintError.from_row(row, note=note)
