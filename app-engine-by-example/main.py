import datetime

import google.oauth2.id_token
from flask import Flask, render_template, request
from google.cloud import datastore
from google.auth.transport import requests
from google.oauth2 import service_account, id_token

app = Flask(__name__)
credentials = service_account.Credentials.from_service_account_file("gcp-creds.json")
datastore_client = datastore.Client(credentials=credentials)
firebase_request_adapter = requests.Request()


def store_time(email, dt):
    entity = datastore.Entity(key=datastore_client.key('User', email, 'visit'))
    entity.update({'timestamp': dt})
    datastore_client.put(entity)


def fetch_times(email, limit):
    ancestor_key = datastore_client.key('User', email)
    query = datastore_client.query(kind='visit', ancestor=ancestor_key)
    query.order = ['-timestamp']
    times = query.fetch(limit=limit)
    return times


@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    times = None

    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            store_time(claims['email'], datetime.datetime.now())
            times = fetch_times(claims['email'], 10)
        except ValueError as exc:
            error_message = str(exc)

    return render_template('index.html', user_data=claims, times=times, error_message=error_message)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
