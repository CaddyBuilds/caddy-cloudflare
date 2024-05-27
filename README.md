
# Caddy Cloudflare
> A fully integrated Caddy Docker image featuring Cloudflare DNS-01 ACME validation

Deploy a hassle-free Caddy server with built-in support for Cloudflare DNS-01 ACME challenges. Streamline your SSL certificate management and ensure your server stays secure without manual updates, making it an effortless and reliable solution.


## Table of Contents

- [Features](#features)
- [Usage](#usage)
  - [Using the Pre-built Docker Image](#using-the-pre-built-docker-image)
  - [Building Your Own Docker Image](#building-your-own-docker-image)
  - [Sample Caddyfile](#sample-caddyfile)
- [Configuration](#configuration)
  - [ACME DNS Challenge Configuration](#acme-dns-challenge-configuration)
  - [Creating a Cloudflare API Token](#creating-a-cloudflare-api-token)
- [Platform Support](#platform-support)
  - [Raspberry Pi](#raspberry-pi-support)
- [Tags](#tags)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Automated Builds**: Automatically checks for new Caddy releases and builds Docker images.
- **Continuous Integration**: Utilizes GitHub Actions for seamless CI/CD.
- **Cloudflare DNS Integration**: Integrates Cloudflare DNS for automatic SSL certificate management.
- **Multi-Platform Support**: Builds images for multiple architectures, including amd64, arm64, and arm/v7 (Raspberry Pi), ensuring compatibility across a wide range of devices and systems.
- **Manual Trigger**: Allows manual triggering of the build process.
- **Open Source**: Contributions are welcome under the MIT License.

## Usage

### Using the Pre-built Docker Image

To use the pre-built Docker image, pull it from the GitHub Container Registry:

```sh
docker pull ghcr.io/cyberverse-dev/caddy-cloudflare-docker:latest
```
You can use the image in your Docker setup. Here is an example `docker-compose.yml` file:
```yaml
version: '3.8'

services:
  caddy:
    image: ghcr.io/cyberverse-dev/caddy-cloudflare-docker:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    environment:
      - CLOUDFLARE_API_TOKEN=your_cloudflare_api_token
```
Replace `your_cloudflare_api_token` with your actual Cloudflare API token.

## Sample Caddyfile
Here is a sample Caddyfile configuration to get you started. This configuration sets up the ACME DNS challenge provider to use Cloudflare and serves a simple static site.

### Global Configuration (Use DNS Challenge for All Sites)
In this configuration, the ACME DNS challenge provider is set globally, so it applies to all sites served by Caddy.

```
# To use your own domain name (with automatic HTTPS), first make
# sure your domain's A/AAAA DNS records are properly pointed to
# this machine's public IP, then replace "example.com" below with your
# domain name.

{
  # Set the ACME DNS challenge provider to use Cloudflare for all sites
  acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}
}

example.com {

    # Set this path to your site's directory.
	root * /usr/share/caddy

	# Enable the static file server.
	file_server

	# Another common task is to set up a reverse proxy:
	# reverse_proxy localhost:8080

	# Or serve a PHP site through php-fpm:
	# php_fastcgi localhost:9000

    encode gzip

    tls {
      # No need to specify dns here, it's already set globally
    }
}

another-example.com {
    root * /usr/share/caddy
    file_server
    encode gzip

    tls {
        # No need to specify dns here, it's already set globally
    }
}
```
### Per-site Configuration
```
example.com {
  
    # Set this path to your site's directory.
	root * /usr/share/caddy

	# Enable the static file server.
	file_server

	# Another common task is to set up a reverse proxy:
	# reverse_proxy localhost:8080

	# Or serve a PHP site through php-fpm:
	# php_fastcgi localhost:9000
    encode gzip

    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
}

another-example.com {
    root * /usr/share/caddy
    file_server
    encode gzip

    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
}
```

## Configuration
### Creating a Cloudflare API Token

To use the Cloudflare DNS challenge provider, you'll need to create an API token in your Cloudflare account. Follow these steps to create a token with the necessary permissions:

1. **Log in to Cloudflare**:
   - Go to the Cloudflare dashboard at [dash.cloudflare.com](https://dash.cloudflare.com) and log in with your account credentials.

2. **Navigate to API Tokens**:
   - Click on your profile icon in the top right corner of the dashboard.
   - Select "My Profile" from the dropdown menu.
   - In the left sidebar, click on "API Tokens".

3. **Create a Custom Token**:
   - Click the "Create Token" button.
   - Under the "Custom Token" section, click "Get started".

4. **Configure Token Permissions**:
   - Give your token a name, such as "Caddy DNS-01 Challenge".
   - Set the permissions as follows:
     - **Zone - Zone - Read**: Allows the token to Read DNS Zones
     - **Zone - DNS - Edit**: Allows the token to edit DNS records, which is required for the DNS-01 challenge.

5. **Specify Account and Zone Resources**:
   - Under "Zone Resources", set the following:
     - **Include - All Zones**: If you want the token to work with all your zones.
     - **Include - Specific Zone**: Select the specific zone(s) you want the token to have access to.

6. **Create and Store the Token**:
   - Click the "Continue to summary" button.
   - Review your token settings and click "Create Token".
   - Copy the generated token and store it in a secure place. You will need this token to set up the environment variable in your Caddy configuration.

7. **Set the Environment Variable**:
   - In your deployment environment, set the environment variable `CLOUDFLARE_API_TOKEN` to the value of the token you just created.

For example, in a Docker environment, you can set this environment variable in your `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  caddy:
    image: ghcr.io/cyberverse-dev/caddy-cloudflare-docker:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    environment:
      - CLOUDFLARE_API_TOKEN=your_cloudflare_api_token
```

Replace `your_cloudflare_api_token` with the actual token you generated.

By following these steps, you'll have a Cloudflare API token configured with the necessary permissions to allow Caddy to manage DNS records for the DNS-01 ACME challenge.

### ACME DNS Challenge Configuration
To configure the [ACME DNS challenge](https://caddyserver.com/docs/automatic-https#dns-challenge) provider for all ACME transactions, add the following to your Caddyfile:
```
{
   acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}
}
```
This configuration sets up the provider to use the Cloudflare DNS module with the API token provided as an environment variable. It ensures that your Caddy server can automatically issue and renew SSL certificates using DNS-01 challenges via Cloudflare.

This setup is the same as specifying the provider in the [tls directive's ACME issuer](https://caddyserver.com/docs/caddyfile/directives/tls#acme) configuration.


## Tags

The [caddy-cloudflare-docker](https://github.com/cyberverse-dev/caddy-cloudflare-docker/pkgs/container/caddy-cloudflare-docker) image on GitHub Container Registry provides the following tags:

- **`latest`**: 
  - Always points to the most recent stable release of Caddy with the Cloudflare DNS module.
  - Automatically updated to ensure you have the latest features and improvements.

- **`<version>`**:
  - Specific version tags for precise version control and consistency in deployments.
  - Examples include:
    - **`2.7.6`**: Full version tag for Caddy version 2.7.6, ensuring you are using this exact release. 
    
         (eg: ```docker pull ghcr.io/cyberverse-dev/caddy-cloudflare-docker:v2.7.6``` )
    - **`2.7`**: Minor version tag for the latest patch release within the 2.7 series, allowing for minor updates without breaking changes.
    - **`2`**: Major version tag for the latest release within the 2.x series, providing updates within the major version while maintaining compatibility.

## Platform Support

The `cyberverse-dev/caddy-cloudflare-docker` image is built to support multiple platforms, ensuring compatibility across a wide range of devices and systems. The supported platforms include:

- **linux/amd64**: Standard x86_64 architecture, commonly used in desktop and server environments.
- **linux/arm64**: ARM 64-bit architecture, used in many modern servers and high-end ARM devices.
- **linux/arm/v7**: ARM 32-bit architecture, widely used in devices like Raspberry Pi.

### Raspberry Pi Support

This Docker image is optimized for Raspberry Pi, allowing you to deploy Caddy with Cloudflare DNS integration on these popular single-board computers. Whether you are using a Raspberry Pi 3 or the latest Raspberry Pi 4, this image provides the necessary support for seamless operation.

To use the image on a Raspberry Pi, ensure you are running a compatible operating system (such as Raspberry Pi OS) and have Docker installed. You can then pull the image and run it as you would on any other system:

```sh
docker pull ghcr.io/cyberverse-dev/caddy-cloudflare-docker:latest
```
# Building Your Own Docker Image
If you prefer to build your own Docker image, follow these steps:

## Prerequisites

- GitHub account
- DockerHub account (if you wish to push the image to DockerHub as well)
- GitHub Secrets configured:
  - `GITHUB_TOKEN` (automatically available in GitHub Actions)
  - `DOCKERHUB_USERNAME` (optional, if you want to push to DockerHub)
  - `DOCKERHUB_TOKEN` (optional, if you want to push to DockerHub)

## Setup Instructions

1. **Fork this repository** to your GitHub account.

2. **Clone the forked repository** to your local machine:
   ```sh
   git clone https://github.com/cyberverse-dev/caddy-cloudflare-docker.git
   cd caddy-cloudflare-docker
   ```

3. **Set up GitHub Secrets**:
   - Go to your repository on GitHub.
   - Navigate to `Settings` > `Secrets and variables` > `Actions`.
   - Add the following secrets:
     - `GITHUB_TOKEN`: This is automatically available in GitHub Actions.
     - `DOCKERHUB_USERNAME`: Your DockerHub username (optional).
     - `DOCKERHUB_TOKEN`: Your DockerHub access token (optional).

4. **Customize the workflow** (if needed):
   - The workflow file `.github/workflows/check-caddy-release.yml` is configured to check for new Caddy releases and build the Docker image. You can customize the schedule or any other part of the workflow as needed.

5. **Commit and push any changes** (if you made customizations):
   ```sh
   git add .
   git commit -m "Customize workflow"
   git push origin main
   ```

6. **Manually trigger the workflow** (optional):
   - Go to the `Actions` tab in your GitHub repository.
   - Select the `Check Caddy Releases and Build Docker Image` workflow.
   - Click the `Run workflow` button to trigger the build process manually.

7. **Monitor the workflow**:
   - You can monitor the progress and logs of the workflow in the `Actions` tab of your GitHub repository.

8. **Docker image**:
   - Once the workflow completes successfully, the Docker image will be available in the GitHub Container Registry under your repository.
   - You can pull the image using:
     ```sh
     docker pull ghcr.io/YOUR_GITHUB_USERNAME/caddy-cloudflare-docker:latest
     ```

## Usage

You can use the built Docker image in your projects. Here is an example of how to use it in a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  caddy:
    image: ghcr.io/YOUR_GITHUB_USERNAME/caddy-cloudflare-docker:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
    environment:
      - CLOUDFLARE_API_TOKEN=your_cloudflare_api_token
```
Replace `YOUR_GITHUB_USERNAME` with your GitHub username and `your_cloudflare_api_token` with your actual Cloudflare API token.

## Contributing

Feel free to open issues or submit pull requests if you have any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.