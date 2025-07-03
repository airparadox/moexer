from unittest.mock import Mock

import pytest

from services.ifrs_service import IFRSService


@pytest.fixture
def sample_html():
    return """
    <html>
        <body>
            <table>
                <tr><th>Year</th><th>Revenue</th></tr>
                <tr><td>2023</td><td>100</td></tr>
            </table>
        </body>
    </html>
    """


def test_fetch_ifrs_from_web(sample_html, mocker):
    mock_get = mocker.patch(
        "requests.get",
        return_value=Mock(status_code=200, text=sample_html)
    )
    service = IFRSService(finance_dir="not_used")
    result = service.fetch_ifrs_from_web("TEST")
    assert "Year\tRevenue" in result
    assert "2023\t100" in result
    mock_get.assert_called()


def test_get_ifrs_data_uses_web(tmp_path, mocker):
    service = IFRSService(finance_dir=tmp_path)
    mocker.patch("requests.get", return_value=Mock(status_code=200, text="<table></table>"))
    result = service.get_ifrs_data("AAA")
    assert "Отчетность" in result or result == ""


def test_get_ifrs_data_file(tmp_path):
    file = tmp_path / "AAA.txt"
    file.write_text("data")
    service = IFRSService(finance_dir=tmp_path)
    assert service.get_ifrs_data("AAA") == "data"
