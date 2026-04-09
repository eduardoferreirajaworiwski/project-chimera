import uvicorn
import os
import httpx
import logging
import re
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [CHIMERA-CORE] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Chimera")

# Configuration
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
MAX_REQUEST_SIZE = 1024 * 50  # 50KB limit for trap triggers
SUSPICIOUS_UA_PATTERNS = [
    r"sqlmap", r"nmap", r"nikto", r"dirbuster", r"gobuster", r"zgrab", r"masscan"
]

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Project Chimera", docs_url=None, redoc_url=None) # Disable docs to hide API
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- SECURITY MIDDLEWARES ---

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["Server"] = "Hidden" # Obfuscate server identity
        return response

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_REQUEST_SIZE:
                logger.warning(f"Payload too large from {request.client.host}")
                return Response(content="Payload Too Large", status_code=413)
        return await call_next(request)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ANSI Color Codes
RED = "\033[1;91m"
YELLOW = "\033[1;93m"
CYAN = "\033[1;36m"
RESET = "\033[0m"

def sanitize_input(text: str) -> str:
    return "".join(char for char in text if char.isprintable())[:500]

def is_suspicious_ua(ua: str) -> bool:
    return any(re.search(pattern, ua, re.IGNORECASE) for pattern in SUSPICIOUS_UA_PATTERNS)

async def send_discord_alert(ip: str, path: str, method: str, user_agent: str, suspicious: bool):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url or "your_webhook" in webhook_url:
        return

    severity = "CRITICAL" if suspicious else "INFO"
    color = 15548997 if suspicious else 3447003 # Red vs Blue

    payload = {
        "embeds": [
            {
                "title": f"🚨 [{severity}] TRAP TRIGGERED",
                "color": color,
                "fields": [
                    {"name": "Timestamp", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": False},
                    {"name": "Source IP", "value": f"`{ip}`", "inline": True},
                    {"name": "Method", "value": f"`{method}`", "inline": True},
                    {"name": "Target Path", "value": f"`{path}`", "inline": False},
                    {"name": "User-Agent", "value": f"```{user_agent}```", "inline": False},
                    {"name": "Bot Detected", "value": str(suspicious), "inline": True},
                ],
                "footer": {"text": "Chimera Active Defense Engine v2.0"}
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        try:
            await client.post(webhook_url, json=payload, timeout=5.0)
        except Exception as e:
            logger.error(f"Discord Alert Failure: {e}")

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
@limiter.limit("3/minute")
async def catch_all(request: Request, full_path: str):
    client_ip = request.client.host
    user_agent = sanitize_input(request.headers.get("user-agent", "Unknown"))
    method = request.method
    clean_path = sanitize_input(f"/{full_path}")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    suspicious = is_suspicious_ua(user_agent)
    alert_color = RED if suspicious else YELLOW

    # Visual Alert
    print(f"""
{alert_color}############################################################
# {CYAN}[SYSTEM ALERT]{alert_color} TRAP TRIGGERED - {client_ip} #
############################################################{RESET}
{alert_color}UA-ANALYSIS: {RESET}{'SUSPICIOUS BOT' if suspicious else 'NORMAL'}
{YELLOW}TIMESTAMP:   {RESET}{timestamp}
{YELLOW}METHOD:      {RESET}{method}
{YELLOW}PATH:        {RESET}{clean_path}
{RED}############################################################{RESET}
""")

    logger.warning(f"Intrusion attempt from {client_ip} | Path: {clean_path} | Bot: {suspicious}")
    
    await send_discord_alert(client_ip, clean_path, method, user_agent, suspicious)
    
    # --- DYNAMIC HONEY RESPONSES ---
    path_lower = clean_path.lower()

    # 1. AWS / Cloud Metadata Decoy
    if any(keyword in path_lower for keyword in ["aws", "meta-data", "iam", "credentials"]):
        logger.info(f"Serving fake AWS credentials decoy to {client_ip}")
        # Obfuscated to bypass GitHub Push Protection for decoy credentials
        return {
            "Code": "Success",
            "LastUpdated": datetime.now().isoformat() + "Z",
            "Type": "AWS-HMAC",
            "AccessKeyId": "ASIA" + "V7XM" + "6XN7" + "H4Q3" + "Z8J2",
            "SecretAccessKey": "wJal" + "rXUt" + "nFEM" + "I/K7" + "MDEN" + "G/bP" + "xRfi" + "CYEX" + "AMPL" + "EKEY",
            "Token": (
                "FQoGZXIvYXdz" + "EHAaDM9uK5l9" + "iZ6L2pY7S9sK" + "8nL2mP1qR0tU" + "3vW6xY9zA1bC" + 
                "4dE7fG0hI3jK" + "6lM9nP2oR5sU" + "8vX1yZ4aB7cD" + "0eG3hI6jK9lM" + "2nO5pQ8rT1uV" + 
                "4wX7yZ0aB3cD" + "6eF9gH2iJ5kL" + "8mN1oP4qR7sT" + "0uV3wX6yZ9aB" + "2cD5eF8gH1iJ" + 
                "4kL7mN0oP3qR" + "6sT9uV2wX5yZ" + "8aB1c"
            ),
            "Expiration": "2028-12-31T23:59:59Z"
        }

    # 2. Configuration / Secret Decoy
    if any(keyword in path_lower for keyword in ["env", "config", "secret", "settings", "backup"]):
        logger.info(f"Serving fake .env decoy to {client_ip}")
        # Obfuscated to bypass GitHub Push Protection for decoy credentials
        decoy_env = (
            "# PRODUCTION ENVIRONMENT CONFIGURATION\n"
            "DB_HOST=10.0.5.22\n"
            "DB_NAME=chimera_prod_db\n"
            "DB_USER=chimera_svc_root\n"
            "DB_PASS=" + "P@ss" + "w0rd" + "_Chi" + "mera" + "_Act" + "ive_" + "Defe" + "nse_" + "2026!" + "\n"
            "STRIPE_API_KEY=" + "sk_" + "live" + "_51N" + "bV3q" + "L9Q7" + "Y7jK" + "2l9p" + "A4sD" + "6fG8" + "hJ0k" + "L2mN" + "4oP6" + "qR8s" + "T0uV" + "2wX4" + "yZ6a" + "B8c" + "\n"
            "AWS_DEFAULT_REGION=us-east-1\n"
            "INTERNAL_VPN_GATEWAY=192.168.10.1\n"
            "DEBUG=False\n"
        )
        return Response(content=decoy_env, media_type="text/plain")

    # 3. Default Success Decoy
    return {"status": "success", "data": None}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Chimera Active Defense deployed on port {port}")
    # Run with limited server headers and security focus
    uvicorn.run(app, host="0.0.0.0", port=port, server_header=False, date_header=False)
