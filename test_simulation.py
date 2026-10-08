"""
Interactive & Automated Call Simulator for Twilio -> Bitrix24 Pipeline
This script simulates the multi-step voice conversation and pushes a lead to Bitrix24.
"""
import sys
import os
import requests

SERVER_URL = "http://127.0.0.1:8000"

def test_health():
    print("\n[1] Checking Server Health...")
    try:
        r = requests.get(f"{SERVER_URL}/health")
        print(f"    Status: {r.status_code}")
        print(f"    Response: {r.json()}")
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"    [!] Error: Server is not running at {SERVER_URL}.")
        print("    Please start the server first using: python main.py or start.bat")
        return False

def simulate_full_call():
    print("\n[2] Simulating Incoming Phone Call Flow...")
    call_sid = "CA_simulated_test_" + os.urandom(4).hex()
    caller_number = "+12025550199"

    # Step 0: Incoming Call
    print(f"\n📞 Dialing into bot (CallSid: {call_sid}, From: {caller_number})...")
    r0 = requests.post(f"{SERVER_URL}/voice", data={"CallSid": call_sid, "From": caller_number})
    print(f"    Bot replied with TwiML (Q1: Desired Service). Status: {r0.status_code}")

    # Step 1: Caller answers Q1
    user_q1 = "We need custom CRM integration and cloud migration."
    print(f"\n🗣️ Caller says: \"{user_q1}\"")
    r1 = requests.post(f"{SERVER_URL}/handle-gather?step=1", data={
        "CallSid": call_sid,
        "SpeechResult": user_q1,
        "Confidence": "0.95"
    })
    print(f"    Bot replied with TwiML (Q2: Company/Name). Status: {r1.status_code}")

    # Step 2: Caller answers Q2
    user_q2 = "Apex Digital Labs"
    print(f"\n🗣️ Caller says: \"{user_q2}\"")
    r2 = requests.post(f"{SERVER_URL}/handle-gather?step=2", data={
        "CallSid": call_sid,
        "SpeechResult": user_q2,
        "Confidence": "0.98"
    })
    print(f"    Bot replied with TwiML (Q3: Contact method). Status: {r2.status_code}")

    # Step 3: Caller answers Q3
    user_q3 = "Reach us at contact@apexdigital.com or this number"
    print(f"\n🗣️ Caller says: \"{user_q3}\"")
    r3 = requests.post(f"{SERVER_URL}/handle-gather?step=3", data={
        "CallSid": call_sid,
        "SpeechResult": user_q3,
        "Confidence": "0.96"
    })
    print(f"    Bot completed call & hung up. Status: {r3.status_code}")
    print("\n✅ Simulated call finished! Lead is now being processed in background.")
    print("👉 Check your Bitrix24 CRM Leads or console logs to see the new record!\n")

if __name__ == "__main__":
    print("==================================================")
    print("  Twilio Voice -> Bitrix24 Pipeline Simulator     ")
    print("==================================================")
    if test_health():
        simulate_full_call()
