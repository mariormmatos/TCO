from supabase import create_client, Client
import streamlit as st

def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

class Database:
    def __init__(self):
        self.supabase: Client = init_supabase()
        try:
            supabase_cfg = st.secrets.get("supabase", {})
        except Exception:
            supabase_cfg = {}
        self.redirect_url = supabase_cfg.get("redirect_url", "http://localhost:8501")

    def _apply_session(self):
        sess = st.session_state.get("db_session")
        if not sess:
            return
        access = None
        refresh = None
        if isinstance(sess, dict):
            access = sess.get("access_token")
            refresh = sess.get("refresh_token")
        else:
            access = getattr(sess, "access_token", None)
            refresh = getattr(sess, "refresh_token", None)
        if access and refresh:
            try:
                self.supabase.auth.set_session(access, refresh)
            except Exception:
                pass

    def sign_up(self, email, password):
        try:
            payload = {"email": email, "password": password}
            if self.redirect_url:
                payload["options"] = {"email_redirect_to": self.redirect_url}
            return self.supabase.auth.sign_up(payload)
        except Exception as e:
            return {"error": str(e)}

    def sign_in(self, email, password):
        try:
            return self.supabase.auth.sign_in_with_password({"email": email, "password": password})
        except Exception as e:
            return {"error": str(e)}

    def sign_out(self):
        try:
            return self.supabase.auth.sign_out()
        except Exception as e:
            return {"error": str(e)}

    def get_user(self):
        try:
            return self.supabase.auth.get_user()
        except:
            return None

    def save_simulation(self, user_id, simulation_data):
        try:
            self._apply_session()
            data = {"user_id": user_id, "data": simulation_data}
            return self.supabase.table("simulations").insert(data).execute()
        except Exception as e:
            return {"error": str(e)}

    def get_simulations(self, user_id):
        try:
            self._apply_session()
            return self.supabase.table("simulations").select("*").eq("user_id", user_id).execute()
        except Exception as e:
            return {"error": str(e)}
