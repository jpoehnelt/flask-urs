Flask-URS-JWT
=========

.. currentmodule:: flask_urs_jwt

Add basic JWT features to your `Flask`_ application based upon NASA EarthData(URS) Oauth2.


Links
-----

* `documentation <http://packages.python.org/Flask-URS-JWT/>`_
* `source <http://github.com/justinwp/flask-urs-jwt>`_
* :doc:`changelog </changelog>`


Installation
------------

Install with **pip** or **easy_install**::

    pip install Flask-URS-JWT

or download the latest version from version control::

    git clone https://github.com/justinwp/flask-urs-jwt.git ./flask-urs-jwt
    pip install ./flask-urs-jwt


Quickstart
----------

Minimum viable application configuration:

.. code-block:: python

    from flask import Flask, render_template, request, jsonify
    from flask_urs_jwt import URS, URSError


    app = Flask(__name__)
    app.debug = True
    app.config['SECRET_KEY'] = 'super-secret'


    app.config['URS_CLIENT_ID'] = 'p-eoBHhkaGOvVjP-vSYC4w&'
    app.config['URS_UID'] = 'gfsad30_test'
    app.config['URS_PASSWORD'] = 'xEEoS1IyCdc8HaBVzfv6mD_X'

    urs = URS(app)

    @app.route('/')
    def protected():
        redirect_uri = request.base_url[:-1] + urs.redirect_url_rule
        return render_template('urs.html', client_id=app.config.get('URS_CLIENT_ID'),
                               redirect_uri=redirect_uri)

    @urs.response_handler
    def callback(jwt, access):
        return render_template('custom_callback.html', jwt=jwt)

    @urs.payload_handler
    def callback(user):
        user.update({'custom_data': 'asdfasdfasdfsdfsd'})
        return user

    @app.errorhandler(URSError)
    def handle_invalid_usage(error):
        response = jsonify(error.__dict__)
        response.status_code = error.status_code
        return response

    if __name__ == '__main__':
        app.run()



This token can then be used to make requests against protected endpoints::

    GET /protected HTTP/1.1
    Authorization: JWT eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZGVudGl0eSI6MSwiaWF0IjoxNDQ0OTE3NjQwLCJuYmYiOjE0NDQ5MTc2NDAsImV4cCI6MTQ0NDkxNzk0MH0.KPmI6WSjRjlpzecPvs3q_T3cJQvAgJvaQAPtk1abC_E


Within a function decorated by `jwt_required()`, you can use the
`current_user` proxy to access the user whose token was passed into this
request context.

.. _Flask: http://flask.pocoo.org
.. _GitHub: http://github.com/justinwp/flask-urs-jwt
