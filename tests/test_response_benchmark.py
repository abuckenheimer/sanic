import pytest
from sanic.response import HTTPResponse, raw

headers = [
    {},
    {"content-type": "text/plain"},
    {"content-type": "text/plain", "charset": "us-ascii"},
    {"content-type": "text/plain", "charset": "us-ascii", "another": "opt"},
    {"content-type": "attachment", "filename": "silly.txt"},
    {"content-type": "attachment", "filename": "strange;name"},
    {"content-type": "attachment", "filename": "strange;name", "size": "123"},
    {"content-type": "form-data", 'name': 'files', 'filename': 'fo"o;bar\\'},
    # Chrome:
    # Content-Disposition: form-data; name="foo%22;bar\"; filename="😀"
    {"Content-Disposition": "form-data", 'name': 'foo";bar\\', 'filename': '😀'},
    # Firefox:
    # Content-Disposition: form-data; name="foo\";bar\"; filename="😀"
    {"Content-Disposition": "form-data", 'name': 'foo";bar\\', 'filename': '😀'},
]


@pytest.fixture(scope="function", params=headers)
def header(request):
    return request.param


bodies = [
    12354,
    "OK",
    "long body",
]


@pytest.fixture(scope="function", params=bodies)
def body(request):
    return request.param


def test_response_output(benchmark, body, header):
    """Test when a response body sent from the application is not a string"""
    if body == "long body":
        body *= 10000
    benchmark(HTTPResponse(body=body, headers=header).output)


def test_raw_response_output(benchmark, body, header):
    """Test when a response body sent from the application is not a string"""
    if body == "long body":
        body *= 10000
    body = str(body).encode()
    benchmark(raw(body=body, headers=header).output)
