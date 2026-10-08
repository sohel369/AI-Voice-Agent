const axios = require('axios');
require('dotenv').config();

/**
 * Pushes lead information to Bitrix24 via REST API (crm.lead.add)
 */
async function pushLeadToBitrix24({
  title,
  name = '',
  companyTitle = '',
  phone = '',
  contactChannel = '',
  desiredService = '',
  rawTranscript = ''
}) {
  const webhookUrl = process.env.BITRIX24_WEBHOOK_URL;

  if (!webhookUrl || webhookUrl.includes('your_token_here')) {
    const errorMsg = 'Bitrix24 Webhook URL is not configured. Please check .env file.';
    console.warn(`[WARN] ${errorMsg}`);
    return { success: false, error: errorMsg };
  }

  const comments = `
    <b>🤖 Automated Voice Bot Lead</b><br/>
    <b>Desired Service:</b> ${desiredService || 'Not specified'}<br/>
    <b>Company / Caller:</b> ${companyTitle || name || 'Not specified'}<br/>
    <b>Preferred Contact:</b> ${contactChannel || 'Not specified'}<br/>
    <hr/><b>Full Call Transcript:</b><br/>${(rawTranscript || 'N/A').replace(/\n/g, '<br/>')}
  `.trim();

  const fields = {
    TITLE: title || `Phone Lead from ${phone || 'Unknown'}`,
    NAME: name || companyTitle || 'Voice Lead',
    COMMENTS: comments,
    SOURCE_ID: 'CALL',
    SOURCE_DESCRIPTION: 'AI Voice Bot Inbound Call'
  };

  if (companyTitle) {
    fields.COMPANY_TITLE = companyTitle;
  }

  if (phone) {
    fields.PHONE = [{ VALUE: phone, VALUE_TYPE: 'WORK' }];
  }

  const payload = {
    fields,
    params: { REGISTER_SONET_EVENT: 'Y' }
  };

  try {
    console.log(`[Bitrix24] Pushing Lead: "${fields.TITLE}"`);
    const response = await axios.post(webhookUrl, payload, { timeout: 10000 });

    if (response.status === 200 && response.data && response.data.result) {
      const leadId = response.data.result;
      console.log(`[Bitrix24] ✅ Successfully created Lead #${leadId}`);
      return { success: true, leadId, data: response.data };
    } else {
      console.error('[Bitrix24] API Error:', response.data);
      return { success: false, error: response.data };
    }
  } catch (error) {
    const errMessage = error.response ? JSON.stringify(error.response.data) : error.message;
    console.error(`[Bitrix24] ❌ Connection error: ${errMessage}`);
    return { success: false, error: errMessage };
  }
}

module.exports = { pushLeadToBitrix24 };
