import os
import re
import socket
import requests
import base64
import urllib3

# Warning များကို ပိတ်ထားရန်
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

g = "\033[1;32m"
y = "\033[1;33m"
r = "\033[1;31m"
w = "\033[1;00m"
c = "\033[1;36m"


def clear():
    os.system("clear" if os.name == "posix" else "cls")


def get_gateway_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split('.')
        parts[-1] = '1'
        return '.'.join(parts)
    except:
        return "192.168.110.1"


def find_portal_url(text, base_url):
    """Response text ထဲမှ portal URL ကို နည်းလမ်းမျိုးစုံဖြင့် ရှာခြင်း"""
    
    # 1. Meta refresh
    meta = re.search(
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;\s*url=([^"\'>\s]+)',
        text, re.IGNORECASE
    )
    if meta:
        url = meta.group(1).strip()
        if url.startswith("/"):
            url = base_url.rstrip("/") + url
        return url, "meta-refresh"

    # 2. JavaScript redirects
    js_patterns = [
        r'location\.href\s*=\s*["\']([^"\']+)["\']',
        r'location\.replace\s*\(\s*["\']([^"\']+)["\']',
        r'window\.location\s*=\s*["\']([^"\']+)["\']',
        r'location\s*=\s*["\']([^"\']+)["\']',
    ]
    for pat in js_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            url = m.group(1).strip()
            if url.startswith("/"):
                url = base_url.rstrip("/") + url
            return url, "js-redirect"

    # 3. Href links
    for m in re.finditer(r'href\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE):
        url = m.group(1)
        if "portal" in url.lower() or "ruijie" in url.lower() or "wifidog" in url.lower():
            if url.startswith("/"):
                url = base_url.rstrip("/") + url
            return url, "href"

    # 4. Full URLs in text (quoted)
    for m in re.finditer(r'["\'](https?://[^"\']+)["\']', text):
        url = m.group(1)
        if "portal" in url.lower() or "ruijie" in url.lower() or "wifidog" in url.lower():
            return url, "quoted-url"

    # 5. Base64 encoded URL
    for m in re.finditer(r'["\']([A-Za-z0-9+/]{30,}={0,2})["\']', text):
        try:
            decoded = base64.b64decode(m.group(1) + "==").decode('utf-8', errors='ignore')
            if "http" in decoded and ("portal" in decoded.lower() or "ruijie" in decoded.lower() or "wifidog" in decoded.lower()):
                return decoded, "base64"
        except:
            pass

    return None, None


def fetch_portal():
    clear()
    print(f"{g}======================================{w}")
    print(f"{c}  Ruijie Auto-Catcher (Skip Mode)     {w}")
    print(f"{g}======================================{w}\n")

    print(f"{y}[*] ကျေးဇူးပြု၍ Ruijie Wi-Fi နှင့် ချိတ်ဆက်ထားပါ။{w}")
    print(f"{y}[*] အင်တာနက် မပွင့်သေးကြောင်း သေချာပါစေ။{w}\n")

    gateways = [get_gateway_ip(), "192.168.110.1", "192.168.0.1", "10.44.77.254", "192.168.1.1"]
    gateways = list(dict.fromkeys(gateways))

    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }

    portal_url = None
    method = None
    found_gateway = None

    # ============ STEP 1: Gateway တစ်ခုချင်း စစ်ခြင်း ============
    for gw in gateways:
        base = f"http://{gw}"
        print(f"{c}[*] Checking Gateway: {base}{w}")
        try:
            res = requests.get(base, headers=headers, timeout=5,
                               allow_redirects=False, verify=False)

            # Location header စစ်ခြင်း
            if "Location" in res.headers:
                loc = res.headers["Location"]
                if "ruijie" in loc.lower() or "portal" in loc.lower() or "wifidog" in loc.lower():
                    portal_url = loc
                    if portal_url.startswith("/"):
                        portal_url = base + portal_url
                    method = "Location-header"
                    found_gateway = gw
                    print(f"{g}[✓] Found via Location header{w}")
                    break

            # Body စစ်ခြင်း
            body = res.text
            if body and ("ruijie" in body.lower() or "portal" in body.lower() or "wifidog" in body.lower()):
                found_gateway = gw
                url, how = find_portal_url(body, base)
                if url:
                    portal_url = url
                    method = how
                    print(f"{g}[✓] Found via {how}{w}")
                    break

        except requests.exceptions.RequestException:
            print(f"{r}[-] No response from {gw}{w}")

    # ============ STEP 2: Redirect လိုက်ခြင်း (allow_redirects=True) ============
    if not portal_url:
        print(f"\n{c}[*] Trying with full redirect follow...{w}")
        for gw in gateways:
            try:
                res = requests.get(f"http://{gw}", headers=headers, timeout=5,
                                   allow_redirects=True, verify=False)
                # Final URL စစ်ခြင်း
                if "ruijie" in res.url.lower() or "portal" in res.url.lower() or "wifidog" in res.url.lower():
                    portal_url = res.url
                    method = "final-redirect"
                    found_gateway = gw
                    print(f"{g}[✓] Found via final redirect: {res.url[:80]}{w}")
                    break
                # History စစ်ခြင်း
                for h in res.history:
                    if "Location" in h.headers:
                        loc = h.headers["Location"]
                        if "ruijie" in loc.lower() or "portal" in loc.lower() or "wifidog" in loc.lower():
                            portal_url = loc
                            method = "redirect-history"
                            found_gateway = gw
                            print(f"{g}[✓] Found in redirect history{w}")
                            break
                if portal_url:
                    break
                # Body ထဲ ထပ်ရှာ
                url, how = find_portal_url(res.text, f"http://{gw}")
                if url:
                    portal_url = url
                    method = how
                    found_gateway = gw
                    print(f"{g}[✓] Found via {how}{w}")
                    break
            except:
                continue

    # ============ STEP 3: Global Intercept (httpbin) ============
    if not portal_url:
        print(f"\n{c}[*] Trying global HTTP intercept (httpbin)...{w}")
        try:
            res = requests.get("http://httpbin.org/get", headers=headers, timeout=5,
                               allow_redirects=True, verify=False)
            if "ruijie" in res.url.lower() or "portal" in res.url.lower() or "wifidog" in res.url.lower():
                portal_url = res.url
                method = "httpbin-intercept"
                print(f"{g}[✓] Found via httpbin intercept{w}")
            else:
                url, how = find_portal_url(res.text, "http://httpbin.org")
                if url:
                    portal_url = url
                    method = how
                    print(f"{g}[✓] Found via {how} in httpbin response{w}")
        except:
            pass

    # ============ STEP 4: Skip Mode - Direct API ============
    if not portal_url and found_gateway:
        print(f"\n{c}[*] Skip Mode: Trying direct API endpoints...{w}")
        api_candidates = [
            f"http://{found_gateway}/api/auth/wifidog?stage=portal",
            f"http://{found_gateway}/api/auth/wifidog?stage=portal&",
            f"http://{found_gateway}/wifidog/ping",
            f"https://portal-as.ruijienetworks.com/api/auth/wifidog?stage=portal",
        ]
        for api in api_candidates:
            try:
                rr = requests.get(api, headers=headers, timeout=5, verify=False)
                if rr.status_code in (200, 302, 401, 403):
                    portal_url = api
                    method = "direct-api"
                    print(f"{g}[✓] API responded: {api}{w}")
                    break
            except:
                continue

    # ============ STEP 5: Result ============
    if portal_url:
        # API path သို့ ပြောင်းလဲခြင်း
        api_url = portal_url
        replacements = [
            ("/auth/wifidogAuth/login/?", "/api/auth/wifidog?stage=portal&"),
            ("/auth/wifidogAuth/login?", "/api/auth/wifidog?stage=portal&"),
            ("/auth/wifidogAuth/login/", "/api/auth/wifidog?stage=portal"),
        ]
        for old, new in replacements:
            api_url = api_url.replace(old, new)

        print(f"\n{g}[✓] PORTAL/API URL ရရှိပါပြီ! (method: {method}){w}")
        print(f"{y}{'-' * 60}{w}")
        print(f"{w}{api_url}{w}")
        print(f"{y}{'-' * 60}{w}")

        b64_url = base64.b64encode(api_url.encode()).decode()
        print(f"\n{c}[*] Base64 Code (script ထဲထည့်ရန်):{w}")
        print(f"{g}{b64_url}{w}\n")
    else:
        print(f"\n{r}[❌] Portal URL ကို ရှာမတွေ့ပါ။{w}")
        print(f"{y}[i] အောက်ပါအချက်များ စစ်ဆေးပါ:{w}")
        print(f"{y}    1. Wi-Fi ချိတ်ဆက်ထားသလား{w}")
        print(f"{y}    2. Browser ဖြင့် http://{get_gateway_ip()} ကို ဖွင့်ကြည့်ပါ{w}")
        print(f"{y}    3. Browser Developer Tools (F12) → Network tab မှာ portal URL ကို ကြည့်ပါ{w}")
        print(f"{y}    4. Portal URL ကို manual ဖြင့် ရိုက်ထည့်ပြီး base64 ပြောင်းပါ{w}\n")


if __name__ == '__main__':
    try:
        fetch_portal()
    except KeyboardInterrupt:
        print(f"\n\n{r}[!] Exiting...{w}")
