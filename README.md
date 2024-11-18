# Trading App

## Step 1: Install Required Softwares
Update your package manager and install necessary packages:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git
```

## Step 2: Clone Your FastAPI Application
Clone your FastAPI project from your version control system:
```commandline
git clone https://github.com/DeltaCompute24/SN8_Trading_App.git
cd SN8_Trading_App
```

## Step 3: Set Up a Virtual Environment
Create a virtual environment for your FastAPI application:
```bash
python3 -m venv venv
source venv/bin/activate
```

## Step 4: Install Python Dependencies
Install the necessary Python packages for your application:
```bash
pip install -r requirements.txt
```

## Step 5: Configure Environment Variables
Create a .env file in your project directory to store environment variables:
```bash
touch .env
```
Add the necessary environment variables:
```bash
POLYGON_API_KEY="XXXXXXXXXXXXXXXXXXXXXXXX"
SIGNAL_API_KEY="XXXXXXXXXXXXXXXXXXXXXX"
DATABASE_URL=postgresql+asyncpg://developer:DeltaCompute123@rococo-db-server-postgres-aurora.cluster-c3y444mm80qj.eu-west-1.rds.amazonaws.com/postgres
```

## Step 6: Set Up Redis
Install Redis for Celery:
```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## Step 7: Run Celery Beat and Workers
Start the Celery beat:
```bash
celery -A src.core.celery_app beat --loglevel=info
```

Start the Celery worker for position_monitor task
```bash
celery -A src.core.celery_app worker --loglevel=info -Q position_monitoring
```

Start the Celery worker for subscription_manager task
```bash
celery -A src.core.celery_app worker --loglevel=info -Q subscription_management
```

## Step 8: Run the FastAPI Application
Run the FastAPI application using uvicorn:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 80
```

## Step 9: Install and Configure Nginx

Install Nginx to act as a reverse proxy:
```bash
sudo apt install nginx
```

Create Nginx configuration file for your FastAPI application:
```bash
sudo nano /etc/nginx/sites-available/trading_app
```
Add the following configuration:

```bash
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the configuration and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/trading_app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Use Certbot to obtain an SSL certificate from Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

# Conclusion
You have successfully deployed your FastAPI application with Celery tasks on an AWS EC2 instance. This setup includes running Redis for Celery, and using Nginx as a reverse proxy.