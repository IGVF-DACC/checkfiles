import datetime
import pytest


@pytest.fixture(autouse=True)
def freeze_checkfiles_time(mocker):
    fixed_now = datetime.datetime(
        2026, 2, 11, 12, 34, 56, tzinfo=datetime.timezone.utc)
    mocker.patch('checkfiles.checkfiles.get_current_utc_time',
                 return_value=fixed_now)
    return fixed_now
