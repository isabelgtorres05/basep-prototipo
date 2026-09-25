"""Conexión exclusivamente de servidor. Nunca se envía la clave al navegador."""
import os
import hmac
import hashlib
import time
from functools import lru_cache

def setting(name):
    if name in os.environ:
        return os.environ[name].strip()
    import streamlit as st
    try:
        return str(st.secrets.get(name, '')).strip()
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return ''

def configured():
    url, key = setting('SUPABASE_URL'), setting('SUPABASE_KEY')
    if bool(url) != bool(key):
        raise ValueError('Completa SUPABASE_URL y SUPABASE_KEY en los secretos del servidor.')
    return bool(url and key)

@lru_cache(maxsize=2)
def _client(url, key):
    from supabase import create_client
    from supabase.lib.client_options import SyncClientOptions
    return create_client(url, key, options=SyncClientOptions(auto_refresh_token=False, persist_session=False))

def client():
    if not configured():
        raise ValueError('Supabase no está configurado.')
    url,key=setting('SUPABASE_URL'),setting('SUPABASE_KEY')
    if not url.startswith('https://'):
        raise ValueError('SUPABASE_URL debe usar HTTPS.')
    if not key.startswith('sb_secret_'):
        import base64,json
        try:
            payload=key.split('.')[1]
            role=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))['role']
        except Exception:
            role=None
        if role!='service_role':
            raise ValueError('Usa una Secret key de servidor; la clave pública no tiene acceso a las tablas privadas.')
    return _client(url,key)

def require_private_access():
    """Barrera temporal para el piloto; el selector de roles NO autentica."""
    import streamlit as st
    if not configured():
        return
    password = setting('BASEP_ACCESS_PASSWORD')
    if len(password) < 16:
        st.error('Configura BASEP_ACCESS_PASSWORD (mínimo 16 caracteres) para habilitar el piloto privado.')
        st.stop()
    fingerprint = hashlib.sha256(password.encode()).hexdigest()
    if st.session_state.get('_basep_access') == fingerprint:
        return
    st.subheader('Acceso privado BASEP')
    with st.form('basep_private_access'):
        entered = st.text_input('Contraseña del piloto', type='password')
        submitted = st.form_submit_button('Entrar')
    if submitted:
        if time.monotonic() < st.session_state.get('_basep_retry_at', 0):
            st.error('Espera unos segundos antes de volver a intentar.')
        elif hmac.compare_digest(entered.encode(), password.encode()):
            st.session_state['_basep_access'] = fingerprint
            st.rerun()
        else:
            st.session_state['_basep_retry_at'] = time.monotonic() + 3
            st.error('Contraseña incorrecta.')
    st.stop()
