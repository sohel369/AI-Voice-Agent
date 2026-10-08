import json
import logging
from config import OPENAI_API_KEY

logger = logging.getLogger("voice_bot")

def extract_with_openai(transcript: str, answers: dict) -> dict:
    """
    Extracts structured fields using OpenAI LLM (gpt-4o-mini).
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = (
            "You are an NLP data extraction assistant for an inbound phone lead qualification bot.\n"
            "Given the caller's answers to the 3 questions, extract the key structured data in valid JSON format.\n\n"
            "Questions and Responses:\n"
            f"1. Desired Service: {answers.get('desired_service', '')}\n"
            f"2. Company/Name: {answers.get('company_name', '')}\n"
            f"3. Contact Channel: {answers.get('contact_channel', '')}\n\n"
            "Return JSON matching this schema:\n"
            "{\n"
            '  "company_name": "clean company name or caller name",\n'
            '  "desired_service": "clean summary of the requested service",\n'
            '  "contact_channel": "email, phone, or preferred channel",\n'
            '  "lead_title": "concise descriptive lead title (e.g. Web Development - Acme Corp)"\n'
            "}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )

        content = response.choices[0].message.content
        extracted = json.loads(content)
        logger.info(f"OpenAI Extracted Data: {extracted}")
        return extracted

    except Exception as e:
        logger.warning(f"OpenAI extraction failed or unavailable ({e}). Using fallback extractor.")
        return fallback_extractor(answers)


def fallback_extractor(answers: dict) -> dict:
    """
    Direct rule-based extraction fallback if OpenAI API is not configured or fails.
    """
    desired_service = answers.get("desired_service", "").strip()
    company_name = answers.get("company_name", "").strip()
    contact_channel = answers.get("contact_channel", "").strip()

    title_parts = []
    if desired_service:
        title_parts.append(desired_service.title())
    if company_name:
        title_parts.append(company_name.title())

    lead_title = " - ".join(title_parts) if title_parts else "Inbound Phone Lead"

    return {
        "company_name": company_name or "Unknown Company",
        "desired_service": desired_service or "General Inquiry",
        "contact_channel": contact_channel or "Phone",
        "lead_title": lead_title
    }


def parse_call_data(answers: dict) -> dict:
    """
    Main entry point for parsing call data.
    """
    # Build a readable transcript string
    raw_transcript = (
        f"Q1 (Service): {answers.get('desired_service', 'N/A')}\n"
        f"Q2 (Company/Name): {answers.get('company_name', 'N/A')}\n"
        f"Q3 (Contact): {answers.get('contact_channel', 'N/A')}"
    )

    if OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"):
        parsed = extract_with_openai(raw_transcript, answers)
    else:
        logger.info("Using built-in parser (OpenAI API key not set).")
        parsed = fallback_extractor(answers)

    parsed["raw_transcript"] = raw_transcript
    return parsed
