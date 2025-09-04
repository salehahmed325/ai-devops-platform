import boto3
import os
import json
from botocore.exceptions import ClientError
from decimal import Decimal
from boto3.dynamodb.conditions import Key

# Configuration
TABLE_NAME = "ai-devops-platform-data"
REGION_NAME = "us-east-1" # Based on project_context.md
CLUSTER_ID = "gmdcpgrafana01" # From previous output
LIMIT = 50 # Number of items to fetch

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

def get_dynamodb_sample_data(table_name: str, region_name: str, cluster_id: str, limit: int = 10):
    """
    Fetches a sample of the latest items from a DynamoDB table for a specific cluster_id.
    """
    try:
        # Ensure AWS credentials are configured (e.g., via environment variables or ~/.aws/credentials)
        session = boto3.Session(region_name=region_name)
        dynamodb = session.resource('dynamodb')
        table = dynamodb.Table(table_name)

        print(f"Attempting to fetch {limit} latest items for cluster '{cluster_id}' from table: {table_name} in region: {region_name}")

        response = table.query(
            KeyConditionExpression=Key('cluster_id').eq(cluster_id),
            ScanIndexForward=False, # Get latest items first
            Limit=limit
        )
        items = response.get('Items', [])

        if not items:
            print(f"No items found for cluster '{cluster_id}' in table '{table_name}'.")
            return

        print(f"Successfully fetched {len(items)} items.")
        for i, item in enumerate(items):
            print(f"\n--- Item {i+1} ---")
            print(json.dumps(item, indent=2, cls=DecimalEncoder))

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"Error: Table '{table_name}' not found in region '{region_name}'.")
        elif e.response['Error']['Code'] == 'AccessDeniedException':
            print("Error: Access denied. Please check your AWS credentials and IAM permissions.")
        else:
            print(f"An AWS client error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("Make sure your AWS credentials are configured (e.g., via AWS CLI 'aws configure' or environment variables).")
    get_dynamodb_sample_data(TABLE_NAME, REGION_NAME, CLUSTER_ID, LIMIT)
