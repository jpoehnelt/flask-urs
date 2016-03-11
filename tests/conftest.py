# -*- coding: utf-8 -*-
"""
    tests.conftest
    ~~~~~~~~~~~~~~

    Test fixtures and what not
"""

from datetime import timedelta

import pytest

from flask import Flask, jsonify

import flask_urs

import responses


@pytest.fixture(scope='function')
def urs():
    return flask_urs.URS()


@pytest.fixture(scope='function')
def user():
    return {
        "email_address": "test@email.com",
        "uid": "username",
        "affiliation": "Government",
        "organization": "Somewhere",
        "first_name": "First",
        "last_name": "Last",
        "user_type": "Science Team",
        "country": "United States"
    }


@pytest.fixture(scope='function')
def app(urs, user):
    app = Flask(__name__)
    app.debug = True
    app.config['SECRET_KEY'] = 'super-secret'
    app.config['JWT_EXPIRATION_DELTA'] = timedelta(milliseconds=600)
    app.config['JWT_EXPIRATION_LEEWAY'] = timedelta(milliseconds=5)

    urs.init_app(app)

    @app.route('/protected')
    @flask_urs.jwt_required()
    def protected():
        return 'success'

    @app.route("/authorize")
    def authorize():
        return jsonify({
            "access_token": "asdf",
            "refresh_token": "asdf",
            "endpoint": "/endpoint"
        })

    @app.route("/endpoint")
    def endpoint():
        return jsonify(user)

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    return app


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def fake_oauth_success(urs, app, user):
    token_response = {"access_token": "asdf", "endpoint": "api/username"}

    responses.add(responses.POST, urs._token_url, json=token_response, status=200)

    responses.add(responses.GET, app.config.get("URS_HOST") + token_response["endpoint"],
                  json=user, status=200)
