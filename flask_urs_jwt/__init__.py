# -*- coding: utf-8 -*-
"""
    flask_urs_urs
    ~~~~~~~~~

    Flask-URS-JWT module
"""

from flask import current_app, render_template, Blueprint, request, jsonify

from flask import _app_ctx_stack as stack
from itsdangerous import (
    TimedJSONWebSignatureSerializer,
    SignatureExpired,
    BadSignature
)
from functools import wraps
from werkzeug.local import LocalProxy
import requests
from datetime import timedelta
from collections import OrderedDict

__version__ = '0.1.0'

current_user = LocalProxy(lambda: getattr(stack.top, 'current_user', None))

_urs = LocalProxy(lambda: current_app.extensions['urs_jwt'])

CONFIG_DEFAULTS = {
    'URS_CALLBACK_RULE': '/callback',
    'URS_URL_PREFIX': '/urs',
    'URS_CALLBACK_TEMPLATE': 'urs_jwt/callback.html',
    'JWT_EXPIRATION_DELTA': 3600,
    'JWT_EXPIRATION_LEEWAY': 100,
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_ALGORITHM': 'HS256',
    'JWT_DEFAULT_REALM': 'Login Required',
    'URS_HOST': 'https://urs.earthdata.nasa.gov/',
    'URS_TOKEN_PATH': 'oauth/token'
}


def _get_serializer():
    expires_in = current_app.config['JWT_EXPIRATION_DELTA']
    leeway = current_app.config['JWT_EXPIRATION_LEEWAY']
    if isinstance(expires_in, timedelta):
        expires_in = int(expires_in.total_seconds())
    if isinstance(leeway, timedelta):
        leeway = int(leeway.total_seconds())
    expires_in_total = expires_in + leeway
    return TimedJSONWebSignatureSerializer(
        secret_key=current_app.config['JWT_SECRET_KEY'],
        expires_in=expires_in_total,
        algorithm_name=current_app.config['JWT_ALGORITHM']
    )


def jwt_required(realm=None):
    """View decorator that requires a valid JWT token to be present in the request

    :param realm: an optional realm
    """

    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_urs(realm)
            return fn(*args, **kwargs)

        return decorator

    return wrapper


class JWTError(Exception):
    def __init__(self, error, description, status_code=400, headers=None):
        self.error = error
        self.description = description
        self.status_code = status_code
        self.headers = headers


class URSError(Exception):
    def __init__(self, error, description, status_code=400, headers=None):
        self.error = error
        self.description = description
        self.status_code = status_code
        self.headers = headers


def verify_urs(realm=None):
    """Does the actual work of verifying the JWT data in the current request.
    This is done automatically for you by `jwt_required()` but you could call it manually.
    Doing so would be useful in the context of optional JWT access in your APIs.

    :param realm: an optional realm
    """
    realm = realm or current_app.config['JWT_DEFAULT_REALM']
    auth = request.headers.get('Authorization', None)

    if auth is None:
        raise JWTError('Authorization Required', 'Authorization header was missing', 401, {
            'WWW-Authenticate': 'JWT realm="%s"' % realm
        })

    parts = auth.split()

    if parts[0].lower() != 'bearer':
        raise JWTError('Invalid JWT header', 'Unsupported authorization type')
    elif len(parts) == 1:
        raise JWTError('Invalid JWT header', 'Token missing')
    elif len(parts) > 2:
        raise JWTError('Invalid JWT header', 'Token contains spaces')

    try:
        handler = _urs.decode_callback
        payload = handler(parts[1])
    except SignatureExpired:
        raise JWTError('Invalid JWT', 'Token is expired')
    except BadSignature:
        raise JWTError('Invalid JWT', 'Token is undecipherable')

    stack.top.current_user = user = _urs.user_callback(payload)

    if user is None:
        raise JWTError('Invalid JWT', 'User does not exist')


def _default_payload_handler(user):
    return user


def _default_user_handler(payload):
    return payload


def _default_encode_handler(payload):
    """Return the encoded payload."""
    return _get_serializer().dumps(payload).decode('utf-8')


def _default_decode_handler(token):
    """Return the decoded token."""
    try:
        result = _get_serializer().loads(token)
    except SignatureExpired:
        if current_app.config['JWT_VERIFY_EXPIRATION']:
            raise
    return result


def _default_jwt_error_handler(error):
    return jsonify(OrderedDict([
        ('status_code', error.status_code),
        ('error', error.error),
        ('description', error.description),
    ])), error.status_code, error.headers


def _default_response_handler(jwt, access):
    return render_template(CONFIG_DEFAULTS.get('URS_CALLBACK_TEMPLATE'), jwt=jwt)


