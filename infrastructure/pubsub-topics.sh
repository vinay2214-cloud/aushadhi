#!/bin/bash
# infrastructure/pubsub-topics.sh
# Run: bash infrastructure/pubsub-topics.sh
set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"aushadhi-hackathon-2026"}

echo "🔧 Creating Pub/Sub topics for project: $PROJECT_ID"

TOPICS=(
  "aushadhi-sentinel-alerts"
  "aushadhi-validated-data"
  "aushadhi-forecast-complete"
  "aushadhi-procured"
  "aushadhi-dead-letter"
)

for TOPIC in "${TOPICS[@]}"; do
  gcloud pubsub topics create $TOPIC --project=$PROJECT_ID 2>/dev/null \
    && echo "  ✅ Created topic: $TOPIC" \
    || echo "  ⏭  Topic exists: $TOPIC"
done

echo ""
echo "🔧 Creating subscriptions..."

# No associative arrays here: macOS ships bash 3.2, which has no `declare -A`.
create_sub() {
  SUB="$1"
  TOPIC="$2"
  gcloud pubsub subscriptions create $SUB \
    --topic=$TOPIC \
    --ack-deadline=120 \
    --message-retention-duration=1h \
    --expiration-period=never \
    --project=$PROJECT_ID 2>/dev/null \
    && echo "  ✅ Created subscription: $SUB → $TOPIC" \
    || echo "  ⏭  Subscription exists: $SUB"
}

create_sub "aushadhi-sentinel-alerts-sub"   "aushadhi-sentinel-alerts"
create_sub "aushadhi-validated-data-sub"    "aushadhi-validated-data"
create_sub "aushadhi-forecast-complete-sub" "aushadhi-forecast-complete"
create_sub "aushadhi-procured-sub"          "aushadhi-procured"

echo ""
echo "✅ Pub/Sub setup complete for AUSHADHI"
