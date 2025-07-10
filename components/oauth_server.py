# oauth_server.py
from flask import Flask, request
import requests
import sys
import time
from components.env import env_class

def run_oauth_server(Q):
    app = Flask(__name__)
    REDIRECT_URI = "http://localhost:8000/callback"

    print("Starting OAuth server...")

    @app.route("/callback")
    def callback():
        print("Callback route hit!")

        code = request.args.get("code")
        if not code:
            return "Missing code", 400

        # Exchange code for token
        token_url = "https://github.com/login/oauth/access_token"
        headers = {'Accept': 'application/json'}
        data = {
            "client_id": "Ov23liIjsHpUC27r5Xe2",
            "client_secret": env_class().github_secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }

        print("Exchanging code for token...")
        r = requests.post(token_url, headers=headers, data=data)
        token = r.json().get("access_token")

        print(token)

        Q.put(token)
        return "GitHub login successful. You can close this tab."

    app.run(port=8000, debug=False, use_reloader=False)



if __name__ == "__main__":
    from multiprocessing import Queue, Process

    CLIENT_ID = "Ov23liIjsHpUC27r5Xe2"

    Q = Queue()
    p = Process(target=run_oauth_server, args=(Q,))
    p.start()
    code = Q.get(block=True)

    print(code)
    time.sleep(1)
    p.terminate()

    print("Please visit the following URL to login with GitHub:")