'''
FastAPI chatbot MVP

- FastApi: Python web framework to build APIs
- Uvicorn: ASGI server used to run the FastAPI app
- Pydantic: data validation library for Python
'''

import asyncio

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
# from google import genai

app = FastAPI()

# client = genai.Client(api_key='GEMINI_API_KEY')

# HTTP methods fot RESTful API

@app.get("/")
def root():
    return {"message": "Hello World"}

class ChatRequest(BaseModel):
    message: str
    session_id: int

class ChatResponse(BaseModel):
    reply: str

sessions = {}

def detect_client_type(session, message):
    if session["client_type"] is not None:
        return None
    msg = message.lower()
    if "buy" in msg:
        session["client_type"] = "buyer"
        return None
    if "sell" in msg:
        session["client_type"] = "seller"
        return None
    session["state"] = "ask_client_type"
    return "Hi! Are you looking to buy electricity or sell electricity?"

def get_allowed_flows(session):
    if session["client_type"] == "buyer":
        return ["product_config", "operational"]
    else:
        return ["consultation", "operational"]

# This router could later be replaced by an intent classifier.
def detect_flow(session, message):
    msg = message.lower()
    allowed_flows = get_allowed_flows(session)
    if "consult" in msg or "contact" in msg or "discuss" in msg:
        return "consultation" if "consultation" in allowed_flows else None
    if "renewable" in msg or "price" in msg or "cost" in msg or "ratio" in msg:
        return "product_config" if "product_config" in allowed_flows else None
    if "history" in msg or "matching" in msg:
        return "operational" if "operational" in allowed_flows else None
    return None

# This could later be replaced by Google's libphonenumber.
def is_valid_phone(phone):
    if not phone:
        return False
    digit_count = 0
    prev_was_digit = False
    start = 0
    if phone[0] == "+":
        start = 1
    for c in phone[start:]:
        if c.isdigit():
            digit_count += 1
            prev_was_digit = True
        elif c == "-":
            if not prev_was_digit:
                return False
            prev_was_digit = False
        else:
            return False
    return digit_count >= 8 and prev_was_digit


# Could be refactored into a table-driven flow later
def handle_consultation(session, message):
    state = session["state"]
    if state == "start":
        session["state"] = "ask_topic"
        return "What would you like to consult about?"
    if state == "ask_topic":
        session["context"]["topic"] = message
        session["state"] = "ask_name"
        return "May I have the name of the person in charge?"
    if state == "ask_name":
        session["context"]["name"] = message
        session["state"] = "ask_email"
        return "What is your email address?"
    if state == "ask_email":
        if "@" not in message:
            return "That doesn't look like a valid email. Could you try again?"
        session["context"]["email"] = message
        session["state"] = "ask_phone"
        return "What is your phone number?"
    if state == "ask_phone":
        if not is_valid_phone(message):
            return "That doesn't look like a valid phone number. Please try again."
        session["context"]["phone"] = message
        session["state"] = "ask_company"
        return "Which company are you representing?"
    if state == "ask_company":
        session["context"]["company"] = message
        session["state"] = "ask_company_url"
        return "What is your company's website?"
    if state == "ask_company_url":
        session["context"]["company_url"] = message
        session["state"] = "ask_address"
        return "What is your company address?"
    if state == "ask_address":
        session["context"]["address"] = message
        session["state"] = "ask_additional_info"
        return "Any additional info you'd like to share?"
    if state == "ask_additional_info":
        session["context"]["additional_info"] = message
        session["state"] = "done"
        session["context_complete"] = True
        if session["client_type"] == "buyer":
            session["flow"] = "product_config"
            session["state"] = "start"
            return handle_product_config(session, message)
    return (
        "Thank you. We've received your consultation request "
        "and will contact you shortly."
    )

VALID_SOURCES = {"solar", "wind", "hydro", "thermal"}

def parse_sources(message):
    msg = message.lower()
    selected = []
    for source in VALID_SOURCES:
        if source in msg:
            selected.append(source)
    return selected

