# Deployment Considerations for CSV Aggregator Application

This document outlines key considerations for deploying the CSV Aggregator & Comparison Tool to a production or production-like environment.

## 1. Backend Deployment

The Python Flask backend requires specific configurations for a robust production setup.

*   **Application Server:**
    *   The Flask development server (`flask run` or `python app.py`) is not suitable for production due to its single-threaded nature and lack of performance under load.
    *   **Recommendation:** Use a production-grade WSGI (Web Server Gateway Interface) server such as:
        *   **Gunicorn:** A popular, simple, and widely used WSGI HTTP server for UNIX-like systems.
        *   **uWSGI:** A feature-rich application server that can also handle more complex setups.

*   **Containerization (Docker):**
    *   Containerizing the backend application is highly recommended for portability, consistency, and scalability.
    *   **`Dockerfile` for Backend:**
        *   Start with an official Python base image (e.g., `python:3.10-slim`).
        *   Set up a working directory (e.g., `/app`).
        *   Copy `requirements.txt` into the image.
        *   Install dependencies using `pip install -r requirements.txt --no-cache-dir`.
        *   Copy the entire `backend/` application code into the image.
        *   Expose the port the WSGI server will run on (e.g., `EXPOSE 5000`).
        *   Specify the command to run the WSGI server. Example for Gunicorn:
            ```
            CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"] 
            # Assuming your Flask app instance is named 'app' in 'app.py'
            ```
    *   **Benefits:**
        *   Ensures the application runs the same way regardless of the host environment.
        *   Simplifies dependency management.
        *   Facilitates scaling and orchestration (e.g., with Kubernetes).

*   **Dependencies:**
    *   Ensure all Python dependencies are pinned to specific versions in `backend/requirements.txt` (e.g., `Flask==2.1.0`, `pandas==1.3.5`) to ensure reproducible and stable builds. This can be achieved using `pip freeze > requirements.txt` in a development environment.

*   **Configuration Management:**
    *   Application settings such as `PROCESSED_FOLDER`, `UPLOAD_FOLDER`, `FLASK_ENV` (set to `production`), secret keys, and allowed origins for CORS should not be hardcoded.
    *   **Recommendation:** Use environment variables to manage these configurations. Flask can load configurations from environment variables at startup. This allows for flexibility across different deployment environments (dev, staging, prod) without code changes.

## 2. Frontend Deployment

The React frontend application needs to be built and served efficiently.

*   **Static Build:**
    *   The command `npm run build` (or `yarn build`) compiles the React application into a set of static HTML, CSS, and JavaScript files, typically placed in a `build/` or `dist/` directory.

*   **Serving Static Files:**
    *   These static assets can be served by any static web server. Common choices include:
        *   **Nginx:** A high-performance web server, often used as a reverse proxy and for serving static content.
        *   **Apache HTTP Server:** Another widely used web server.
    *   **Cloud Storage Solutions:** For simple deployments, static website hosting features of cloud storage services can be used:
        *   AWS S3 (Simple Storage Service)
        *   Google Cloud Storage
        *   Azure Blob Storage

*   **Containerization (Docker with Nginx):**
    *   A common pattern is to use a multi-stage Dockerfile for the frontend:
        *   **Build Stage:** Use a Node.js base image (e.g., `node:18-alpine`) to install dependencies (`npm install`) and build the React app (`npm run build`).
        *   **Serve Stage:** Use an Nginx base image (e.g., `nginx:stable-alpine`). Copy the build artifacts from the build stage (e.g., from `/app/build`) into Nginx's HTML directory (e.g., `/usr/share/nginx/html`).
        *   Include a custom Nginx configuration file (`nginx.conf`) to correctly serve the React application (e.g., handling client-side routing by redirecting all non-asset requests to `index.html`).
    *   This approach creates a lightweight image optimized for serving the compiled frontend.

*   **API URL Configuration:**
    *   The frontend application must know the URL of the backend API.
    *   **Recommendation:**
        *   **Build-time configuration:** Use environment variables during the build process (e.g., `REACT_APP_API_URL=http://your-backend-api.com npm run build`). React's build scripts can embed these into the static files.
        *   **Runtime configuration:** Place a configuration file (e.g., `config.js`) in the `public` directory that can be fetched at runtime, or inject environment variables into the serving environment (e.g., Docker container running Nginx) which then makes them available to `index.html` or a startup script.

## 3. Combined Deployment / Orchestration

For managing both backend and frontend services together:

