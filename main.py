import logging
from typing import Optional
from fastapi import FastAPI, Request, Form, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, JSONResponse
from twilio.twiml.voice_response import VoiceResponse, Gather

from config import PORT, HOST, BITRIX24_WEBHOOK_URL
from extractor import parse_call_data
from bitrix_service import push_lead_to_bitrix24

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("voice_bot")

app = FastAPI(
    title="Twilio Voice to Bitrix24 Bot",
    description="Automated phone call bot that gathers caller info and creates leads in Bitrix24",
    version="1.0.0"
)

# In-memory session store for active calls
# Format: { call_sid: { "caller": str, "answers": {} } }
call_sessions = {}


def process_lead_in_background(call_sid: str, caller_phone: str, answers: dict):
    """
    Background worker that runs NLP extraction and writes to Bitrix24.
    """
    logger.info(f"Processing lead for Call SID: {call_sid} (Caller: {caller_phone})")
    try:
        # Step 1: Parse and structure the call data
        structured_data = parse_call_data(answers)

        # Step 2: Push to Bitrix24 REST API
        result = push_lead_to_bitrix24(
            title=structured_data.get("lead_title", f"Lead from {caller_phone}"),
            name=structured_data.get("company_name", "Voice Caller"),
            company_title=structured_data.get("company_name", ""),
            phone=caller_phone,
            contact_channel=structured_data.get("contact_channel", ""),
            desired_service=structured_data.get("desired_service", ""),
            raw_transcript=structured_data.get("raw_transcript", "")
        )

        logger.info(f"Lead creation result for {call_sid}: {result}")
    except Exception as e:
        logger.exception(f"Error processing lead in background: {e}")
    finally:
        # Clean up memory session
        call_sessions.pop(call_sid, None)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Twilio Voice to Bitrix24 Automated Bot",
        "endpoints": {
            "twilio_voice_webhook": "/voice",
            "health_check": "/health",
            "test_bitrix_lead": "/test-lead"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "bitrix_configured": bool(BITRIX24_WEBHOOK_URL and "your_token_here" not in BITRIX24_WEBHOOK_URL)
    }


@app.post("/voice")
async def voice_entry(
    request: Request,
    CallSid: str = Form(...),
    From: Optional[str] = Form("")
):
    """
    Step 1: Twilio Inbound Call Entry Point.
    Plays TTS greeting and asks Question 1 (Desired Service).
    """
    logger.info(f"Incoming Call received. SID: {CallSid}, From: {From}")

    # Initialize call session
    call_sessions[CallSid] = {
        "caller": From or "Unknown",
        "answers": {}
    }

    vr = VoiceResponse()
    vr.say(
        "Hello! Thank you for calling. I am an automated assistant. "
        "To direct you to the right department, please answer three quick questions. "
        "First, what service are you interested in?",
        voice="Polly.Joanna",
        language="en-US"
    )

    # Gather speech response for Question 1
    gather = Gather(
        input="speech",
        action="/handle-gather?step=1",
        method="POST",
        speechTimeout="auto",
        timeout=4
    )
    vr.append(gather)

    # If no speech is detected, retry
    vr.say("We did not receive any input. Please call back later. Goodbye!", voice="Polly.Joanna")
    vr.hangup()

    return Response(content=str(vr), media_type="application/xml")


@app.post("/handle-gather")
async def handle_gather(
    step: int,
    background_tasks: BackgroundTasks,
    CallSid: str = Form(...),
    SpeechResult: Optional[str] = Form(""),
    Confidence: Optional[str] = Form(None)
):
    """
    Handles speech responses for questions and steps to the next question.
    """
    logger.info(f"Gather Step {step} for CallSid {CallSid}. SpeechResult: '{SpeechResult}' (Confidence: {Confidence})")

    session = call_sessions.get(CallSid)
    if not session:
        # Recreate session if missing
        session = {"caller": "Unknown", "answers": {}}
        call_sessions[CallSid] = session

    vr = VoiceResponse()
    recognized_text = (SpeechResult or "").strip()

    if step == 1:
        # Question 1 answered: Desired Service -> Ask Question 2: Company/Name
        session["answers"]["desired_service"] = recognized_text or "General Inquiry"

        vr.say(
            "Got it! Second, what is the name of your company, or what is your name?",
            voice="Polly.Joanna",
            language="en-US"
        )
        gather = Gather(
            input="speech",
            action="/handle-gather?step=2",
            method="POST",
            speechTimeout="auto",
            timeout=4
        )
        vr.append(gather)
        vr.say("Thank you. Goodbye!", voice="Polly.Joanna")
        vr.hangup()

    elif step == 2:
        # Question 2 answered: Company/Name -> Ask Question 3: Contact details
        session["answers"]["company_name"] = recognized_text or "Voice Caller"

        vr.say(
            "Thank you. Lastly, what is your preferred contact method or email address?",
            voice="Polly.Joanna",
            language="en-US"
        )
        gather = Gather(
            input="speech",
            action="/handle-gather?step=3",
            method="POST",
            speechTimeout="auto",
            timeout=4
        )
        vr.append(gather)
        vr.say("Thank you. Goodbye!", voice="Polly.Joanna")
        vr.hangup()

    elif step == 3:
        # Question 3 answered: Contact Channel -> Complete call & push to Bitrix24
        session["answers"]["contact_channel"] = recognized_text or "Phone"

        vr.say(
            "Thank you so much! Your request has been recorded and a specialist will contact you shortly. Have a great day!",
            voice="Polly.Joanna",
            language="en-US"
        )
        vr.hangup()

        # Trigger Bitrix24 lead push asynchronously
        caller_phone = session.get("caller", "")
        answers_copy = dict(session.get("answers", {}))
        background_tasks.add_task(process_lead_in_background, CallSid, caller_phone, answers_copy)

    else:
        vr.say("Thank you. Goodbye!", voice="Polly.Joanna")
        vr.hangup()

    return Response(content=str(vr), media_type="application/xml")


@app.post("/test-lead")
async def test_lead(
    service: str = "Web Design & Development",
    company: str = "Acme Global Solutions",
    phone: str = "+12025550143",
    contact: str = "john.doe@example.com"
):
    """
    Direct test endpoint to verify Bitrix24 integration without calling via phone.
    """
    test_answers = {
        "desired_service": service,
        "company_name": company,
        "contact_channel": contact
    }

    parsed = parse_call_data(test_answers)
    result = push_lead_to_bitrix24(
        title=parsed.get("lead_title", f"Test Lead - {company}"),
        name=parsed.get("company_name", company),
        company_title=parsed.get("company_name", company),
        phone=phone,
        contact_channel=parsed.get("contact_channel", contact),
        desired_service=parsed.get("desired_service", service),
        raw_transcript=parsed.get("raw_transcript", "Manual test lead")
    )
    return {
        "status": "tested",
        "parsed_data": parsed,
        "bitrix_response": result
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
