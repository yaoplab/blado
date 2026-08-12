"""AuthManager — Blado authentication (SHA-256 + optional OAuth2 PKCE)."""
# BLADO-VENDORED: cleaned from Larc school context
import os
import hashlib
import secrets
import base64
import configparser
import threading
import webbrowser
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Tuple

from .session import AuthResult, UserRole
from .database import db, DBMode
from .design_system import ds
from .logger import log
from .config_loader import find_cfg


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


class AuthManager:

    @classmethod
    def auth_intranet(cls, email: str, password: str) -> Tuple[bool, AuthResult, str]:
        """Authenticate against blado_user table (SHA-256 hashed password)."""
        conn = db.server_conn
        if conn is None or db.server_mode != DBMode.INTRANET:
            return False, AuthResult(), "Non connecté à l'intranet"

        pass_hash = _sha256_hex(password)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, full_name, password, role "
                    "FROM blado_user WHERE LOWER(email) = %s AND is_active = TRUE",
                    (email.strip().lower(),)
                )
                row = cur.fetchone()
            if row is None:
                return False, AuthResult(), 'Utilisateur introuvable'
            stored_hash = row[3]
            if stored_hash and stored_hash != pass_hash:
                return False, AuthResult(), 'Mot de passe incorrect'

            role_str = row[4] or 'RH'
            try:
                role = UserRole(role_str)
            except ValueError:
                role = UserRole.RH

            return True, AuthResult(
                user_id=row[0], email=email.strip().lower(),
                full_name=row[2] or '', role=role,
            ), ''
        except Exception as e:
            return False, AuthResult(), str(e)

    @classmethod
    def auth_pin(cls, email: str, pin: str, local_conn=None) -> Tuple[bool, AuthResult, str]:
        """PIN-based auth for offline/local SQLite cache."""
        if local_conn is None:
            return False, AuthResult(), 'Base locale non disponible'
        pin_hash = _sha256_hex(pin)
        try:
            row = local_conn.execute(
                "SELECT user_id, email, full_name, role, term_id, term_label "
                "FROM session_cache WHERE LOWER(email) = ? AND pin_hash = ?",
                (email.strip().lower(), pin_hash)
            ).fetchone()
            if row is None:
                return False, AuthResult(), 'Email ou PIN incorrect'
            role_str = row['role'] or 'RH'
            try:
                role = UserRole(role_str)
            except ValueError:
                role = UserRole.RH
            return True, AuthResult(
                user_id=int(row['user_id']),
                email=row['email'],
                full_name=row['full_name'],
                role=role,
                term_id=int(row['term_id'] or 0),
                term_label=row['term_label'] or '',
            ), ''
        except Exception as e:
            return False, AuthResult(), str(e)

    @classmethod
    def create_user(cls, email: str, password: str, full_name: str = '',
                    role: str = 'RH') -> Tuple[bool, str]:
        """Create a new blado_user (for setup wizard)."""
        conn = db.server_conn
        if conn is None:
            return False, "Non connecté à la base"
        pass_hash = _sha256_hex(password)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO blado_user (email, password, full_name, role) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (email) DO UPDATE SET full_name = %s",
                    (email.strip().lower(), pass_hash, full_name, role, full_name)
                )
            return True, ''
        except Exception as e:
            return False, str(e)


# ---------------------------------------------------------------------------
# OAuth2 PKCE — configurable provider (Google by default)
# ---------------------------------------------------------------------------

class _CallbackHandler(BaseHTTPRequestHandler):
    code:  str             = ''
    event: threading.Event = threading.Event()

    def do_GET(self) -> None:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if 'code' in qs:
            _CallbackHandler.code = qs['code'][0]
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(
            (f'<html><body style="font-family:sans-serif;text-align:center;padding:{ds.space_xl - ds.space_sm}px">'
             '<h2>✔ Authentification réussie</h2>'
             '<p>Vous pouvez fermer cet onglet et revenir à {0}.</p>'
             '</body></html>').format(OAuth2Manager.APP_DISPLAY).encode('utf-8')
        )
        _CallbackHandler.event.set()

    def log_message(self, *args) -> None:
        pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


