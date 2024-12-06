WEEK="5"
PROJ=$(gcloud config get-value project)
PROJ_NUMBER=$(gcloud projects list \
--filter="$(gcloud config get-value project)" \
--format="value(PROJECT_NUMBER)")
SERVICE_ACCOUNT="cloud-run-manager@scg-l200-genai2.iam.gserviceaccount.com"
LOCATION="us-west1"
IMG_TAG="$LOCATION-docker.pkg.dev/$PROJ/l200-genai-upskill/travel-chatbot-$WEEK"

gcloud run deploy "travel-chatbot-$WEEK"  \
    --project "$PROJ"    \
    --set-env-vars "LOCATION=$LOCATION, PROJECT_NUMBER=$PROJ_NUMBER, PROJECT_ID=$PROJ"     \
    --set-secrets "GEMMA_ENDPOINT_ID=projects/$PROJ_NUMBER/secrets/travelbot-endpoint-id:1, GEMINI_TUNED_ENDPOINT_ID]]=projects/$PROJ_NUMBER/secrets/gemini-finetuned-endpoint-id:2"     \
    --image "$IMG_TAG:latest"    \
    --platform "managed"  \
    --port 8080           \
    --region "$LOCATION"    \
    --allow-unauthenticated    \
    --service-account "$SERVICE_ACCOUNT"
