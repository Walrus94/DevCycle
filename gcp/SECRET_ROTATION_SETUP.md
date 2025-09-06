# 🔐 GCP Secret Manager & Rotation Setup Guide

This guide walks you through setting up Google Cloud Platform Secret Manager with automated secret rotation for your DevCycle application.

## 🎯 Overview

The setup includes:
- **GCP Secret Manager** for secure secret storage
- **Cloud Functions** for automated secret rotation
- **Cloud Scheduler** for scheduled rotation triggers
- **Enhanced configuration** that automatically retrieves secrets from GCP

## 📋 Prerequisites

1. **GCP Project** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Required APIs** enabled (handled by deployment script)
4. **IAM permissions** to create resources

## 🚀 Quick Setup

### 1. Configure Environment Variables

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GCP_REGION="us-central1"  # or your preferred region
```

### 2. Run the Deployment Script

```bash
chmod +x gcp/deploy-secret-rotation.sh
./gcp/deploy-secret-rotation.sh
```

This script will:
- ✅ Enable required GCP APIs
- ✅ Create secrets in Secret Manager
- ✅ Deploy Cloud Functions for rotation
- ✅ Set up Cloud Scheduler jobs
- ✅ Configure IAM permissions
- ✅ Test the setup

## 🔧 Manual Setup (Alternative)

If you prefer manual setup or need to customize:

### 1. Enable APIs

```bash
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 2. Create Secrets

```bash
# Production secrets
echo -n "$(openssl rand -base64 32)" | gcloud secrets create prod-jwt-secret-key --data-file=-
echo -n "$(openssl rand -base64 32)" | gcloud secrets create prod-database-password --data-file=-
echo -n "$(openssl rand -base64 32)" | gcloud secrets create prod-redis-password --data-file=-
echo -n "your-huggingface-token" | gcloud secrets create prod-huggingface-token --data-file=-

# Staging secrets
echo -n "$(openssl rand -base64 32)" | gcloud secrets create staging-jwt-secret-key --data-file=-
echo -n "$(openssl rand -base64 32)" | gcloud secrets create staging-database-password --data-file=-
echo -n "$(openssl rand -base64 32)" | gcloud secrets create staging-redis-password --data-file=-
echo -n "your-huggingface-token" | gcloud secrets create staging-huggingface-token --data-file=-
```

### 3. Deploy Cloud Functions

```bash
# Main rotation function
gcloud functions deploy rotate-secret \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --source ./gcp/cloud-functions/secret-rotation \
    --entry-point rotate_secret \
    --region us-central1 \
    --memory 256MB \
    --timeout 300s

# Validation function
gcloud functions deploy validate-secrets \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --source ./gcp/cloud-functions/secret-rotation \
    --entry-point validate_secrets \
    --region us-central1 \
    --memory 256MB \
    --timeout 180s
```

### 4. Create Scheduler Jobs

```bash
# JWT secret rotation (monthly)
gcloud scheduler jobs create http jwt-secret-rotation \
    --location=us-central1 \
    --schedule="0 2 1 * *" \
    --uri="https://us-central1-your-project.cloudfunctions.net/rotate-secret" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"secret_id":"jwt-secret-key","environment":"prod","rotation_type":"jwt"}' \
    --time-zone="UTC"

# Database password rotation (quarterly)
gcloud scheduler jobs create http database-password-rotation \
    --location=us-central1 \
    --schedule="0 3 1 */3 *" \
    --uri="https://us-central1-your-project.cloudfunctions.net/rotate-secret" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"secret_id":"database-password","environment":"prod","rotation_type":"password"}' \
    --time-zone="UTC"
```

## 🔄 Rotation Schedules

| Secret Type | Schedule | Frequency | Function |
|-------------|----------|-----------|----------|
| JWT Secret Key | `0 2 1 * *` | Monthly | `rotate-secret` |
| Database Password | `0 3 1 */3 *` | Quarterly | `rotate-secret` |
| Redis Password | `0 4 1 */2 *` | Bi-monthly | `rotate-secret` |
| HuggingFace Token | `0 5 1 */6 *` | Semi-annually | `rotate-secret` |
| Secret Validation | `0 6 * * *` | Daily | `validate-secrets` |

## 🛠️ Application Integration

### 1. Update Dependencies

Add to your `pyproject.toml`:

```toml
[tool.poetry.dependencies]
google-cloud-secret-manager = "^2.16.0"
```

### 2. Update Configuration

Replace your current configuration with the secret-aware version:

```python
# In your main configuration file
from devcycle.core.secrets.secret_config import (
    SecretAwareSecurityConfig,
    SecretAwareDatabaseConfig,
    SecretAwareRedisConfig,
    SecretAwareHuggingFaceConfig
)

# Use the new secret-aware configurations
security = SecretAwareSecurityConfig()
database = SecretAwareDatabaseConfig()
redis = SecretAwareRedisConfig()
huggingface = SecretAwareHuggingFaceConfig()
```

