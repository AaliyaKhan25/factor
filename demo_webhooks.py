"""Live demo of Factor's webhooks, no Instagram or courier account needed.

It plays the part of the outside world: a customer DM arriving, and a courier sending signed tracking events.
The app receives them through the same endpoints real services would call, so the inbox and the order
tracking update live on screen.

Usage (API must be running):
  python demo_webhooks.py --email you@example.com --password yourpass            # DM + courier events
  python demo_webhooks.py --email ... --password ... --only dm
  python demo_webhooks.py --email ... --password ... --only courier --order ORD-1001
Only the Python standard library is used.
"""
import argparse, hashlib, hmac, json, sys, time, urllib.error, urllib.request

p = argparse.ArgumentParser()
p.add_argument("--api", default="http://localhost:8000")
p.add_argument("--email", required=True)
p.add_argument("--password", required=True)
p.add_argument("--order", default="", help="order code such as ORD-1001 (default: newest order)")
p.add_argument("--only", choices=["dm", "courier"], default="")
p.add_argument("--pause", type=float, default=4.0, help="seconds between events, so the audience can watch")
a = p.parse_args()


def call(method, path, body=None, token="", headers=None):
    data = json.dumps(body).encode() if body is not None and not isinstance(body, bytes) else body
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(a.api + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} failed: {e.code} {e.read().decode()[:300]}")
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach {a.api}: {e.reason}. Is the API running?")


token = call("POST", "/auth/login", {"email": a.email, "password": a.password})["access_token"]

if a.only in ("", "dm"):
    print("1) A customer sends an Instagram DM (like Meta's webhook would deliver)...")
    call("POST", "/inbox/simulate", {"channel": "instagram", "handle": "@riya.crafts", "name": "Riya",
                                      "text": "Hi! Do you have the sage tote in stock? Can you ship to Pune?"}, token)
    print("   Open the Inbox: a new chat appeared. The agent answers what it safely can and flags the rest for you.")
    time.sleep(a.pause)

if a.only in ("", "courier"):
    orders = call("GET", "/orders", token=token)
    rows = orders if isinstance(orders, list) else orders.get("items") or orders.get("orders") or []
    order = next((o for o in rows if o["code"] == a.order), None) if a.order else (rows[0] if rows else None)
    if not order:
        sys.exit("No order found. Create one in the app first, or pass --order ORD-xxxx.")
    awb = "DEMO" + str(int(time.time()))[-8:]
    print(f"2) Connecting a demo courier and attaching AWB {awb} to {order['code']}...")
    conn = call("POST", "/couriers", {"name": "Demo Courier", "provider": "generic"}, token)
    call("PUT", f"/couriers/orders/{order['id']}/shipment",
         {"courier_name": "Demo Courier", "awb": awb, "courier_connection_id": conn["id"]}, token)
    print(f"   Keep the order page open: /orders/{order['id']}  (or the public page /track/{order['id']})")
    time.sleep(a.pause)
    secret = conn["webhook_secret"].encode()
    for i, (status, detail) in enumerate([("picked_up", "Picked up from seller"),
                                          ("in_transit", "Arrived at Indore hub"),
                                          ("out_for_delivery", "Out for delivery in Pune"),
                                          ("delivered", "Delivered. Signed by customer")], 1):
        body = json.dumps({"event_id": f"{awb}-{i}", "awb": awb, "status": status, "detail": detail}).encode()
        ts = str(int(time.time()))
        sig = hmac.new(secret, ts.encode() + b"." + body, hashlib.sha256).hexdigest()
        print(f"3.{i}) Courier webhook: {status}")
        call("POST", conn["webhook_path"], body, headers={"X-Courier-Timestamp": ts, "X-Courier-Signature": f"sha256={sig}"})
        time.sleep(a.pause)
    print("   Replaying the last event is ignored (duplicate), and a wrong signature is rejected. Try it in the Q&A.")
print("Done.")