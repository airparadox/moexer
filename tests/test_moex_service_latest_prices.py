from services.moex_service import MOEXService


class DummyResponse:
    def __init__(self, json_data):
        self._json = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


class DummySession:
    def __init__(self, json_data):
        self._json = json_data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def get(self, url, params=None):
        return DummyResponse(self._json)


def test_get_latest_prices_uses_available_columns(monkeypatch):
    json_data = {
        "securities": {
            "columns": ["SECID", "PREVADMITTEDQUOTE"],
            "data": [["TRNFP", 123.45]],
        }
    }
    monkeypatch.setattr("requests.Session", lambda: DummySession(json_data))
    service = MOEXService()
    df = service.get_latest_prices(["TRNFP"])
    assert df.loc["TRNFP", "price"] == 123.45
