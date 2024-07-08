#!/bin/bash

# Register a user
# echo "Registering a user..."
# curl -X POST -H "Content-Type: application/json" \
# -d '{"username":"ahmed", "password":"testpass"}' \
# http://localhost:5000/register

# Login to get JWT token
echo "Logging in..."
response=$(curl -s -X POST -H "Content-Type: application/json" \
-d '{"username":"ahmed", "password":"testpass"}' \
http://localhost:5000/login)

token=$(echo $response | jq -r '.token')
echo "Token: $token"

# Request VM creation
echo "Requesting VM creation..."
response=$(curl -s -X POST -i -H "x-access-tokens: $token" \
http://localhost:5000/request-vm)


# Extract the Automation Key from headers
automation_key=$(echo "$response" | sed -n 's/^Automation-Key: \(.*\)/\1/p' )
echo "Automation Key: $automation_key"

# Create job
echo "Creating job..."
curl -X POST -H "x-access-tokens: $token" \
-H "Automation-Key: $automation_key" \
http://localhost:5000/create-job

# Wait a few seconds to let the job complete
sleep 3

# Check job status
echo "Checking job status..."
curl -X GET -H "x-access-tokens: $token" \
-H "Automation-Key: $automation_key" \
http://localhost:5000/job-status
