import asyncio
import weakref
from sanic import Sanic, response


class LeakedObject:
    pass


leaked = weakref.WeakSet()
app = Sanic(__name__)


@app.route("/slow")
async def slow_handler(request):
    lo = LeakedObject()
    leaked.add(lo)
    await asyncio.sleep(2)
    return response.text('OK')


@app.route("/fast")
async def fast_handler(request):
    lo = LeakedObject()
    leaked.add(lo)
    return response.text('OK')


app.config.RESPONSE_TIMEOUT = 1


def test_cli(method, url, **kwargs):
    results = [None, None]

    @app.listener('after_server_start')
    async def _collect_response(sanic, loop):
        print(loop)
        results[0] = await app.test_client._local_request(method, url)
        # at this point the request is done leaked should no longer have a
        # weakref to LeakedObject
        await asyncio.sleep(1)  # just making sure theres no pending cleanup tasks
        results[1] = list(leaked)
        app.stop()

    app.run(
        host='127.0.0.1',
        port=app.test_client.port,
        auto_reload=False,
        **kwargs
    )
    app.listeners['after_server_start'].pop()
    return results


# this works
def test_completed_request_cleaned_up(**kwargs):
    resp, references_leaked = test_cli('get', '/fast', **kwargs)
    assert resp.status == 200
    assert resp.body == b'OK'
    assert references_leaked == []


# this does not
def test_timed_out_request_cleaned_up(**kwargs):
    resp, references_leaked = test_cli('get', '/slow', **kwargs)
    assert resp.status == 503
    assert resp.body == b'Error: Response Timeout'
    assert references_leaked == []  # <<< fails here


if __name__ == '__main__':
    # test_completed_request_cleaned_up()
    test_timed_out_request_cleaned_up()
    test_timed_out_request_cleaned_up(debug=True)
