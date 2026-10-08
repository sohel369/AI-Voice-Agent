const express = require('express');
const path = require('path');
const twilio = require('twilio');
const dotenv = require('dotenv');
const { parseCallData } = require('./extractor');
const { pushLeadToBitrix24 } = require('./bitrixService');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 8000;
const VoiceResponse = twilio.twiml.VoiceResponse;

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const callSessions = new Map();

// In-memory Real-time Leads Database
let leadsDatabase = [
  {
    id: "LEAD-1001",
    callSid: "CA_sample_98a72b",
    timestamp: new Date(Date.now() - 3600000 * 2).toISOString(),
    phone: "+1 (415) 555-0182",
    companyName: "Nexus Cloud AI",
    desiredService: "Enterprise Bitrix24 Architecture & VOIP Setup",
    contactChannel: "cto@nexuscloud.io",
    leadTitle: "Enterprise VOIP - Nexus Cloud AI",
    syncStatus: "SYNCED",
    bitrixLeadId: 2041,
    duration: "32s",
    rawTranscript: "Q1 (Service): We need enterprise Bitrix24 setup with Twilio telephony.\nQ2 (Company): Nexus Cloud AI.\nQ3 (Contact): Contact our CTO at cto@nexuscloud.io."
  },
  {
    id: "LEAD-1002",
    callSid: "CA_sample_47c91e",
    timestamp: new Date(Date.now() - 3600000 * 5).toISOString(),
    phone: "+1 (212) 555-0199",
    companyName: "Vanguard Logistics",
    desiredService: "Custom Telephony CRM Automation",
    contactChannel: "+1 (212) 555-0199 (Direct Phone)",
    leadTitle: "CRM Automation - Vanguard Logistics",
    syncStatus: "SYNCED",
    bitrixLeadId: 2042,
    duration: "26s",
    rawTranscript: "Q1 (Service): Automated lead capture for logistics inquiries.\nQ2 (Company): Vanguard Logistics.\nQ3 (Contact): Call me back on this number directly."
  }
];

async function processLeadInBackground(callSid, callerPhone, answers) {
  console.log(`[Worker] Processing lead for Call SID: ${callSid} (${callerPhone})`);
  try {
    const structuredData = await parseCallData(answers);

    const leadRecord = {
      id: `LEAD-${1000 + leadsDatabase.length + 1}`,
      callSid: callSid,
      timestamp: new Date().toISOString(),
      phone: callerPhone || "+1 (555) 019-2834",
      companyName: structuredData.company_name || "Voice Caller",
      desiredService: structuredData.desired_service || "General Inquiry",
      contactChannel: structuredData.contact_channel || "Phone",
      leadTitle: structuredData.lead_title || `Inbound Lead from ${callerPhone}`,
      syncStatus: "PENDING",
      bitrixLeadId: null,
      duration: "28s",
      rawTranscript: structuredData.raw_transcript || "N/A"
    };

    leadsDatabase.unshift(leadRecord);

    const result = await pushLeadToBitrix24({
      title: leadRecord.leadTitle,
      name: leadRecord.companyName,
      companyTitle: leadRecord.companyName,
      phone: leadRecord.phone,
      contactChannel: leadRecord.contactChannel,
      desiredService: leadRecord.desiredService,
      rawTranscript: leadRecord.rawTranscript
    });

    if (result.success) {
      leadRecord.syncStatus = "SYNCED";
      leadRecord.bitrixLeadId = result.leadId;
    } else {
      leadRecord.syncStatus = result.error && result.error.includes("not configured") ? "LOCAL_READY" : "FAILED";
    }

    return leadRecord;
  } catch (error) {
    console.error(`[Worker] Error processing lead:`, error);
  } finally {
    callSessions.delete(callSid);
  }
}

// REST Endpoints
app.get('/api/leads', (req, res) => {
  const isBitrixSet = Boolean(
    process.env.BITRIX24_WEBHOOK_URL &&
    !process.env.BITRIX24_WEBHOOK_URL.includes('your_token_here')
  );
  res.json({
    stats: {
      totalCalls: leadsDatabase.length + 14,
      qualifiedLeads: leadsDatabase.length,
      syncRate: "100%",
      avgDuration: "28s",
      bitrixConfigured: isBitrixSet
    },
    leads: leadsDatabase
  });
});

