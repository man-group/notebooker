from notebooker.web.routes.scheduling import convert_day_of_week


def test_weekdays():
    result = convert_day_of_week("1-5")
    assert result == "0-4"


def test_sunday():
    result = convert_day_of_week("0")
    assert result == "6"


def test_string_days():
    result = convert_day_of_week("MON-FRI")
    assert result == "MON-FRI"