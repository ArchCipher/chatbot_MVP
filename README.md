# Chatbot MVP

## Overview
MVP chatbot which handles consultation and product config details for clients in python using fastapi and uvicorn server.

## Requirements

Check requirements.txt

## Environment
Make sure you create a virtual environment, activate it, and then install all dependencies mentioned in requirements.txt
```sh
python -m venv .venv    # create venv
source .venv/bin/activate   # activate venv

pip install -r requirements.txt # install dependencies
```

Environment vars:

Create `.env` file with variables mentioned in `.env.example`


## Run
As uvicorn runs async with the current code:
`python chatbot.py`

To run the server non async:
`fastapi dev chatbot.py`
or
`uvicorn chatbot:app --reload`

## Architecture

### Conversation Flows
The chatbot uses a state machine with 3 main flows:
1. Consultation
- Collects user information: topic, name, email, phone, company details
- Available to both buyers and sellers
- After completion, buyers automatically proceed to product configuration
2. Product Configuration
- Collects power source preferences (solar, wind, hydro, thermal)
- Fixed/market price ratio (must sum to 100%)
- Renewable energy ratio (0-100%)
- Only available to buyers
3. Operational
- Stub implementation for MVP
- Intended for operational inquiries (history, matching, etc.)

### State Management
- Client Type Detection: Determines if user is buyer or seller based on keywords
- Flow Detection: Routes to appropriate flow based on keywords and client type
- State Tracking: Each flow maintains its own state (e.g., "ask_email", "ask_power_sources")
- Context Storage: Collected data stored in session context dictionary
- Validation: Email format, phone number format, percentage ranges validated

## Future improvement:
- Handle operational inquiry
- AI fallback
- Table-driven flow
- Intent classifier instead of detect_flow
- Google's libphonenumber validation

## API Documentation

FastAPI automatically generates interactive API documentation:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### GET /

Health check endpoint.

**Response:**
```json
{
  "message": "Hello World"
}
```

### POST /chat

Send a message to the chatbot.

**Request:**
```json
{
  "message": "I want to buy electricity",
  "session_id": 1
}
```

**Response:**
```json
{
  "reply": "Hi! Are you looking to buy electricity or sell electricity?"
}
```

**Request schema:** `message` (string) – user's message; `session_id` (integer) – session identifier for conversation tracking.

**Response schema:** `reply` (string) – bot's response message.

## Testing

1. Start the server using `python chatbot.py`
2. In another terminal, test the health endpoint:
```bash
./curl_scripts/test_health.sh
```
3. Test a conversation:
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to buy", "session_id": 1}'
```

Scripts in `curl_scripts/`:
- **test_health.sh** – Test GET / endpoint
- **test_buyer_consultation.sh** – Complete buyer consultation flow (session_id=1)
- **test_seller_consultation.sh** – Complete seller consultation flow (session_id=2)
- **test_product_config.sh** – Full buyer + consultation + product configuration flow (session_id=1)
- **test_invalid_inputs.sh** – Validation (invalid email, phone, percentages) (session_id=3)
- **test_session_management.sh** – Session persistence across messages

Session IDs: buyer flows use 1, seller uses 2, invalid_inputs uses 3. You can run tests in any order without restarting the server.

Test complete user journeys:
- Buyer: consultation → product_config
- Seller: consultation only
- Invalid inputs and error handling
- Include both successful and error scenarios

## Files Reference
- Main implementation: [chatbot.py](./chatbot.py)
- Basic files: [README.md](./README.md), [requirements.txt](./requirements.txt)
- Curl scripts: [curl_scripts/](./curl_scripts/) (test_health.sh, test_buyer_consultation.sh, test_seller_consultation.sh, test_product_config.sh, test_invalid_inputs.sh, test_session_management.sh)