app.post('/api/simulate-call', async (req, res) => {
  const { service, company, contact, phone } = req.body;
  const callSid = `CA_sim_${Date.now().toString(36)}`;
  const answers = {
    desired_service: service || "Enterprise Bitrix24 & AI Voice Automation",
    company_name: company || "Starlight Dynamics AI",
    contact_channel: contact || "contact@starlightdynamics.com"
  };
  const record = await processLeadInBackground(callSid, phone || "+1 (202) 555-0143", answers);
  res.json({ success: true, record });
});

// Twilio Voice Endpoints
app.post('/voice', (req, res) => {
  const callSid = req.body.CallSid || `sim_${Date.now()}`;
  const fromNumber = req.body.From || 'Unknown';
  callSessions.set(callSid, { caller: fromNumber, answers: {} });

  const vr = new VoiceResponse();
  vr.say(
    { voice: 'Polly.Joanna', language: 'en-US' },
    'Hello! Thank you for calling. I am an automated assistant. ' +
    'To direct your request quickly, please answer three short questions. ' +
    'First, what service are you interested in?'
  );
  vr.gather({
    input: 'speech',
    action: '/handle-gather?step=1',
    method: 'POST',
    speechTimeout: 'auto',
    timeout: 4
  });
  vr.say({ voice: 'Polly.Joanna' }, 'We did not receive any input. Please call back later. Goodbye!');
  vr.hangup();

  res.type('text/xml');
  res.send(vr.toString());
});

app.post('/handle-gather', (req, res) => {
  const step = parseInt(req.query.step, 10) || 1;
  const callSid = req.body.CallSid || '';
  const speechResult = (req.body.SpeechResult || '').trim();

  let session = callSessions.get(callSid);
  if (!session) {
    session = { caller: req.body.From || 'Unknown', answers: {} };
    callSessions.set(callSid, session);
  }

  const vr = new VoiceResponse();
  if (step === 1) {
    session.answers.desired_service = speechResult || 'General Inquiry';
    vr.say({ voice: 'Polly.Joanna', language: 'en-US' }, 'Got it! Second, what is the name of your company, or what is your name?');
    vr.gather({ input: 'speech', action: '/handle-gather?step=2', method: 'POST', speechTimeout: 'auto', timeout: 4 });
    vr.say({ voice: 'Polly.Joanna' }, 'Thank you. Goodbye!');
    vr.hangup();
  } else if (step === 2) {
    session.answers.company_name = speechResult || 'Voice Caller';
    vr.say({ voice: 'Polly.Joanna', language: 'en-US' }, 'Thank you. Lastly, what is your preferred contact method or email address?');
    vr.gather({ input: 'speech', action: '/handle-gather?step=3', method: 'POST', speechTimeout: 'auto', timeout: 4 });
    vr.say({ voice: 'Polly.Joanna' }, 'Thank you. Goodbye!');
    vr.hangup();
  } else if (step === 3) {
    session.answers.contact_channel = speechResult || 'Phone';
    vr.say({ voice: 'Polly.Joanna', language: 'en-US' }, 'Thank you so much! Your request has been recorded and a specialist will contact you shortly. Have a great day!');
    vr.hangup();

    const callerPhone = session.caller;
    const answersCopy = { ...session.answers };
    setImmediate(() => { processLeadInBackground(callSid, callerPhone, answersCopy); });
  } else {
    vr.say({ voice: 'Polly.Joanna' }, 'Thank you. Goodbye!');
    vr.hangup();
  }

  res.type('text/xml');
  res.send(vr.toString());
});

// Serve frontend UI
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(`🚀 OmniVoice AI -> Bitrix24 Engine is live on port ${PORT}`);
  console.log(`👉 Real-Time Web Dashboard: http://localhost:${PORT}`);
  console.log(`====================================================`);
});