### 3. Environment Variables

Set these environment variables for your application:

```bash
# Required
export ENVIRONMENT="production"  # or "staging", "development"
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Optional (fallbacks for development)
export SECRET_KEY="dev-secret-key"  # Only for development
export DB_PASSWORD="dev-password"   # Only for development
export REDIS_PASSWORD="dev-redis-password"  # Only for development
export HF_TOKEN="dev-hf-token"      # Only for development
```

## 🧪 Testing

### 1. Test Secret Retrieval

```python
from devcycle.core.secrets.gcp_secret_manager import get_secret

# Test retrieving a secret
secret_value = get_secret("jwt-secret-key", environment="prod")
print(f"Retrieved secret: {secret_value[:10]}...")
```

### 2. Test Manual Rotation

```bash
# Rotate JWT secret manually
gcloud functions call rotate-secret \
    --region=us-central1 \
    --data='{"secret_id":"jwt-secret-key","environment":"prod","rotation_type":"jwt"}'
```

### 3. Test Validation

```bash
# Validate all secrets
gcloud functions call validate-secrets \
    --region=us-central1 \
    --data='{"environment":"prod"}'
```

## 📊 Monitoring

### 1. Cloud Functions Logs

```bash
# View rotation logs
gcloud functions logs read rotate-secret --region=us-central1

# View validation logs
gcloud functions logs read validate-secrets --region=us-central1
```

### 2. Cloud Scheduler Jobs

```bash
# List all scheduler jobs
gcloud scheduler jobs list --location=us-central1

# View job details
gcloud scheduler jobs describe jwt-secret-rotation --location=us-central1
```

### 3. Secret Manager

```bash
# List all secrets
gcloud secrets list

# View secret versions
gcloud secrets versions list prod-jwt-secret-key
```

## 🔒 Security Best Practices

### 1. IAM Permissions

- **Principle of Least Privilege**: Only grant necessary permissions
- **Service Account**: Use dedicated service accounts for different functions
- **Audit Logging**: Enable Cloud Audit Logs for secret access

### 2. Secret Naming Convention

```
{environment}-{secret-type}-{purpose}
```

Examples:
- `prod-jwt-secret-key`
- `staging-database-password`
- `prod-redis-password`

### 3. Rotation Strategy

- **High-frequency secrets** (JWT): Monthly rotation
- **Medium-frequency secrets** (DB passwords): Quarterly rotation
- **Low-frequency secrets** (API tokens): Semi-annual rotation
- **Validation**: Daily checks for accessibility

## 🚨 Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Grant Secret Manager access
   gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:SERVICE_ACCOUNT" \
       --role="roles/secretmanager.secretAccessor"
   ```

2. **Function Timeout**
   ```bash
   # Increase timeout
   gcloud functions deploy rotate-secret \
       --timeout=600s
   ```

3. **Secret Not Found**
   ```bash
   # Check if secret exists
   gcloud secrets describe prod-jwt-secret-key

   # Create if missing
   echo -n "new-secret-value" | gcloud secrets create prod-jwt-secret-key --data-file=-
   ```

### Debug Commands

```bash
# Test function locally
gcloud functions call rotate-secret \
    --region=us-central1 \
    --data='{"secret_id":"jwt-secret-key","environment":"prod"}' \
    --log-http

# View function details
gcloud functions describe rotate-secret --region=us-central1

# Check scheduler job status
gcloud scheduler jobs describe jwt-secret-rotation --location=us-central1
```

## 📈 Cost Optimization

### 1. Function Optimization

- **Memory**: Use minimum required memory (256MB for most functions)
- **Timeout**: Set appropriate timeouts to avoid unnecessary costs
- **Cold Starts**: Consider using Cloud Run for better performance

### 2. Scheduler Optimization

- **Frequency**: Balance security needs with cost
- **Timezone**: Use UTC to avoid daylight saving issues
- **Retry Logic**: Configure appropriate retry policies

## 🔄 Migration from Environment Variables

### 1. Gradual Migration

1. **Phase 1**: Deploy GCP infrastructure
2. **Phase 2**: Update application configuration
3. **Phase 3**: Test in staging environment
4. **Phase 4**: Deploy to production
5. **Phase 5**: Remove old environment variables

### 2. Rollback Plan

Keep environment variables as fallbacks during migration:

```python
# Configuration supports both GCP and environment variables
secret_value = get_secret(
    "jwt-secret-key",
    environment="prod",
    fallback_env_var="SECRET_KEY"  # Fallback for development
)
```

## 📚 Additional Resources

- [GCP Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [IAM Best Practices](https://cloud.google.com/iam/docs/using-iam-securely)

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review Cloud Functions logs
3. Verify IAM permissions
4. Test with manual function calls
5. Check GCP quotas and limits

---

**Note**: This setup provides enterprise-grade secret management with automated rotation. The system is designed to be secure, scalable, and cost-effective for production use.
