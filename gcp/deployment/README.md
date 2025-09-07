# GCP Deployment Guide for DevCycle API

This guide explains how to deploy the DevCycle API to Google Cloud Platform using managed SSL/TLS certificates and load balancing.

## 🏗️ **Architecture Overview**

```
Internet → GCP Load Balancer (HTTPS) → Cloud Run/Compute Engine (HTTP) → DevCycle API
```

### **Key Components**

1. **GCP Load Balancer**: Handles SSL/TLS termination and load balancing
2. **Managed SSL Certificates**: Automatic certificate management and renewal
3. **Cloud Run/Compute Engine**: Hosts the DevCycle API application
4. **Secret Manager**: Stores sensitive configuration values
5. **Cloud SQL**: Managed PostgreSQL database
6. **Cloud Memorystore**: Managed Redis cache

## 🚀 **Deployment Options**

### **Option 1: Cloud Run (Recommended for Serverless)**

- **Pros**: Auto-scaling, pay-per-use, managed infrastructure
- **Cons**: Cold starts, execution time limits
- **Best for**: Variable traffic, cost optimization

### **Option 2: Compute Engine (GKE)**

- **Pros**: Full control, persistent connections, no cold starts
- **Cons**: Higher cost, more management overhead
- **Best for**: High traffic, consistent performance requirements

## 📋 **Prerequisites**

1. **GCP Project** with billing enabled
2. **gcloud CLI** installed and configured
3. **Docker** installed for building images
4. **kubectl** installed (for Compute Engine deployment)
5. **Domain name** configured in GCP

## 🔧 **Configuration**

### **1. Environment Variables**

The application uses the following environment variables:

```bash
# Required
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
API_GCP_LOAD_BALANCER_ENABLED=true
API_TRUST_PROXY=true

# Database
DB_HOST=your-cloud-sql-instance
DB_PASSWORD=your-secure-password

# Security
SECURITY_SECRET_KEY=your-very-secure-secret-key

# Redis
REDIS_HOST=your-memorystore-instance
REDIS_PASSWORD=your-redis-password

# Hugging Face
HF_TOKEN=your-huggingface-token
```

### **2. GCP Services Required**

- **Cloud Run** or **Compute Engine**
- **Cloud SQL** (PostgreSQL)
- **Cloud Memorystore** (Redis)
- **Secret Manager**
- **Load Balancer** with managed SSL
- **Cloud DNS** (for domain management)

## 🚀 **Deployment Steps**

### **Step 1: Prepare GCP Project**

```bash
# Set your project ID
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable compute.googleapis.com
```

### **Step 2: Create Secrets**

```bash
# Create secrets in Secret Manager
echo -n "your-db-host" | gcloud secrets create devcycle-secrets --data-file=-
echo -n "your-db-password" | gcloud secrets versions add devcycle-secrets --data-file=-
echo -n "your-secret-key" | gcloud secrets versions add devcycle-secrets --data-file=-
echo -n "your-redis-host" | gcloud secrets versions add devcycle-secrets --data-file=-
echo -n "your-redis-password" | gcloud secrets versions add devcycle-secrets --data-file=-
echo -n "your-hf-token" | gcloud secrets versions add devcycle-secrets --data-file=-
```

### **Step 3: Deploy Application**

#### **Cloud Run Deployment**

```bash
# Build and push image
docker build -f gcp/deployment/Dockerfile -t gcr.io/$GCP_PROJECT_ID/devcycle-api:latest .
docker push gcr.io/$GCP_PROJECT_ID/devcycle-api:latest

# Deploy to Cloud Run
gcloud run deploy devcycle-api \
  --image gcr.io/$GCP_PROJECT_ID/devcycle-api:latest \
  --platform managed \
  --region $GCP_REGION \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 100 \
  --min-instances 1 \
  --timeout 300 \
  --concurrency 100 \
  --set-env-vars "ENVIRONMENT=production,API_HOST=0.0.0.0,API_PORT=8000,API_GCP_LOAD_BALANCER_ENABLED=true,API_TRUST_PROXY=true" \
  --set-secrets "DB_HOST=devcycle-secrets:db-host,DB_PASSWORD=devcycle-secrets:db-password,SECURITY_SECRET_KEY=devcycle-secrets:secret-key,REDIS_HOST=devcycle-secrets:redis-host,REDIS_PASSWORD=devcycle-secrets:redis-password,HF_TOKEN=devcycle-secrets:hf-token"
```

