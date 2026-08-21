#!/bin/bash
# scripts/teardown.sh
# Run EVERY NIGHT to stop GCP costs
# Usage: bash scripts/teardown.sh

echo "🌙 AUSHADHI — End of Day Cost Shutdown"
REGION="us-central1"

gcloud run services update aushadhi-api --min-instances=0 --region=$REGION 2>/dev/null
gcloud run services update aushadhi-agents --min-instances=0 --region=$REGION 2>/dev/null
gcloud run services update aushadhi-frontend --min-instances=0 --region=$REGION 2>/dev/null
gcloud scheduler jobs pause sentinel-poll --location=$REGION 2>/dev/null

echo "✅ All services scaled to zero. GCP costs stopped."
echo "   Resume tomorrow: gcloud scheduler jobs resume sentinel-poll --location=$REGION"
