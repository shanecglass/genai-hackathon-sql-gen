WEEK="5"
PROJ=$(gcloud config get-value project)
LOCATION="us-west1"
IMG_TAG="$LOCATION-docker.pkg.dev/$PROJ/l200-genai-upskill/travel-chatbot-$WEEK"

gcloud builds --project $PROJ submit --tag "$IMG_TAG:latest"