def handle_product_config(session, message):
    state = session["state"]
    if state == "start":
        session["state"] = "ask_power_sources"
        return (
            "Which power sources are you interested in?\n"
            "You can choose multiple: solar, wind, hydro, thermal."
        )
    if state == "ask_power_sources":
        sources = parse_sources(message)
        if not sources:
            return "Please choose atleast one: solar, wind, hydro, thermal"
        session["context"]["power_sources"] = sources
        session["state"] = "ask_fixed_price"
        return "What percentage should be fixed price?"
    if state == "ask_fixed_price":
        if not message.isdigit():
            return "Please enter a number between 0 and 100."
        session["context"]["fixed_price"] = int(message)
        session["state"] = "ask_market_price"
        return "What percentage should be market price?"
    if state == "ask_market_price":
        if not message.isdigit():
            return "Please enter a number between 0 and 100."
        market = int(message)
        fixed = session["context"]["fixed_price"]
        if fixed + market != 100:
            session["state"] = "ask_fixed_price"
            return (
                "Fixed price and market price should add upto 100%"
                "What percentage should be fixed price?"
            )
        session["context"]["market_price"] = market
        session["state"] = "ask_renewable_ratio"
        return "What percentage of renewable energy do you want?"
    if state == "ask_renewable_ratio":
        if not message.isdigit():
            return "Please enter a number between 0 and 100."
        value = int(message)
        if not (0 <= value <= 100):
            return "Please enter a number between 0 and 100."
        session["context"]["renewable_ratio"] = value
        session["state"] = "confirm"
        return f"""Please confirm with 'yes' or 'no':
Power sources: {session['context']['power_sources']}
Fixed price: {session['context']['fixed_price']}%
Market price: {session['context']['market_price']}%
Renewable ratio: {session['context']['renewable_ratio']}%
Non-renewable ratio: {100 - session['context']['renewable_ratio']}%"""
    if state == "confirm":
        msg = message.lower()
        if msg != "yes" and msg != "no":
            return ('confirm with "yes" or "no"')
        elif msg == "no":
            session["state"] = "ask_power_sources"
            return (
            "Which power sources are you interested in?"
            "You can choose multiple: solar, wind, hydro, thermal."
        )
        else:
            return "Product configurations saved!" 
    return None

def handle_operational(session, message):
    return "You need to login for further inquiry."

def handle_message(message, session_id):
    session = sessions.setdefault(session_id, {
        "client_type": None,
        "flow": None,
        "state": None,
        "context": {},
        "context_complete": False,
        "history": []
    })
    session["history"].append(message)
    reply = detect_client_type(session, message)
    if reply:
        return reply
    if session["flow"] is None:
        session["flow"] = detect_flow(session, message) or "consultation"
        session["state"] = "start"
    if session["flow"] == "product_config" and not session.get("context_complete"):
        session["flow"] = "consultation"
        session["state"] = "start"
        return "Before configuring products, please give us some info about you"
    if session["flow"] == "consultation":
        return handle_consultation(session, message)
    if session["flow"] == "product_config":
        return handle_product_config(session, message)
    return handle_operational(session, message)
# maybe remove operational altogether fo MVP?

# stub for ai fallback
# https://github.com/googleapis/python-genai
# 1. Obtaining an API key from Google AI Studio.
# 2. Installing the google-genai Python library (pip install google-genai).
# 3. Setting your API key as an environment variable.
# 4. Then, you can start experimenting with calling the Gemini API from your chatbot.py to generate responses or classify user intents.
def ai_fallback(message, context):
    response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents={'text': 'Why is the sky blue?'},
    config={
        'temperature': 0,
        'top_p': 0.95,
        'top_k': 20,
    },
)

# #region agent log
DEBUG_LOG = "/Users/kiru/Documents/CS/digital_grid/.cursor/debug.log"
def _debug_log(msg: str, data: dict, hypothesis_id: str):
    import json
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(json.dumps({"location": "chatbot.py:chat", "message": msg, "data": data, "hypothesisId": hypothesis_id, "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass
# #endregion

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # # #region agent log
    # _debug_log("chat request", {"session_id": req.session_id, "message": req.message}, "H1")
    # # #endregion
    reply = handle_message(req.message, req.session_id)
    # # #region agent log
    # s = sessions.get(req.session_id, {})
    # _debug_log("after handle_message", {"session_id": req.session_id, "client_type": s.get("client_type"), "flow": s.get("flow"), "state": s.get("state"), "context_complete": s.get("context_complete"), "reply_preview": (reply[:60] + "..." if reply and len(reply) > 60 else reply)}, "H2")
    # # #endregion
    return ChatResponse(reply=reply)

async def main():
    '''Run Uvicorn programmatically'''
    config = uvicorn.Config("chatbot:app", port=8000)
    # use reload=True if not production?
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")