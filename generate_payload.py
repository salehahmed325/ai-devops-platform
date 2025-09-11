import sys
import httpx
import json
import boto3

# Create a sample JSON payload
json_payload = {
    "metric": {
        "__name__": "test_metric",
        "instance": "test_instance",
        "job": "test_job",
        "cluster_id": "test_cluster"
    },
    "value": [1678886400.0, 1.0]
}

# Serialize to JSON string
json_data = json.dumps(json_payload)

# Save to file (optional, for debugging)
with open("payload.json", "w") as f:
    f.write(json_data)
print("Payload saved to payload.json")

# Send the request
API_KEY = "nppVhOlacSElDHVz6qa46IYw5nXcBA1m2zo5RVNG"
API_ENDPOINT = "https://6kyjm29wa6.execute-api.us-east-1.amazonaws.com/"

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

try:
    response = httpx.post(API_ENDPOINT, headers=headers, content=json_data)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except httpx.RequestError as exc:
    print(f"An error occurred while requesting {exc.request.url!r}: {exc}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

# --- DynamoDB Verification ---
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("ai-devops-platform-data")

print("\nScanning DynamoDB table for the test item...")

response = table.scan(
    FilterExpression="cluster_id = :cid AND metric_name = :mn",
    ExpressionAttributeValues={
        ":cid": {"S": "test_cluster"},
        ":mn": {"S": "test_metric"}
    }
)

items = response.get("Items", [])

if items:
    print("Found item(s) in DynamoDB:")
    for item in items:
        print(item)
else:
    print("Test item not found in DynamoDB.")