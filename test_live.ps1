# Set environment variables
$env:TEST_SUMMONER_NAME = "Numandiel"
$env:TEST_SUMMONER_TAG = "EUW"
$env:TEST_REGION = "EUW1"  # EUW yerine EUW1 kullanmalıyız
$env:TEST_INTERVAL = "30"

# Run the test script
python src/test_live_data.py 