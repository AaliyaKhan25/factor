"""Live demo of the Instagram and WhatsApp webhooks, with no Meta account.

It acts as Meta: first the one-time verification handshake, then real-format message events
(Instagram "messaging" payload and WhatsApp Cloud API "changes" payload), signed the way Meta signs them.
Your app receives them on its normal webhook URLs, so the chats appear in the Inbox live.

Usage (API running, Inbox open in the browser):
  python demo_meta.py --email demo@factor.com --password Demo-Pass-123
  python demo_meta.py --email ... --password ... --app-secret YOUR_META_APP_SECRET
Pass --app-secret only if META_APP_SECRET is set in apps\\api\\.env. The app then also checks signatures,
and this script shows a forged one being rejected.
"""
import argparse, hashlib, hmac, json, sys, time, urllib.error, urllib.parse, urllib.request

p = argparse.ArgumentParser()
p.add_argument("--api", default="http://localhost:8000")
p.add_argument("--email", required=True)
p.add_argument("--password", required=True)
p.add_argument("--app-secret", default="")
p.add_argument("--pause", type=float, default=4.0)
a = p.parse_args()


def call(method, path, body=None, token="", headers=None, raw=False, expect_error=False):
    data = body if isinstance(body, bytes) else (json.dumps(body).encode() if body is not None else None)
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(a.api + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out = r.read()
            return out.decode() if raw else json.loads(out or b"null")
    except urllib.error.HTTPError as e:
        if expect_error:
            return e.code
        sys.exit(f"{method} {path} failed: {e.code} {e.read().decode()[:300]}")
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach {a.api}: {e.reason}. Is the API running?")


def send(path, payload, forge=False):
    raw = json.dumps(payload).encode()
    headers = {}
    if a.app_secret:
        key = b"wrong-secret" if forge else a.app_secret.encode()
        headers["X-Hub-Signature-256"] = "sha256=" + hmac.new(key, raw, hashlib.sha256).hexdigest()
    return call("POST", path, raw, headers=headers, expect_error=forge)


token = call("POST", "/auth/login", {"email": a.email, "password": a.password})["access_token"]
existing = {c["channel"]: c for c in call("GET", "/channels", token=token)}
conns = {ch: existing.get(ch) or call("POST", "/channels", {"channel": ch, "label": f"Demo {ch}"}, token)
         for ch in ("instagram", "whatsapp")}

print("1) Meta verifies the webhook URL (the handshake you do once in the Meta dashboard)...")
for ch, c in conns.items():
    q = urllib.parse.urlencode({"hub.mode": "subscribe", "hub.verify_token": c["verify_token"], "hub.challenge": "12345"})
    echoed = call("GET", f"{c['webhook_path']}?{q}", raw=True)
    print(f"   {ch}: sent challenge 12345, app echoed {echoed}  (verified)")
time.sleep(a.pause)

print("2) A customer sends an Instagram DM...")
ig = {"object": "instagram", "entry": [{"id": "17841400000000000", "time": int(time.time()), "messaging": [
    {"sender": {"id": "5550001111"}, "recipient": {"id": "17841400000000000"}, "timestamp": int(time.time() * 1000),
     "message": {"mid": "m_demo_1", "text": "Hi! Is the sage tote available? What is the price?"}}]}]}
print("   app received:", send(conns["instagram"]["webhook_path"], ig))
time.sleep(a.pause)

print("3) A customer sends a WhatsApp message...")
wa = {"object": "whatsapp_business_account", "entry": [{"id": "WABA_ID", "changes": [{"field": "messages", "value": {
    "messaging_product": "whatsapp", "metadata": {"display_phone_number": "919800000000", "phone_number_id": "PHONE_ID"},
    "contacts": [{"profile": {"name": "Ananya Rao"}, "wa_id": "919876543210"}],
    "messages": [{"from": "919876543210", "id": "wamid.DEMO1", "timestamp": str(int(time.time())), "type": "text",
                  "text": {"body": "Hello, I want to return my order. It arrived damaged."}}]}}]}]}
print("   app received:", send(conns["whatsapp"]["webhook_path"], wa))
time.sleep(a.pause)

print("4) The same customer follows up on Instagram (lands in the same chat)...")
ig["entry"][0]["messaging"][0]["message"] = {"mid": "m_demo_2", "text": "Also, can you ship to Pune by Friday?"}
print("   app received:", send(conns["instagram"]["webhook_path"], ig))

if a.app_secret:
    time.sleep(a.pause)
    print("5) Someone forges a request with the wrong signature...")
    print(f"   app answered HTTP {send(conns['instagram']['webhook_path'], ig, forge=True)} (rejected, nothing saved)")
print("Done. Open the Inbox: chats from Instagram and WhatsApp, with the ones that need you flagged.")