# Shogun - The boss of student labs

This project is designed for creating student labs using Docker and Nginx. It provides a convenient way to manage lab environments for students by creating, listing, and deleting student containers and lab configurations.

## Prerequisites:
1. Python (already installed)
2. Nginx

## Initial Installation:

1. Install pipenv:
   Open a terminal and run the following command to install pipenv:
   ```
   pip install pipenv
   ```

2. Set up pipenv:
   In the project directory, run the following command to install the required dependencies:
   ```
   pipenv install
   ```

3. Nginx configuration:
   Make sure Nginx is installed on your system. Update your nginx.conf file with the following content:
   ```
   worker_processes  1;

   events {
       worker_connections  1024;
   }

   http {
       include       mime.types;
       default_type  application/octet-stream;

       sendfile        on;
       keepalive_timeout  65;
       server_names_hash_bucket_size 64;

       # Include server blocks configuration for labs
       include shogun.conf;
   }
   ```
   
4. Setting up SSL with Nginx (Optional):

**Acquire an SSL Certificate (Self-Signed):**

If you need one, you can generate a self-signed certificate using the following command
(useful for testing and dev purposes):

```
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt
```

**Modify the Nginx Configuration:**

Environment Variables:

Adjust your `.env` file to include relevant SSL related variables:

```
USE_SSL=true  # or false, depending on whether you wish to use SSL
SSL_CERT_PATH=/etc/nginx/ssl/nginx.crt
SSL_KEY_PATH=/etc/nginx/ssl/nginx.key
ROOT_DOMAIN=example.com
```
Use the actual paths to your SSL certificate and key files.
Use the actual root domain for your lab environment.


## CLI Usage:

You can use the provided shogun.bat (for Windows) or shogun shell script (for Unix systems) to interact with the CLI. The available commands are:

1. Create a new student container:
   ```
   shogun create <student_id> <lab_id> [--count <count>] [--start <start>] [--norestart]
   ```

2. Delete a student container:
   ```
   shogun delete [<student_id>] [<lab_id>] [--norestart]
   ```

3. List available or active labs:
   ```
   shogun list <type>
   ```

For detailed information about each command and its arguments, run:
   ```
   shogun --help
   ```

---

## Adding a New Lab to Shogun

To integrate a new lab into the Shogun platform, you must follow a structured approach that ensures smooth deployment and management. Here's a step-by-step guide on how to add a new lab:

### 1. Prepare the Lab Project

If your lab project already builds Docker images to a public repo (such as Dockerhub), you can skip this step. Otherwise, you'll need to set up a GitHub repository for your lab and configure GitHub Actions to build and push Docker images to a container registry. Here are the recommended steps for doing this with GitHub Actions:

#### a. Organizing Dockerfiles

Inside your lab's repository, create a directory named `.shogun`. This directory will house all Dockerfiles tailored for Shogun deployment.

Example structure:

```
- your_lab_name/
    - src/
    - docker-compose.yml
    - .shogun/
        - Dockerfile.service1
        - Dockerfile.service2
        ...
```

Each Dockerfile within the `.shogun` directory corresponds to a specific service in your lab. Name them appropriately so that their purpose is clear.

#### b. Locally Testing the New Dockerfile(s)

Before proceeding to set up GitHub Actions, it's important to test the new Dockerfiles locally to make sure they are working as indended. Here's how we can test each Dockerfile:

1. Build the Docker image locally:
   ```
   docker build -t your_lab_name_service1 -f .shogun/Dockerfile.service1 .
   ```
2. Run the Docker image locally:
   ```
   docker run -d --name your_lab_name_service1 -p 8080:80 your_lab_name_service1
   ```
3. Test the service by visiting `localhost:8080` in your browser.
4. Check the logs to ensure there are no errors:
   ```
   docker logs your_lab_name_service1
   ```
5. Stop and remove the container:
   ```
    docker stop your_lab_name_service1
    docker rm your_lab_name_service1
    ```

**Note:** If your container is being hosted as a GitHub package, make sure you [connect a repository to the package](https://docs.github.com/en/packages/learn-github-packages/connecting-a-repository-to-a-package) by adding the source label (e.g. `LABEL org.opencontainers.image.source=https://github.com/OWNER/REPONAME`) instruction to your Dockerfile.

View the [dojo-basic](https://github.com/SamuraiWTF/samurai-dojo) repository for an example of how to set up a GitHub package for a lab and the actions required to build and push Docker images to the package.

#### c. GitHub Actions

Set up GitHub Actions to automatically build Docker images from the Dockerfiles in `.shogun` and push them to a container registry. Ensure the image names and tags are predictable and consistent across labs, e.g., `ghcr.io/username/your_lab_name_service1:latest`.




### 2. Docker Compose Template for Shogun

#### a. Template Creation

Create a Docker Compose template for your lab, similar to how you'd set up a standard Docker Compose file, but with placeholders that Shogun will replace during deployment (e.g., `{{ student_id }}`, `{{ lab_id }}`).

#### b. Required Labels

All services in your compose template should include specific labels to ensure they're appropriately managed by Shogun:

```yaml
labels:
  - 'lab_id={{ lab_id }}'
  - 'student_id={{ student_id }}'
```

For example:

```yaml
version: '3'
services:
  web:
    image: 'ghcr.io/username/your_lab_name_service1:latest'
    container_name: '{{ student_id }}_{{ lab_id }}_web'
    ports:
      - '{{ web_host_port }}:80'
    labels:
      - 'lab_id={{ lab_id }}'
      - 'student_id={{ student_id }}'
```

#### c. Adding Template to Shogun

Once your Docker Compose template is ready, add it to the Shogun project under:

```
shogun/lab_configs/docker_compose_templates/your_lab_name.template.yml
```

### 3. Update Shogun's Lab List

Ensure you update any central list or configuration within Shogun that keeps track of available labs. By default this is the lab_configs/default_config.yaml file but you can also create your own configuration file. To specify a custom config file, add a `CONFIG_FILE` entry to your .env file:

```
CONFIG_FILE=your_config_file.yaml
```