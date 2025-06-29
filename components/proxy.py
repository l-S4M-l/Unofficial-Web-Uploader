from flask import Flask, Response, request
import requests

app = Flask(__name__)

@app.route('/<user>/<repo>/<branch>/<path:filename>')
def github_proxy(user, repo, branch, filename):
    # Construct the GitHub raw URL
    raw_url = f'https://raw.githubusercontent.com/{user}/{repo}/{branch}/{filename}'

    # Fetch the file
    resp = requests.get(raw_url, stream=True)

    # Forward status code and headers
    headers = {
        'Content-Type': resp.headers.get('Content-Type', 'application/octet-stream'),
        'Content-Length': resp.headers.get('Content-Length', None),
    }

    return Response(resp.content, status=resp.status_code, headers=headers)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=80)
