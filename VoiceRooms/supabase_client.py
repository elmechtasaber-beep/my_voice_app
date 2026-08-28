from supabase import create_client, Client

SUPABASE_URL = "https://kwlovnyznahfkyhvmyzv.supabase.co"
SUPABASE_KEY = "sb_publishable_pzWRXTsydWX_FoyWnF_Tmg_5VWO-vKd"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
