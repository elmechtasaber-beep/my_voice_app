import requests

SUPABASE_URL = "https://kwlcvnyznahfkyfvmymw.supabase.co"
SUPABASE_KEY = "sb_publishable_pzWRXTsydWX_FoyWnF_Tmg_5VWO-vKd"

AUTH_URL = f"{SUPABASE_URL}/auth/v1"
REST_URL = f"{SUPABASE_URL}/rest/v1"

BASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Content-Type": "application/json",
}


class AuthResponse:
    def __init__(self, data, ok):
        self.ok = ok
        self.user = data.get("user") if ok else None
        if ok and data.get("access_token"):
            self.session = type("Session", (), {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
            })()
        else:
            self.session = None
        self.raw = data


class User:
    def __init__(self, data):
        self.id = data.get("id")
        self.email = data.get("email")
        self.user_metadata = data.get("user_metadata", {}) or {}
        self.raw = data


# ---------- AUTH ----------
def sign_up(email, password):
    r = requests.post(f"{AUTH_URL}/signup", headers=BASE_HEADERS,
                       json={"email": email, "password": password})
    data = r.json()
    if r.status_code >= 400:
        raise Exception(data.get("msg") or data.get("error_description") or data.get("message") or "خطأ فالتسجيل")
    return AuthResponse(data, True)


def sign_in_with_password(email, password):
    r = requests.post(f"{AUTH_URL}/token?grant_type=password", headers=BASE_HEADERS,
                       json={"email": email, "password": password})
    data = r.json()
    if r.status_code >= 400:
        raise Exception(data.get("msg") or data.get("error_description") or data.get("message") or "خطأ فتسجيل الدخول")
    return AuthResponse(data, True)


def set_session(access_token, refresh_token):
    r = requests.post(f"{AUTH_URL}/token?grant_type=refresh_token", headers=BASE_HEADERS,
                       json={"refresh_token": refresh_token})
    data = r.json()
    if r.status_code >= 400:
        raise Exception(data.get("msg") or data.get("error_description") or "فشلت الجلسة")
    return AuthResponse(data, True)


def sign_out(access_token):
    headers = {**BASE_HEADERS, "Authorization": f"Bearer {access_token}"}
    requests.post(f"{AUTH_URL}/logout", headers=headers)


def get_user(access_token):
    headers = {**BASE_HEADERS, "Authorization": f"Bearer {access_token}"}
    r = requests.get(f"{AUTH_URL}/user", headers=headers)
    if r.status_code >= 400:
        raise Exception("جلسة غير صالحة")
    return User(r.json())


# ---------- TABLES (REST) ----------
def select(table, access_token, select_cols="*", filters="", order="", limit=None, count=False, single=False):
    headers = {**BASE_HEADERS, "Authorization": f"Bearer {access_token}"}
    if count:
        headers["Prefer"] = "count=exact"

    params = f"select={select_cols}"
    if filters:
        params += f"&{filters}"
    if order:
        params += f"&order={order}"
    if limit:
        params += f"&limit={limit}"

    r = requests.get(f"{REST_URL}/{table}?{params}", headers=headers)
    data = r.json()

    total_count = None
    if count and "content-range" in r.headers:
        try:
            total_count = int(r.headers["content-range"].split("/")[-1])
        except Exception:
            total_count = None

    if single:
        data = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else None)

    return data, total_count, r.status_code


def insert(table, access_token, data):
    headers = {**BASE_HEADERS, "Authorization": f"Bearer {access_token}", "Prefer": "return=representation"}
    r = requests.post(f"{REST_URL}/{table}", headers=headers, json=data)
    return r.json(), r.status_code


def upsert(table, access_token, data, on_conflict=None):
    headers = {**BASE_HEADERS, "Authorization": f"Bearer {access_token}", "Prefer": "resolution=merge-duplicates,return=representation"}
    params = f"?on_conflict={on_conflict}" if on_conflict else ""
    r = requests.post(f"{REST_URL}/{table}{params}", headers=headers, json=data)
    return r.json(), r.status_code


def delete(table, access_token, filters=""):
    headers = {**BASE_HEADERS, "Authorization": f"Bearer {access_token}"}
    r = requests.delete(f"{REST_URL}/{table}?{filters}", headers=headers)
    return r.status_code


def rpc(function_name, access_token, params=None):
    headers = {**BASE_HEADERS, "Authorization": f"Bearer {access_token}"}
    r = requests.post(f"{REST_URL}/rpc/{function_name}", headers=headers, json=params or {})
    data = r.json() if r.text else None
    if r.status_code >= 400:
        msg = data.get("message") if isinstance(data, dict) else str(data)
        raise Exception(msg or "خطأ فـ استدعاء الدالة")
    return data