*   **Docker Compose:**
    *   Ideal for local development, testing, and simpler single-server production deployments.
    *   A `docker-compose.yml` file can define the backend and frontend services, their respective Docker images (or build contexts), ports, environment variables, and potentially shared volumes or networks.
    *   Example services:
        *   `backend-service`: Builds from the backend Dockerfile, maps port 5000.
        *   `frontend-service`: Builds from the frontend Dockerfile, maps port 80 (or 3000 if Nginx is configured for that).

*   **Kubernetes (K8s):**
    *   For more complex, scalable, and resilient deployments, especially in cloud environments.
    *   Requires creating Kubernetes deployment manifests (YAML files) for Deployments, Services, Ingress (for routing), ConfigMaps (for configuration), etc., for both backend and frontend.
    *   Offers advanced features like auto-scaling, rolling updates, service discovery, and self-healing.

*   **Platform-as-a-Service (PaaS):**
    *   Solutions like Heroku, AWS Elastic Beanstalk, Google App Engine, Azure App Service can significantly simplify deployment.
    *   Developers typically provide the application code (and sometimes a Docker image or configuration like a Procfile), and the PaaS handles the underlying infrastructure, scaling, load balancing, and often CI/CD integration.
    *   May have specific requirements or conventions for structuring the application.

## 4. Data Persistence

As noted in the architecture documentation:

*   **`backend/uploads/`**: This directory is for transient storage of uploaded CSVs. While the application attempts to clean these up after processing, in a containerized environment, this local storage is ephemeral. If the backend container restarts, these files are lost (which is acceptable for their purpose).
*   **`backend/processed/`**: This directory stores the generated Excel reports.
    *   **Challenge:** In a simple Docker deployment, this directory is also local to the container's filesystem and will be lost if the container is removed or restarted (unless a volume is used). For multi-instance backend deployments, this local storage is not shared.
    *   **Solutions for Persistent Reports:**
        *   **Docker Volumes:** Mount a host directory or a named Docker volume to `/app/backend/processed` within the backend container to persist reports on the host machine or a managed volume.
        *   **Shared Network Storage:** For multi-instance backends, use a shared storage solution like NFS (Network File System) or a cloud-based file service (e.g., AWS EFS, Azure Files) mounted into all backend containers.
        *   **Cloud Object Storage (e.g., S3, GCS, Azure Blob):** A more scalable approach is to have the backend upload generated reports to a cloud object storage bucket. The download endpoint would then serve files from this bucket (e.g., by providing signed URLs or proxying downloads). This decouples report storage from the backend instances.

## 5. CORS (Cross-Origin Resource Sharing)

*   If the frontend and backend are served from different domains or ports (common in development and many production setups), CORS must be configured on the backend.
*   **Recommendation:** Use the `Flask-CORS` extension for the Flask backend.
    *   Configure it to allow requests specifically from the frontend's production domain(s).
    *   Avoid using wildcard origins (`*`) in production for security reasons.
    *   Specify allowed methods (GET, POST, OPTIONS), headers, and whether credentials can be supported if necessary.

## 6. HTTPS

*   **Essential for Production:** All communication between users, the frontend, and the backend must be over HTTPS to secure data in transit.
*   **Implementation:**
    *   Typically not handled directly within the Flask/Node.js application code.
    *   **Reverse Proxy:** Deploy a reverse proxy like Nginx or a load balancer (e.g., AWS ELB/ALB, Google Cloud Load Balancing) in front of the application.
    *   The reverse proxy/load balancer handles SSL/TLS termination (decrypts incoming HTTPS traffic and forwards it as HTTP to the backend application servers within the internal network).
    *   It also manages SSL certificates (e.g., using Let's Encrypt for free certificates or commercial certificates).

These considerations provide a starting point for planning the deployment of the CSV Aggregator application. The specific choices will depend on the expected scale, budget, and existing infrastructure.Okay, I have created the `docs/deployment_considerations.md` file and populated it with the detailed deployment considerations as outlined in the subtask description.

The content covers:
*   **Backend Deployment:** WSGI servers, Docker containerization, dependency pinning, and configuration management using environment variables.
*   **Frontend Deployment:** Static builds, serving static files (Nginx, cloud storage), Docker containerization with Nginx, and API URL configuration.
*   **Combined Deployment / Orchestration:** Docker Compose, Kubernetes, and PaaS solutions.
*   **Data Persistence:** Challenges with local container storage for `processed/` reports and solutions like Docker volumes, shared network storage, or cloud object storage.
*   **CORS:** Necessity and configuration using Flask-CORS for production.
*   **HTTPS:** Importance and implementation via reverse proxies or load balancers.

This document should serve as a comprehensive guide for deploying the application.
