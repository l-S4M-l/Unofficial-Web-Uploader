import multiprocessing as mp
import webbrowser
import urllib.parse
from components.oauth_server import run_oauth_server
import time
import requests
import base64

mp.set_start_method('spawn', force=True)


class GithubHandler:
    def __init__(self, token = None):

        self.token = token
        self.username = ""

        self.headers = {
        "Authorization": f"token {self.token}",
        "Accept": "application/vnd.github+json",
        }

    def create_repo(self, repo_name, private=False):
        url = "https://api.github.com/user/repos"
        data = {
            "name": repo_name,
            "description": "Created via API",
            "private": private,
            "auto_init": False
        }
        response = requests.post(url, json=data, headers=self.headers)
        if response.status_code == 201:
            print(f"Repo '{repo_name}' created successfully.")
            return True
        if response.status_code == 422:
            print(f"{repo_name} repo already exists")
        else:
            print("Error creating repo:", response.json())
            return False
        
    def upload_file(self, repo_name, path, content_bytes, commit_msg="Add file"):
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/contents/{path}"
        encoded_content = base64.b64encode(content_bytes).decode()
        data = {
            "message": commit_msg,
            "content": encoded_content
        }
        response = requests.put(url, json=data, headers=self.headers)
        if response.status_code in [201, 200]:
            print(f"File '{path}' uploaded successfully.")

            return response.json()["content"]["download_url"]

        elif response.status_code == 422:
            print(f"{path} already exists")
        else:
            print("Error uploading file:", response.json())

    def check_github_login(self, token):
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json"
        }
        response = requests.get("https://api.github.com/user", headers=headers)
        if response.status_code == 200:
            user = response.json()
            print(f"Logged in as {user['login']}")
            return user['login'], True
        else:
            print("Invalid token or unauthorized:", response.status_code, response.text)
            return None, False
        
    def delete_repo(self, repo_name):
        """
        Delete a repository by its name.
        """
        url = f"https://api.github.com/repos/{self.username}/{repo_name}"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 204:
            print(f"Repo '{repo_name}' deleted successfully.")
            return True
        else:
            print(f"Error deleting repo '{repo_name}':", response.status_code, response.text)
            return False

    def list_repos(self):
        """
        List all repositories for the authenticated user.
        """
        url = "https://api.github.com/user/repos"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            repos = response.json()
            repo_names = [repo['name'] for repo in repos]
            return repo_names
        else:
            print("Error listing repos:", response.status_code, response.text)
            return []

if __name__ == "__main__":
    gh = GithubHandler()
    gh.login_with_github()

    a = gh.list_repos()
    print(a)