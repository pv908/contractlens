#!/usr/bin/env bash
set -e

# One-shot build + deploy script for ContractLens
# Reads your .env file and passes all the variables to Cloud Run.

PROJECT_ID=$(gcloud config get-value project)
IMAGE="gcr.io/${PROJECT_ID}/contractlens"

echo "Using project: ${PROJECT_ID}"
echo "Building image: ${IMAGE}"
echo "----------------------------------------"

gcloud builds submit --tag "${IMAGE}"

echo "----------------------------------------"
echo "Loading env vars from .env..."

# Convert .env lines into a comma-separated list
ENV_VARS=$(grep -v '^#' .env | xargs | sed 's/ /,/g')

echo "Env vars found:"
echo "${ENV_VARS}"
echo "----------------------------------------"

echo "Deploying to Cloud Run..."
echo

gcloud run deploy contractlens \
  --image "${IMAGE}" \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "${ENV_VARS}"

echo
echo "✅ Deploy complete."
