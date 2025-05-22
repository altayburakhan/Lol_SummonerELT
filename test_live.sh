#!/bin/bash

# Load environment variables
export TEST_SUMMONER_NAME="Numandiel"
export TEST_SUMMONER_TAG="EUW"
export TEST_REGION="EUW"
export TEST_INTERVAL=30

# Run the test script
python src/test_live_data.py 