#### **Compute Engine Deployment**

```bash
# Apply Kubernetes manifests
kubectl apply -f gcp/deployment/compute-engine.yaml
kubectl apply -f gcp/deployment/load-balancer.yaml

# Wait for deployment
kubectl wait --for=condition=available --timeout=300s deployment/devcycle-api-deployment
```

### **Step 4: Configure Load Balancer**

1. **Create Global Load Balancer** in GCP Console
2. **Configure Backend Service** pointing to your Cloud Run service or GKE cluster
3. **Set up URL Map** with path-based routing
4. **Configure Managed SSL Certificate** for your domain
5. **Set up Health Checks** using `/api/v1/health/ready` endpoint

### **Step 5: Configure DNS**

1. **Create A record** pointing to the load balancer IP
2. **Create CNAME record** for `api.yourdomain.com`
3. **Wait for SSL certificate** to be provisioned (can take up to 1 hour)

## 🔍 **Verification**

### **Health Checks**

```bash
# Check application health
curl https://yourdomain.com/api/v1/health
curl https://yourdomain.com/api/v1/health/ready
curl https://yourdomain.com/api/v1/health/live
```

### **SSL Certificate**

```bash
# Check SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

### **Load Balancer**

```bash
# Check load balancer status
gcloud compute url-maps list
gcloud compute backend-services list
```

## 📊 **Monitoring and Logging**

### **Cloud Monitoring**

- **Application metrics** via Cloud Run/Compute Engine
- **Load balancer metrics** via GCP Load Balancer
- **Database metrics** via Cloud SQL
- **Custom metrics** via application code

### **Cloud Logging**

- **Application logs** via Cloud Run/Compute Engine
- **Load balancer logs** via GCP Load Balancer
- **Access logs** via Cloud CDN (if enabled)

## 🔒 **Security Features**

### **SSL/TLS**

- **Managed SSL certificates** with automatic renewal
- **TLS 1.2+** only
- **Strong cipher suites** configured
- **HTTP to HTTPS redirect** via load balancer

### **Network Security**

- **VPC** for private networking
- **Firewall rules** restricting access
- **Private Google Access** for Cloud SQL and Memorystore
- **Cloud Armor** for DDoS protection (optional)

### **Application Security**

- **Security headers** via middleware
- **CORS** properly configured
- **Rate limiting** on auth endpoints
- **Secret management** via Secret Manager

## 🚨 **Troubleshooting**

### **Common Issues**

1. **SSL Certificate Not Provisioned**
   - Check domain DNS configuration
   - Verify domain ownership
   - Wait up to 1 hour for certificate

2. **Application Not Starting**
   - Check environment variables
   - Verify secrets are accessible
   - Check application logs

3. **Load Balancer Not Routing**
   - Check backend service health
   - Verify URL map configuration
   - Check firewall rules

### **Debug Commands**

```bash
# Check Cloud Run logs
gcloud run logs read devcycle-api --region=$GCP_REGION

# Check GKE logs
kubectl logs -l app=devcycle-api

# Check load balancer status
gcloud compute url-maps describe devcycle-api-ingress
```

## 💰 **Cost Optimization**

### **Cloud Run**

- **Set minimum instances** to 0 for cost savings
- **Use appropriate memory/CPU** allocation
- **Monitor execution time** to avoid cold starts

### **Compute Engine**

- **Use preemptible instances** for non-critical workloads
- **Right-size instances** based on actual usage
- **Use committed use discounts** for predictable workloads

## 🔄 **Updates and Maintenance**

### **Application Updates**

```bash
# Build new image
docker build -f gcp/deployment/Dockerfile -t gcr.io/$GCP_PROJECT_ID/devcycle-api:$TAG .

# Push image
docker push gcr.io/$GCP_PROJECT_ID/devcycle-api:$TAG

# Update Cloud Run
gcloud run deploy devcycle-api --image gcr.io/$GCP_PROJECT_ID/devcycle-api:$TAG

# Update GKE
kubectl set image deployment/devcycle-api-deployment devcycle-api=gcr.io/$GCP_PROJECT_ID/devcycle-api:$TAG
```

### **SSL Certificate Renewal**

- **Automatic renewal** handled by GCP
- **No manual intervention** required
- **Monitor certificate status** via Cloud Console

## 📚 **Additional Resources**

- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GCP Load Balancer Documentation](https://cloud.google.com/load-balancing/docs)
- [GCP Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [DevCycle API Documentation](../docs/api-documentation.md)
