#!/bin/bash

# Azure Deployment Script for Nexus System
# This script deploys the complete Nexus system to Azure

set -e

echo "=========================================="
echo "Nexus Azure Deployment"
echo "=========================================="

# Configuration
RESOURCE_GROUP="nexus-rg"
LOCATION="eastus"
APP_SERVICE_PLAN="nexus-plan"
AUTH_APP_NAME="nexus-auth-app"
NEXUS_APP_NAME="nexus-api-app"
STORAGE_ACCOUNT="nexusstorage$(date +%s)"
CONTAINER_REGISTRY="nexusregistry$(date +%s)"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI is not installed"
    echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
echo "Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo "Please login to Azure:"
    az login
fi

# Get subscription
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Using subscription: $SUBSCRIPTION_ID"

# Create Resource Group
echo ""
echo "Creating resource group: $RESOURCE_GROUP"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION

# Create App Service Plan (Linux)
echo ""
echo "Creating App Service Plan: $APP_SERVICE_PLAN"
az appservice plan create \
    --name $APP_SERVICE_PLAN \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --is-linux \
    --sku B1

# Create Auth Web App
echo ""
echo "Creating Auth Service: $AUTH_APP_NAME"
az webapp create \
    --name $AUTH_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --runtime "PYTHON:3.11"

# Create Nexus API Web App
echo ""
echo "Creating Nexus API: $NEXUS_APP_NAME"
az webapp create \
    --name $NEXUS_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --runtime "PYTHON:3.11"

# Configure Auth App Settings
echo ""
echo "Configuring Auth Service environment variables..."
az webapp config appsettings set \
    --name $AUTH_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        SECRET_KEY="$(openssl rand -hex 32)" \
        DATABASE_URL="sqlite:///./auth_system.db" \
        AUTH_ALLOWED_ORIGINS="https://$AUTH_APP_NAME.azurewebsites.net,https://$NEXUS_APP_NAME.azurewebsites.net" \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Configure Nexus App Settings
echo ""
echo "Configuring Nexus API environment variables..."
az webapp config appsettings set \
    --name $NEXUS_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        JWT_SECRET="$(openssl rand -hex 32)" \
        GEMINI_API_KEY="$GEMINI_API_KEY" \
        DATABASE_URL="sqlite:///./nexus.db" \
        CONFIDENCE_THRESHOLD="0.5" \
        MAX_CONCURRENT_TASKS="50" \
        TOKEN_EXPIRY_MINUTES="30" \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Configure deployment source for Auth
echo ""
echo "Configuring Auth Service deployment..."
cd auth
zip -r ../auth-deploy.zip . -x "*.pyc" -x "__pycache__/*" -x ".pytest_cache/*"
cd ..

az webapp deployment source config-zip \
    --name $AUTH_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --src auth-deploy.zip

# Configure deployment source for Nexus
echo ""
echo "Configuring Nexus API deployment..."
zip -r nexus-deploy.zip . \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x ".pytest_cache/*" \
    -x "client/*" \
    -x "auth/*" \
    -x "*.log" \
    -x ".git/*"

az webapp deployment source config-zip \
    --name $NEXUS_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --src nexus-deploy.zip

# Get URLs
AUTH_URL=$(az webapp show --name $AUTH_APP_NAME --resource-group $RESOURCE_GROUP --query defaultHostName -o tsv)
NEXUS_URL=$(az webapp show --name $NEXUS_APP_NAME --resource-group $RESOURCE_GROUP --query defaultHostName -o tsv)

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Services:"
echo "  Auth API:  https://$AUTH_URL"
echo "  Nexus API: https://$NEXUS_URL"
echo ""
echo "Next steps:"
echo "1. Update client/.env with these URLs:"
echo "   VITE_AUTH_API_BASE=https://$AUTH_URL"
echo "   VITE_NEXUS_API_BASE=https://$NEXUS_URL"
echo ""
echo "2. Deploy frontend to Azure Static Web Apps:"
echo "   ./deploy-frontend.sh"
echo ""
echo "3. Initialize databases:"
echo "   az webapp ssh --name $NEXUS_APP_NAME --resource-group $RESOURCE_GROUP"
echo "   python -m nexus.init_db"
echo ""
echo "To view logs:"
echo "  az webapp log tail --name $AUTH_APP_NAME --resource-group $RESOURCE_GROUP"
echo "  az webapp log tail --name $NEXUS_APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
