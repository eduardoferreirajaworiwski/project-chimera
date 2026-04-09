import uvicorn
import os
import httpx
import logging
import re
import asyncio
import random
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
MAX_REQUEST_SIZE = 1024 * 50
SUSPICIOUS_UA_PATTERNS = [
    r"sqlmap", r"nmap", r"nikto", r"dirbuster", r"gobuster", r"zgrab", r"masscan", r"python-requests"
]

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Project Chimera", docs_url=None, redoc_url=None)
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
        response.headers["Server"] = "Hidden"
        return response

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_REQUEST_SIZE:
                return Response(content="Payload Too Large", status_code=413)
        return await call_next(request)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

# ANSI Color Codes
RED = "\033[1;91m"
YELLOW = "\033[1;93m"
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
RESET = "\033[0m"

def sanitize_input(text: str) -> str:
    return "".join(char for char in text if char.isprintable())[:500]

def is_suspicious_ua(ua: str) -> bool:
    return any(re.search(pattern, ua, re.IGNORECASE) for pattern in SUSPICIOUS_UA_PATTERNS)

async def get_geoip(ip: str):
    """Fetch Threat Intel Geo-IP data."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://ip-api.com/json/{ip}", timeout=3.0)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Geo-IP Lookup Failed: {e}")
    return {}

async def send_discord_alert(ip: str, path: str, method: str, user_agent: str, suspicious: bool, geo: dict):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url or "your_webhook" in webhook_url: return

    severity = "🚨 CRITICAL" if suspicious else "⚠️ WARNING"
    color = 15548997 if suspicious else 16705372 # Red vs Amber
    
    country = geo.get("country", "Unknown")
    city = geo.get("city", "Unknown")
    isp = geo.get("isp", "Unknown")
    country_code = geo.get("countryCode", "").lower()
    flag = f":flag_{country_code}:" if country_code else "🌐"

    payload = {
        "embeds": [{
            "title": f"{severity}: Intrusion Attempt",
            "color": color,
            "fields": [
                {"name": "🌍 Origin", "value": f"{flag} {city}, {country} ({isp})", "inline": False},
                {"name": "🌐 IP Address", "value": f"`{ip}`", "inline": True},
                {"name": "🛠️ Method", "value": f"`{method}`", "inline": True},
                {"name": "📂 Target Path", "value": f"`{path}`", "inline": False},
                {"name": "🤖 Bot Detected", "value": f"`{suspicious}`", "inline": True},
                {"name": "🕵️ User-Agent", "value": f"```{user_agent}```", "inline": False},
            ],
            "footer": {"text": f"Chimera Intel v3.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        }]
    }
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=payload, timeout=5.0)

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
@limiter.limit("5/minute")
async def catch_all(request: Request, full_path: str):
    client_ip = request.client.host
    user_agent = sanitize_input(request.headers.get("user-agent", "Unknown"))
    method = request.method
    clean_path = sanitize_input(f"/{full_path}")
    path_lower = clean_path.lower()
    
    suspicious = is_suspicious_ua(user_agent) or any(k in path_lower for k in ["env", "aws", "git", "config"])
    
    # 1. IP Intel
    geo = await get_geoip(client_ip)
    
    # 2. Visual Alert
    alert_color = RED if suspicious else YELLOW
    print(f"\n{alert_color}############################################################\n# {CYAN}[THREAT INTEL]{alert_color} TRAP TRIGGERED - {client_ip} ({geo.get('country', '??')}) #\n############################################################{RESET}\n{YELLOW}PATH:     {RESET}{clean_path}\n{YELLOW}ISP:      {RESET}{geo.get('isp', 'Unknown')}\n{RED}############################################################{RESET}")

    # 3. Active Defense: The Tarpit (Always active for sensitive probes)
    if suspicious or any(k in path_lower for k in ["env", "aws", "git", "config", "secret"]):
        delay = random.randint(5, 15)
        logger.warning(f"Tarpit activated for {client_ip}: {delay}s delay...")
        await asyncio.sleep(delay)

    # 4. Out-of-band Alert
    await send_discord_alert(client_ip, clean_path, method, user_agent, suspicious, geo)
    
    # 5. Dynamic Honey Responses
    if any(k in path_lower for k in ["aws", "iam", "credentials"]):
        logger.info(f"Serving fake AWS credentials decoy to {client_ip}")
        return {
            "Code": "Success", "LastUpdated": datetime.now().isoformat() + "Z", "Type": "AWS-HMAC",
            "AccessKeyId": "ASIA" + "V7XM" + "6XN7" + "H4Q3" + "Z8J2",
            "SecretAccessKey": "wJal" + "rXUt" + "nFEM" + "I/K7" + "MDEN" + "G/bP" + "xRfi" + "CYEX" + "AMPL" + "EKEY"
        }

    if any(k in path_lower for k in ["env", "config", "secret", "settings"]):
        logger.info(f"Serving fake .env decoy to {client_ip}")
        decoy = (
            "DB_HOST=10.0.5.22\n"
            "DB_USER=root\n"
            "DB_PASS=" + "P@ss" + "w0rd" + "_Chi" + "mera" + "\n"
            "STRIPE_LIVE_KEY=" + "sk_" + "live" + "_51N" + "bV3q" + "L9Q7" + "\n"
        )
        return Response(content=decoy, media_type="text/plain")

    if ".git/config" in path_lower:
        logger.info(f"Serving fake .git/config decoy to {client_ip}")
        decoy = "[remote \"origin\"]\n\turl = https://github.com/chimera-prod/internal-infra.git\n\tfetch = +refs/heads/*:refs/remotes/origin/*"
        return Response(content=decoy, media_type="text/plain")

    return {"status": "success", "data": None}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Chimera Intel v3.0 deployed on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, server_header=False, date_header=False)
