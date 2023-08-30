from notebooker.web.routes.scheduling import crontab_to_apscheduler_day_of_week
from notebooker.web.routes.scheduling import apscheduler_to_crontab_day_of_week


def test_to_appscheduler_days():
    result = crontab_to_apscheduler_day_of_week("0,1,2,3,4,5,6")
    assert result == "6,0,1,2,3,4,5"


def test_to_crontab_days():
    result = apscheduler_to_crontab_day_of_week("6,0,1,2,3,4,5")
    assert result == "0,1,2,3,4,5,6"


def test_to_appscheduler_weekdays():
    result = crontab_to_apscheduler_day_of_week("1-5")
    assert result == "0-4"


def test_to_crontab_weekdays():
    result = apscheduler_to_crontab_day_of_week("0-4")
    assert result == "1-5"


def test_to_appscheduler_sunday():
    result = crontab_to_apscheduler_day_of_week("0")
    assert result == "6"


def test_to_crontab_sunday():
    result = apscheduler_to_crontab_day_of_week("6")
    assert result == "0"


def test_to_appscheduler_string_days():
    result = crontab_to_apscheduler_day_of_week("MON-FRI")
    assert result == "MON-FRI"


def test_to_crontab_string_days():
    result = apscheduler_to_crontab_day_of_week("MON-FRI")
    assert result == "MON-FRI"
