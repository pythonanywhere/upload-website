import os
import pathlib
import sys
from urllib.parse import urljoin

import requests


MY_DIR = os.path.dirname(os.path.abspath(__file__))
WSGI_FILE_TEMPLATE = """
import sys

project_home = {project_home!r}
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

from flask_app import app as application  # noqa
"""




def main():
    username = input("Please enter the PythonAnywhere username: ")
    api_token = input("Please enter the API token: ")

    region = None
    while region not in ("eu", "www"):
        region = input("Please enter the region (eu or www): ")

    base_api_url = f"https://{region}.pythonanywhere.com/api/v0/user/{username}/"

    if region == "eu":
        site_hostname = f"{username}.eu.pythonanywhere.com"
    else:
        site_hostname = f"{username}.pythonanywhere.com"

    project_home = f"/home/{username}/mysite/"

    webapps_url = urljoin(base_api_url, "webapps/")
    print(f"Checking if website already exists with GET from {webapps_url}")
    resp = requests.get(
        webapps_url,
        headers={"Authorization": f"Token {api_token}"}
    )
    if resp.status_code != 200:
        print(f"Error getting website list: status was {resp.status_code}\n{resp.content}")
        sys.exit(-1)

    sites = [site["domain_name"] for site in resp.json()]
    print(f"Found these sites: {sites}")
    if site_hostname not in sites:
        print(f"Creating website at {site_hostname} with POST to {webapps_url}")
        resp = requests.post(
            webapps_url,
            data={
                "domain_name": site_hostname,
                "python_version": "python37",
            },
            headers={"Authorization": f"Token {api_token}"}
        )
        if resp.status_code not in (200, 201):
            print(f"Error creating site: status was {resp.status_code}\n{resp.content}")
            sys.exit(-1)

    paths_to_upload = [
        "src/flask_app.py",
        "src/static/style.css",
        "src/templates/index.html"
    ]
    file_upload_url = urljoin(base_api_url, f"files/path")
    for path in paths_to_upload:
        print(f"Reading {path}")
        with open(os.path.join(MY_DIR, path)) as f:
            content = f.read()

        relative_path = str(pathlib.Path(*pathlib.Path(path).parts[1:]))
        remote_path = f"{project_home}/{relative_path}"
        upload_url = file_upload_url + remote_path
        print(f"Uploading {path} via {upload_url}")
        resp = requests.post(
            upload_url,
            files={"content": content},
            headers={"Authorization": f"Token {api_token}"}
        )
        if resp.status_code not in (200, 201):
            print(f"Error uploading {path}: status was {resp.status_code}\n{resp.content}")
            sys.exit(-1)

    wsgi_file_filename = site_hostname.replace(".", "_").lower() + "_wsgi.py"
    wsgi_file_remote_path = f"/var/www/{wsgi_file_filename}"
    wsgi_file_upload_url = file_upload_url + wsgi_file_remote_path
    wsgi_file_content = WSGI_FILE_TEMPLATE.format(project_home=project_home)
    print(f"Uploading WSGI file via {wsgi_file_upload_url}")
    resp = requests.post(
        wsgi_file_upload_url,
        files={"content": wsgi_file_content},
        headers={"Authorization": f"Token {api_token}"}
    )
    if resp.status_code not in (200, 201):
        print(f"Error uploading WSGI file: status was {resp.status_code}\n{resp.content}")
        sys.exit(-1)


    our_webapp_url = urljoin(webapps_url, f"{site_hostname}/")
    static_file_route_url = urljoin(our_webapp_url, "static_files/")
    print(f"Configuring static file route with post to {static_file_route_url}")
    resp = requests.post(
        static_file_route_url,
        data={
            "url": "/static",
            "path": f"{project_home}/static",
        },
        headers={"Authorization": f"Token {api_token}"}
    )
    if resp.status_code not in (200, 201):
        print(f"Error creating static file route: status was {resp.status_code}\n{resp.content}")
        sys.exit(-1)

    reload_website_url = urljoin(our_webapp_url, "reload/")
    print(f"Reloading website with post to {reload_website_url}")
    resp = requests.post(
        reload_website_url,
        headers={"Authorization": f"Token {api_token}"}
    )
    if resp.status_code not in (200, 201):
        print(f"Error reloading website: status was {resp.status_code}\n{resp.content}")
        sys.exit(-1)

    site_url = f"https://{site_hostname}/"
    print(f"All done!  The site is now live at {site_url}")




if __name__ == "__main__":
    main()