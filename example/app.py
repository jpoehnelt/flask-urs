from flask import Flask, render_template, request, jsonify
from flask_urs_jwt import URS, URSError
import os

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'super-secret'
app.config['URS_CLIENT_ID'] = os.environ['URS_CLIENT_ID']
app.config['URS_UID'] = os.environ['URS_UID']
app.config['URS_PASSWORD'] = os.environ['URS_PASSWORD']

urs = URS(app)


@app.route('/')
def protected():
    redirect_uri = request.base_url[:-1] + urs.redirect_url_rule
    return render_template('urs.html', client_id=app.config.get('URS_CLIENT_ID'),
                           redirect_uri=redirect_uri)


@urs.response_handler
def response_callback(jwt, access):
    return render_template('custom_callback.html', jwt=jwt)


@urs.payload_handler
def payload_callback(user):
    user.update({'custom_data': 'asdfasdfasdfsdfsd'})
    return user


@app.errorhandler(URSError)
def handle_invalid_usage(error):
    response = jsonify(error.__dict__)
    response.status_code = error.status_code
    return response


if __name__ == '__main__':
    app.run()
