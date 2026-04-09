# 🎭 Project Chimera: Active Cyber Deception Engine

![Version](https://img.shields.io/badge/version-2.0.0--stable-red?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.10+-blue?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688?style=for-the-badge)

**Project Chimera** is a high-fidelity Active Cyber Deception (ACD) and HoneyToken engine designed to entrap, identify, and neutralize adversaries the moment they touch your infrastructure. By deploying "Dynamic Honey Responses," Chimera turns your attack surface into a minefield of convincing decoys.

> *"In the conflict between predator and prey, the ultimate advantage is control over the environment. Chimera is that control."*

---

## 🏗️ Architecture: The Trinity of Deception

Chimera is built on three core pillars designed for stealth, speed, and actionable intelligence:

| Component | Code Name | Responsibility |
| :--- | :--- | :--- |
| **The Forge** | `Credential Engine` | Generates high-entropy, realistic fake credentials for AWS, Postgres, Stripe, and JWTs. |
| **The Trap** | `chimera_listener.py` | A hardened, catch-all FastAPI server that serves dynamic decoys based on path analysis. |
| **The Webhook** | `Discord SOC` | Instantaneous, rich-embed alerts delivered directly to your Security Operations Center. |

---

## ✨ Features

- **🛡️ Dynamic Honey Responses**: Automatically switches response types based on attacker behavior:
    - **Cloud Decoy**: Returns fake AWS STS Temporary Credentials when `aws` or `iam` paths are probed.
    - **Secret Decoy**: Serves mock `.env` files with fake DB strings and Stripe keys for `config` or `backup` probes.
    - **Ghost Success**: Returns a generic `200 OK` for all other paths to maximize attacker "Time on Trap."
- **🕵️ Advanced Bot Fingerprinting**: Detects and flags common scanners (Nmap, SQLMap, Nikto, Dirbuster) via UA-Analysis.
- **⚡ Hardened Security**:
    - Built-in Rate Limiting (`SlowAPI`) to prevent webhook exhaustion.
    - Automated Input Sanitization to mitigate Log Injection.
    - Hidden Server Headers to prevent fingerprinting of the listener itself.
- **📢 SOC Integration**: Real-time Discord notifications with Severity levels (INFO vs CRITICAL).

---

## 🚀 Installation & Deployment

### 1. Clone & Forge the Environment
```bash
git clone https://github.com/your-org/project-chimera.git
cd project-chimera
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the SOC (System of Control)
Create a `.env` file in the root directory:
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-id/your-token
ALLOWED_HOSTS=*
PORT=8000
```

### 3. Deploy the Trap
```bash
python chimera_listener.py
```

---

## 🛠️ Usage Example

When an attacker attempts to access `http://your-server/backup/.env`, Chimera executes:
1. **Detection**: Captures IP, User-Agent, and Method.
2. **Analysis**: Flags if the User-Agent belongs to a known scanner.
3. **Alerting**: Sends a high-priority rich embed to Discord.
4. **Deception**: Serves a realistic `.env` file instead of a `404` or `401`.

---

## 📊 Security Comparison

| Feature | Standard Honeypot | Project Chimera |
| :--- | :---: | :---: |
| Catch-all Routing | ❌ | ✅ |
| Dynamic Payloads | ❌ | ✅ |
| Rate Limiting | ❌ | ✅ |
| Bot Analysis | ❌ | ✅ |
| Discord SOC | ❌ | ✅ |

---

## ⚖️ Disclaimer

Project Chimera is intended for **defensive security purposes only**. Deployment of honeytokens must comply with local laws and organizational policies. The developers assume no liability for misuse.

**Maintain the Illusion. Secure the Perimeter.**
