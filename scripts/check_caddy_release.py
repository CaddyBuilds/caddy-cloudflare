import os
import json
import requests
import sys

def get_latest_caddy_release():
    try:
        response = requests.get('https://api.github.com/repos/caddyserver/caddy/releases/latest')
        response.raise_for_status()
        release = response.json()
        return release['tag_name']
    except requests.RequestException as e:
        print(f"Error fetching latest release: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    latest_version = get_latest_caddy_release()
    version_file = 'version.json'
    
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            data = json.load(f)
            current_version = data.get('version', 'none')
    else:
        current_version = 'none'

    print(f"Latest version: {latest_version}")
    print(f"Current version: {current_version}")

    if latest_version != current_version:
        with open(os.getenv('GITHUB_ENV'), 'a') as env_file:
            env_file.write(f'IS_NEW_RELEASE=true\n')
            env_file.write(f'LATEST_VERSION={latest_version}\n')
    else:
        with open(os.getenv('GITHUB_ENV'), 'a') as env_file:
            env_file.write(f'IS_NEW_RELEASE=false\n')

if __name__ == "__main__":
    main()