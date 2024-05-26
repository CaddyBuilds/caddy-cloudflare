import os
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
    previous_version = os.getenv('PREVIOUS_VERSION', 'none')

    print(f"Latest version: {latest_version}")
    print(f"Previous version: {previous_version}")

    if latest_version != previous_version:
        print(f'::set-output name=new_release::true')
        print(f'::set-output name=version::{latest_version}')
        with open(os.getenv('GITHUB_ENV'), 'a') as env_file:
            env_file.write(f'NEW_VERSION={latest_version}\n')
    else:
        print('::set-output name=new_release::false')
        print(f'Latest version ({latest_version}) is the same as the previous version ({previous_version}).')

if __name__ == "__main__":
    main()