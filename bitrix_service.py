import logging
import requests
from config import BITRIX24_WEBHOOK_URL

logger = logging.getLogger("voice_bot")

def push_lead_to_bitrix24(
    title: str,
    name: str = "",
    company_title: str = "",
    phone: str = "",
    contact_channel: str = "",
    desired_service: str = "",
    raw_transcript: str = "",
    webhook_url: str = None
) -> dict:
    """
    Sends structured lead information to Bitrix24 via its REST API (crm.lead.add).
    """
    target_url = webhook_url or BITRIX24_WEBHOOK_URL

    if not target_url or "your_token_here" in target_url:
        error_msg = "Bitrix24 Webhook URL is not configured. Please set BITRIX24_WEBHOOK_URL in .env"
        logger.warning(error_msg)
        return {"success": False, "error": error_msg}

    # Format comments section for full transparency in Bitrix24
    comments = (
        f"<b>🤖 Automated Voice Bot Lead</b><br/>"
        f"<b>Desired Service:</b> {desired_service or 'Not specified'}<br/>"
        f"<b>Company / Caller:</b> {company_title or name or 'Not specified'}<br/>"
        f"<b>Preferred Contact:</b> {contact_channel or 'Not specified'}<br/>"
        f"<hr/><b>Full Call Transcript:</b><br/>{raw_transcript or 'N/A'}"
    )

    fields = {
        "TITLE": title or f"Phone Lead from {phone or 'Unknown'}",
        "NAME": name or company_title or "Voice Lead",
        "COMMENTS": comments,
        "SOURCE_ID": "CALL",
        "SOURCE_DESCRIPTION": "AI Voice Bot Inbound Call"
    }

    if company_title:
        fields["COMPANY_TITLE"] = company_title

    if phone:
        fields["PHONE"] = [{"VALUE": phone, "VALUE_TYPE": "WORK"}]

    payload = {
        "fields": fields,
        "params": {"REGISTER_SONET_EVENT": "Y"}
    }

    try:
        logger.info(f"Pushing Lead to Bitrix24: {fields['TITLE']}")
        response = requests.post(target_url, json=payload, timeout=10)
        response_data = response.json()

        if response.status_code == 200 and "result" in response_data:
            lead_id = response_data["result"]
            logger.info(f"Successfully created Lead #{lead_id} in Bitrix24")
            return {"success": True, "lead_id": lead_id, "data": response_data}
        else:
            logger.error(f"Bitrix24 API Error: {response_data}")
            return {"success": False, "error": response_data}

    except Exception as e:
        logger.exception(f"Exception while connecting to Bitrix24: {e}")
        return {"success": False, "error": str(e)}