class OAuth2Manager:
    PORT           = 8765
    APP_DISPLAY    = 'Blado'
    REDIRECT       = f'http://localhost:{PORT}/callback'
    GOOGLE_AUTH    = 'https://accounts.google.com/o/oauth2/v2/auth'
    GOOGLE_TOKEN   = 'https://oauth2.googleapis.com/token'

    # BLADO: no hosted_domain restriction by default (configurable via config.ini)
    @classmethod
    def _hosted_domain(cls) -> str:
        cfg = configparser.ConfigParser()
        cfg.read(find_cfg())
        return cfg.get('OAuth2', 'HostedDomain', fallback='')

    @classmethod
    def authenticate(cls) -> Tuple[bool, AuthResult, str]:
        cfg = configparser.ConfigParser()
        cfg.read(find_cfg())
        client_id     = cfg.get('OAuth2', 'ClientID',     fallback='')
        client_secret = cfg.get('OAuth2', 'ClientSecret', fallback='')
        if not client_id:
            return False, AuthResult(), 'ClientID OAuth2 manquant dans config.ini'

        verifier  = _b64url(secrets.token_bytes(32))
        challenge = _b64url(hashlib.sha256(verifier.encode('ascii')).digest())
        state     = _b64url(secrets.token_bytes(16))

        params = {
            'client_id':             client_id,
            'redirect_uri':          cls.REDIRECT,
            'response_type':         'code',
            'scope':                 'openid email profile',
            'code_challenge':        challenge,
            'code_challenge_method': 'S256',
            'state':                 state,
            'access_type':           'offline',
            'prompt':                'select_account',
        }
        hd = cls._hosted_domain()
        if hd:
            params['hd'] = hd

        auth_url = cls.GOOGLE_AUTH + '?' + urllib.parse.urlencode(params)

        _CallbackHandler.code = ''
        _CallbackHandler.event.clear()

        srv = HTTPServer(('localhost', cls.PORT), _CallbackHandler)
        threading.Thread(target=srv.handle_request, daemon=True).start()
        webbrowser.open(auth_url)

        if not _CallbackHandler.event.wait(timeout=120):
            srv.server_close()
            return False, AuthResult(), 'Délai de 2 min dépassé'

        srv.server_close()
        code = _CallbackHandler.code
        if not code:
            return False, AuthResult(), 'Code OAuth2 non reçu'

        token_body = urllib.parse.urlencode({
            'code':          code,
            'client_id':     client_id,
            'client_secret': client_secret,
            'redirect_uri':  cls.REDIRECT,
            'grant_type':    'authorization_code',
            'code_verifier': verifier,
        }).encode()
        try:
            req = urllib.request.Request(
                cls.GOOGLE_TOKEN, data=token_body, method='POST',
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                tokens = json.loads(resp.read())
        except Exception as e:
            return False, AuthResult(), f'Échange de token échoué : {e}'

        id_token = tokens.get('id_token', '')
        if not id_token:
            return False, AuthResult(), 'Token ID absent de la réponse'

        parts = id_token.split('.')
        if len(parts) < 2:
            return False, AuthResult(), 'Token ID malformé'
        pad     = '=' * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + pad))

        email = payload.get('email', '')
        # BLADO: no hosted_domain enforcement (optional config)
        hd = payload.get('hd', '')
        required_hd = cls._hosted_domain()
        if required_hd and hd != required_hd:
            return False, AuthResult(), f'Domaine non autorisé : {hd or "(aucun)"}'

        conn = db.server_conn
        if conn is None:
            return True, AuthResult(email=email, full_name=payload.get('name', '')), ''

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, full_name, role "
                    "FROM blado_user WHERE LOWER(email) = %s AND is_active = TRUE",
                    (email.lower(),)
                )
                row = cur.fetchone()
            if row is None:
                return False, AuthResult(), f'Utilisateur {email} non trouvé dans Blado'

            role_str = row[2] or 'RH'
            try:
                role = UserRole(role_str)
            except ValueError:
                role = UserRole.RH

            return True, AuthResult(
                user_id=row[0], email=email, full_name=row[1] or '',
                role=role,
            ), ''
        except Exception as e:
            return False, AuthResult(), str(e)
