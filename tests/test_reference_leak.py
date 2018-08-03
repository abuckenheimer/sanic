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


# this works
def test_completed_request_cleaned_up():
    results = [None, None]

    @app.listener('after_server_start')
    async def _collect_response(sanic, loop):
        results[0] = await app.test_client._local_request('get', '/fast')
        # at this point the request is done leaked should no longer have a
        # weakref to LeakedObject
        results[1] = list(leaked)
        app.stop()

    app.run(host='127.0.0.1', debug=True, port=app.test_client.port)
    resp, references_leaked = results
    assert resp.status == 200
    assert resp.body == b'OK'
    assert references_leaked == []
    app.listeners['after_server_start'].pop()


# this does not
def test_timed_out_request_cleaned_up():
    results = [None, None]

    @app.listener('after_server_start')
    async def _collect_response(sanic, loop):
        results[0] = await app.test_client._local_request('get', '/slow')
        # at this point the request is done leaked should no longer have a
        # weakref to LeakedObject
        await asyncio.sleep(1)
        results[1] = list(leaked)
        app.stop()

    app.run(host='127.0.0.1', debug=True, port=app.test_client.port)
    resp, references_leaked = results
    assert resp.status == 503
    assert resp.body == b'Error: Response Timeout'
    assert references_leaked == []  # <<< fails here
    app.listeners['after_server_start'].pop()


if __name__ == '__main__':
    test_completed_request_cleaned_up()
    test_timed_out_request_cleaned_up()
    # app.run('0.0.0.0', port=8001)
