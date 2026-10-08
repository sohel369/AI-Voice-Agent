const OpenAI = require('openai');
require('dotenv').config();

const openaiApiKey = process.env.OPENAI_API_KEY ? process.env.OPENAI_API_KEY.trim() : '';

/**
 * Fallback parser if OpenAI key is not provided
 */
function fallbackExtractor(answers) {
  const desiredService = (answers.desired_service || '').trim();
  const companyName = (answers.company_name || '').trim();
  const contactChannel = (answers.contact_channel || '').trim();

  const titleParts = [];
  if (desiredService) titleParts.push(desiredService);
  if (companyName) titleParts.push(companyName);

  const leadTitle = titleParts.length > 0 ? titleParts.join(' - ') : 'Inbound Phone Lead';

  return {
    company_name: companyName || 'Unknown Company',
    desired_service: desiredService || 'General Inquiry',
    contact_channel: contactChannel || 'Phone',
    lead_title: leadTitle
  };
}

/**
 * Uses OpenAI to extract structured JSON data from the caller's answers
 */
async function extractWithOpenAI(transcript, answers) {
  try {
    const openai = new OpenAI({ apiKey: openaiApiKey });

    const prompt = `You are an NLP extraction assistant for an inbound phone lead qualification bot.
Given the caller's answers to the 3 questions, extract the key structured data in valid JSON.

Questions and Responses:
1. Desired Service: ${answers.desired_service || ''}
2. Company/Name: ${answers.company_name || ''}
3. Contact Channel: ${answers.contact_channel || ''}

Return JSON matching this schema:
{
  "company_name": "clean company name or caller name",
  "desired_service": "clean summary of the requested service",
  "contact_channel": "email, phone, or preferred channel",
  "lead_title": "concise descriptive lead title"
}`;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: prompt }],
      response_format: { type: 'json_object' },
      temperature: 0.2
    });

    const parsed = JSON.parse(completion.choices[0].message.content);
    console.log('[NLP] OpenAI Extracted Data:', parsed);
    return parsed;
  } catch (err) {
    console.warn(`[NLP] OpenAI extraction failed (${err.message}). Using fallback.`);
    return fallbackExtractor(answers);
  }
}

/**
 * Main parser entry point
 */
async function parseCallData(answers) {
  const rawTranscript = [
    `Q1 (Service): ${answers.desired_service || 'N/A'}`,
    `Q2 (Company/Name): ${answers.company_name || 'N/A'}`,
    `Q3 (Contact): ${answers.contact_channel || 'N/A'}`
  ].join('\n');

  let extracted;
  if (openaiApiKey && openaiApiKey.startsWith('sk-')) {
    extracted = await extractWithOpenAI(rawTranscript, answers);
  } else {
    extracted = fallbackExtractor(answers);
  }

  extracted.raw_transcript = rawTranscript;
  return extracted;
}

module.exports = { parseCallData, fallbackExtractor };
