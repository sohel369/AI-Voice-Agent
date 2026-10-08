const axios = require('axios');

const SERVER_URL = 'http://127.0.0.1:8000';

async function runSimulation() {
  console.log('==================================================');
  console.log('  📞 Twilio Voice -> Bitrix24 Simulation (Node.js)');
  console.log('==================================================\n');

  try {
    // 1. Health check
    const health = await axios.get(`${SERVER_URL}/health`);
    console.log('[1] Server Health:', health.data);
  } catch (e) {
    console.error(`[!] Server is not reachable at ${SERVER_URL}. Make sure 'npm start' or 'npm run dev' is running.`);
    return;
  }

  const callSid = `CA_test_${Date.now()}`;
  const callerPhone = '+12025550199';

  console.log(`\n[2] Simulating Call (CallSid: ${callSid}, From: ${callerPhone})...`);

  // Step 0: Initial call
  console.log(' -> Dialing into bot...');
  await axios.post(`${SERVER_URL}/voice`, new URLSearchParams({ CallSid: callSid, From: callerPhone }));
  console.log('    Bot answered & asked Q1 (Desired Service).');

  // Step 1: Answer Q1
  const q1Text = 'We need full Bitrix24 setup and telephony integration';
  console.log(`\n🗣️ Caller says: "${q1Text}"`);
  await axios.post(`${SERVER_URL}/handle-gather?step=1`, new URLSearchParams({
    CallSid: callSid,
    SpeechResult: q1Text
  }));
  console.log('    Bot acknowledged & asked Q2 (Company name).');

  // Step 2: Answer Q2
  const q2Text = 'Starline International';
  console.log(`\n🗣️ Caller says: "${q2Text}"`);
  await axios.post(`${SERVER_URL}/handle-gather?step=2`, new URLSearchParams({
    CallSid: callSid,
    SpeechResult: q2Text
  }));
  console.log('    Bot acknowledged & asked Q3 (Contact info).');

  // Step 3: Answer Q3
  const q3Text = 'sales@starline.com or call me back on this number';
  console.log(`\n🗣️ Caller says: "${q3Text}"`);
  await axios.post(`${SERVER_URL}/handle-gather?step=3`, new URLSearchParams({
    CallSid: callSid,
    SpeechResult: q3Text
  }));
  console.log('    Bot completed call & hung up.');

  console.log('\n✅ Call simulation finished!');
  console.log('👉 Check your server terminal and Bitrix24 Leads to see the new record.\n');
}

runSimulation();