class URS(object):
    def __init__(self, app=None):
        self.user_callback = _default_user_handler
        self.response_callback = _default_response_handler
        self.encode_callback = _default_encode_handler
        self.decode_callback = _default_decode_handler
        self.payload_callback = _default_payload_handler
        self.jwt_error_callback = _default_jwt_error_handler

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        for k, v in CONFIG_DEFAULTS.items():
            app.config.setdefault(k, v)

        app.config.setdefault('JWT_SECRET_KEY', app.config['SECRET_KEY'])

        bp = Blueprint('urs_urs', __name__, template_folder='templates')
        bp.url_prefix = app.config.get('URS_URL_PREFIX', '')
        bp.add_url_rule(app.config.get('URS_CALLBACK_RULE'), methods=['GET'],
                        view_func=self.callback)

        app.register_blueprint(bp)

        if not hasattr(app, 'extensions'):  # pragma: no cover
            app.extensions = {}

        app.errorhandler(JWTError)(self.jwt_error_callback)

        app.extensions['urs_jwt'] = self

    @property
    def redirect_url_rule(self):
        return current_app.config.get('URS_URL_PREFIX') + current_app.config.get(
            'URS_CALLBACK_RULE')

    @property
    def _token_url(self):
        return current_app.config.get('URS_HOST', CONFIG_DEFAULTS['URS_HOST']) \
               + current_app.config.get('URS_TOKEN_PATH', CONFIG_DEFAULTS['URS_TOKEN_PATH'])

    def callback(self):
        code = request.args.get('code', None)
        if code is None:
            raise Exception

        access = self.get_token(code)
        user = self.get_user(access['access_token'], access['endpoint'])
        payload = self.payload_callback(user)
        jwt = self.encode_callback(payload)

        return self.response_callback(jwt, access)

    def refresh(self, refresh_token):
        """
        Get new access token...
        :param refresh_token:
        :return:
        """

        # TODO

        pass

    def get_user(self, token, endpoint, refresh_token=None):
        headers = {
            "Authorization": "Bearer %s" % token
        }

        r = requests.get(current_app.config.get('URS_HOST') + endpoint, headers=headers)

        if r.status_code != 200:
            raise URSError('Invalid Code', 'No Authorization Code')

        return r.json()

    def get_token(self, code):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": request.base_url
        }

        auth = requests.auth.HTTPBasicAuth(current_app.config.get('URS_UID'),
                                           current_app.config.get('URS_PASSWORD'))

        r = requests.post(self._token_url, headers=headers, data=data, auth=auth)

        if r.status_code == 401:
            raise URSError('Token Access Denied', 'Incorrect Application UID or Password',
                           status_code=500)

        elif r.status_code == 400:
            error = r.json()
            raise URSError(r.json()['error'], error['error_description'], status_code=500)

        elif r.status_code != 200:
            raise URSError('Unknown Error', 'Could Not Retrieve Access Token', status_code=500)

        return r.json()

    def response_handler(self, callback):
        """Specifies the response handler function. This function receives a
        JWT-encoded payload, the token payload and returns a Flask response.

        :param callable callback: the response handler function
        """
        self.response_callback = callback
        return callback

    def user_handler(self, callback):
        """Specifies the user handler function. This function receives the token payload as
        its only positional argument. It should return an object representing the current
        user. Example::

            @urs.user_handler
            def load_user(payload):
                if payload['user_id'] == 1:
                    return User(id=1, username='joe')

        :param callback: the user handler function
        """
        self.user_callback = callback
        return callback

    def error_handler(self, callback):
        """Specifies the error handler function. This function receives a URSError instance as
        its only positional argument. It can optionally return a response. Example::

            @urs.error_handler
            def error_handler(e):
                return "Something bad happened", 400

        :param callback: the error handler function
        """
        self.error_callback = callback
        return callback

    def encode_handler(self, callback):
        """Specifies the encoding handler function. This function receives a
        payload and signs it.

        :param callable callback: the encoding handler function
        """
        self.encode_callback = callback
        return callback

    def decode_handler(self, callback):
        """Specifies the decoding handler function. This function receives a
        signed payload and decodes it.

        :param callable callback: the decoding handler function
        """
        self.decode_callback = callback
        return callback

    def payload_handler(self, callback):
        """Specifies the payload handler function. This function receives a
        user object and returns a dictionary payload.

        Example::

            @urs.payload_handler
            def make_payload(user):
                return {
                    'user_id': user.id,
                    'exp': datetime.utcnow() + current_app.config['JWT_EXPIRATION_DELTA']
                }

        :param callable callback: the payload handler function
        """
        self.payload_callback = callback
        return callback

    def jwt_error_handler(self, callback):
        """Specifies the error handler function. Example::
            @urs.error_handler
            def error_handler(e):
                return "Something bad happened", 400
        :param callback: the error handler function
        """
        self.jwt_error_callback = callback
        return callback
