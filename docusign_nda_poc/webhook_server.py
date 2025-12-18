#!/usr/bin/env python3
"""
DocuSign Webhook Test Server

A simple FastAPI server for testing DocuSign Connect webhooks locally.
Use with ngrok to expose this server to the internet.

Usage:
    # Start the server
    uv run docusign_nda_poc/webhook_server.py

    # In another terminal, expose with ngrok
    ngrok http 8000

    # Configure DocuSign Connect with the ngrok URL:
    # https://xxxx.ngrok.io/webhook/docusign
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from docusign_nda_poc.services.webhook_service import WebhookService
from docusign_nda_poc.models.webhook_event import WebhookEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DocuSign Webhook Test Server",
    description="Test server for receiving DocuSign Connect webhooks",
    version="1.0.0",
)

# Initialize webhook service
# TODO: Set HMAC key for production use
webhook_service = WebhookService(hmac_key=None)

# Directory to save received webhooks and signed PDFs
OUTPUT_DIR = Path(__file__).parent / "webhook_output"
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "DocuSign Webhook Test Server is running",
        "webhook_endpoint": "/webhook/docusign",
    }


@app.post("/webhook/docusign")
async def receive_webhook(
    request: Request,
    x_docusign_signature_1: Optional[str] = Header(None),
):
    """
    Receive DocuSign Connect webhook.

    DocuSign sends envelope status change notifications here.
    """
    # Get raw body for signature verification
    body = await request.body()

    # Log received webhook
    logger.info(f"Received webhook, size: {len(body)} bytes")

    # Verify signature if configured
    if x_docusign_signature_1:
        if not webhook_service.verify_signature(body, x_docusign_signature_1):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        # DocuSign can send XML or JSON. We expect JSON here.
        # If XML, you'll need to configure DocuSign Connect to send JSON.
        payload = await request.json()
    except json.JSONDecodeError:
        # Try to decode as string (might be XML)
        body_str = body.decode("utf-8")
        if body_str.startswith("<?xml"):
            logger.warning("Received XML payload. Please configure DocuSign Connect to send JSON.")
            # Save XML for debugging
            save_webhook_data({"raw_xml": body_str}, "xml_payload")
            return JSONResponse(
                status_code=200,
                content={"message": "XML received but JSON preferred"},
            )
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Save raw payload for debugging
    save_webhook_data(payload, "raw")

    # Parse event
    try:
        event = webhook_service.parse_event(payload)
        logger.info(f"Parsed event: {event.event}, envelope: {event.envelope_id}, status: {event.status}")
    except Exception as e:
        logger.error(f"Failed to parse webhook event: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse event: {e}")

    # Handle event
    result = webhook_service.handle_event_sync(event)
    logger.info(f"Webhook result: {result.message}")

    # Save processed result
    save_webhook_data(
        {
            "envelope_id": result.envelope_id,
            "event_type": result.event_type,
            "message": result.message,
            "signer_email": result.signer_email,
            "signer_name": result.signer_name,
            "processed_at": datetime.now().isoformat(),
        },
        "processed",
    )

    # If completed, save signed PDF info
    if event.is_completed:
        try:
            signed_pdf = webhook_service.envelope_service.get_signed_document(event.envelope_id)
            pdf_path = OUTPUT_DIR / f"signed_{event.envelope_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(signed_pdf)
            logger.info(f"Saved signed PDF to: {pdf_path}")
        except Exception as e:
            logger.error(f"Failed to save signed PDF: {e}")

    return JSONResponse(
        status_code=200,
        content={
            "success": result.success,
            "envelope_id": result.envelope_id,
            "event": result.event_type,
            "message": result.message,
        },
    )


def save_webhook_data(data: dict, prefix: str):
    """Save webhook data to file for debugging"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = OUTPUT_DIR / f"{prefix}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Saved webhook data to: {filename}")


@app.get("/webhooks")
async def list_webhooks():
    """List received webhooks"""
    files = sorted(OUTPUT_DIR.glob("*.json"), reverse=True)[:20]
    webhooks = []
    for f in files:
        try:
            with open(f, "r") as file:
                data = json.load(file)
                webhooks.append({
                    "filename": f.name,
                    "data": data,
                })
        except Exception:
            pass
    return {"webhooks": webhooks}


@app.get("/webhooks/{filename}")
async def get_webhook(filename: str):
    """Get specific webhook data"""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Webhook not found")

    with open(filepath, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DocuSign Webhook Test Server")
    print("=" * 60)
    print("\nServer starting on http://localhost:8000")
    print("\nTo test webhooks:")
    print("  1. Install ngrok: https://ngrok.com/download")
    print("  2. Run: ngrok http 8000")
    print("  3. Configure DocuSign Connect with URL:")
    print("     https://xxxx.ngrok.io/webhook/docusign")
    print("\nEndpoints:")
    print("  GET  /                 - Health check")
    print("  POST /webhook/docusign - Webhook receiver")
    print("  GET  /webhooks         - List received webhooks")
    print("\n" + "=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
