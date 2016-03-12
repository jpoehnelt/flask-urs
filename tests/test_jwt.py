# -*- coding: utf-8 -*-
"""
    tests.test_jwt
    ~~~~~~~~~~~~~~

    Flask-URS-JWT tests
"""
import time

from itsdangerous import TimedJSONWebSignatureSerializer

from flask import Flask, json, jsonify

import responses

import pytest

import flask_urs


def post_json(client, url, data):
    resp = client.post(
        url,
        headers={'content-type': 'application/json'},
        data=json.dumps(data)
    )
    return resp, json.loads(resp.data)


def assert_error_response(r, code, msg, desc):
    assert r.data is not None
    try:
        jdata = json.loads(r.data)
    except:
        print(r.data)
        return
    assert r.status_code == code
    assert jdata['status_code'] == code
    assert jdata['error'] == msg
    assert jdata['description'] == desc


def test_initialize():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'super-secret'
    urs = flask_urs.URS(app)
    assert isinstance(urs, flask_urs.URS)
    assert len(app.url_map._rules) == 2


def test_jwt_required_decorator_with_valid_token(urs, client, user):
    token = urs.encode_callback(user)
    resp = client.get(
        '/protected',
        headers={'authorization': 'Bearer ' + token})
    assert resp.status_code == 200
    assert resp.data == b'success'


def test_jwt_required_decorator_with_valid_request_current_user(urs, client, user):
    with client as c:
        token = urs.encode_callback(user)
        c.get(
            '/protected',
            headers={'authorization': 'Bearer ' + token})
        assert flask_urs.current_user


def test_jwt_required_decorator_with_invalid_request_current_user(app, client):
    with client as c:
        c.get(
            '/protected',
            headers={'authorization': 'Bearer bogus'})
        assert not flask_urs.current_user


def test_jwt_required_decorator_with_invalid_authorization_headers(client):
    # Missing authorization header
    r = client.get('/protected')
    assert_error_response(r, 401, 'Authorization Required', 'Authorization header was missing')
    assert r.headers['WWW-Authenticate'] == 'JWT realm="Login Required"'

    # Not a bearer token
    r = client.get('/protected', headers={'authorization': 'Bogus xxx'})
    assert_error_response(r, 400, 'Invalid JWT header', 'Unsupported authorization type')

    # Missing token
    r = client.get('/protected', headers={'authorization': 'Bearer'})
    assert_error_response(r, 400, 'Invalid JWT header', 'Token missing')

    # Token with spaces
    r = client.get('/protected', headers={'authorization': 'Bearer xxx xxx'})
    assert_error_response(r, 400, 'Invalid JWT header', 'Token contains spaces')


def test_jwt_required_decorator_with_invalid_jwt_tokens(client, user, urs):
    token = urs.encode_callback(user)

    # Undecipherable
    r = client.get('/protected', headers={'authorization': 'Bearer %sX' % token})
    assert_error_response(r, 400, 'Invalid JWT', 'Token is undecipherable')

    # Expired
    time.sleep(1)
    r = client.get('/protected', headers={'authorization': 'Bearer ' + token})
    assert_error_response(r, 400, 'Invalid JWT', 'Token is expired')


def test_jwt_required_decorator_with_missing_user(urs, client, user):
    token = urs.encode_callback(user)

    @urs.user_handler
    def load_user(payload):
        return None

    r = client.get('/protected', headers={'authorization': 'Bearer %s' % token})
    assert_error_response(r, 400, 'Invalid JWT', 'User does not exist')


@responses.activate
@pytest.mark.usefixtures("fake_oauth_success")
def test_custom_response_handler(app, client, urs, user):
    @urs.response_handler
    def response_callback(user, jwt, access):
        return jsonify({"jwt": jwt})

    r = client.get(
        app.config.get("URS_URL_PREFIX") + app.config.get("URS_CALLBACK_RULE") + "?code=x")

    assert r.status_code == 200
    assert "jwt" in json.loads(r.data)


def test_default_encode_handler(user, app, urs):
    token = urs.encode_callback(user)

    serializer = TimedJSONWebSignatureSerializer(
        secret_key=app.config['JWT_SECRET_KEY']
    )
    decoded = serializer.loads(token)
    assert decoded['email_address'] == user['email_address']


def test_custom_encode_handler(urs, user, app):
    serializer = TimedJSONWebSignatureSerializer(
        app.config['JWT_SECRET_KEY'],
        algorithm_name=app.config['JWT_ALGORITHM']
    )

    @urs.encode_handler
    def encode_data(payload):
        return serializer.dumps({'foo': 42}).decode('utf-8')

    token = urs.encode_callback(user)

    decoded = serializer.loads(token)
    assert decoded == {'foo': 42}


def test_custom_decode_handler(client, user, urs):
    @urs.decode_handler
    def decode_data(data):
        return {'user_id': user['uid']}

    with client as c:
        token = urs.encode_callback(user)

        c.get(
            '/protected',
            headers={'authorization': 'Bearer ' + token})
        assert flask_urs.current_user == decode_data(user)


def test_custom_payload_handler(client, urs, user):
    @urs.user_handler
    def load_user(payload):
        if payload['uid'] == user['uid']:
            return user

    @urs.payload_handler
    def make_payload(u):
        return {
            'id': u['uid']
        }

    with client as c:
        token = urs.encode_callback(user)

        c.get(
            '/protected',
            headers={'authorization': 'Bearer ' + token})
        assert flask_urs.current_user == user
