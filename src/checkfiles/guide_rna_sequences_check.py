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

    def __init__(self, **options):
        super().__init__(**options)
        self._guide_id_to_spacer = {}
        self._spacer_to_guide_id = {}

    def validate_row(self, row):

        # ---------- 1) Enforce guide_id <-> spacer 1-to-1 ----------
        guide_id = row.get("guide_id")
        spacer = row.get("spacer")

        if not _is_missing(guide_id) and not _is_missing(spacer):
            existing_spacer = self._guide_id_to_spacer.get(guide_id)
            if existing_spacer is None:
                self._guide_id_to_spacer[guide_id] = spacer
            elif existing_spacer != spacer:
                note = (
                    f"guide_id '{guide_id}' is associated with multiple spacers "
                    f"('{existing_spacer}' and '{spacer}'); there must be a 1-to-1 "
                    "mapping between guide_id and spacer."
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name="guide_id",
                )

            existing_guide_id = self._spacer_to_guide_id.get(spacer)
            if existing_guide_id is None:
                self._spacer_to_guide_id[spacer] = guide_id
            elif existing_guide_id != guide_id:
                note = (
                    f"spacer '{spacer}' is associated with multiple guide_ids "
                    f"('{existing_guide_id}' and '{guide_id}'); there must be a 1-to-1 "
                    "mapping between guide_id and spacer."
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name="spacer",
                )

        # ---------- 2) Conditionally required fields for targeting guides ----------
        targeting = row.get("targeting")

        if targeting is False:
            return

        required_when_not_false = [
            "guide_chr",
            "guide_start",
            "guide_end",
            "strand",
            "pam",
            "genomic_element",
            "intended_target_name",
            "intended_target_chr",
            "intended_target_start",
            "intended_target_end",
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

        # ---------- 3) putative_target_genes requirement for positive controls ----------
        genomic_element = row.get("genomic_element")
        guide_type = row.get("type")

        if guide_type == "positive control" and genomic_element in {
            "enhancer",
            "insulator",
            "silencer",
            "distal element",
            "splice site",
        }:
            value = row.get("putative_target_genes")
            if _is_missing(value) or value == []:
                note = (
                    "putative_target_genes is required when type is 'positive control' "
                    f"and genomic_element is '{genomic_element}'"
                )
                yield errors.ConstraintError.from_row(
                    row,
                    note=note,
                    field_name="putative_target_genes",
                )
