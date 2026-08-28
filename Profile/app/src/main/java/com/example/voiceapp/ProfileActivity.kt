package org.sarvoc.profile

import android.os.Bundle
import android.util.Base64
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Profile screen connected directly to Supabase REST/PostgREST.
 * No service_role key is stored in the APK. Only the publishable/anon key is used.
 * The authenticated user's access token must already be saved by the app under:
 *   SharedPreferences: supabase_session / access_token
 * or passed as Intent extra: access_token.
 */
class ProfileActivity : AppCompatActivity() {
    companion object {
        private const val SUPABASE_URL = "https://kwlovnyznahfkyhvmyzv.supabase.co"
        private const val SUPABASE_PUBLISHABLE_KEY = "sb_publishable_pzWRXTsydWX_FoyWnF_Tmg_5VWO-vKd"
        private const val PREFS = "supabase_session"
    }

    private lateinit var tvUserId: TextView
    private lateinit var tvFollowing: TextView
    private lateinit var tvFans: TextView
    private lateinit var tvVisitors: TextView
    private lateinit var tvLevel: TextView
    private lateinit var tvBalance: TextView
    private lateinit var ivAvatar: ImageView

    private fun accessToken(): String? =
        intent.getStringExtra("access_token")
            ?: getSharedPreferences(PREFS, MODE_PRIVATE).getString("access_token", null)

    private fun userIdFromToken(token: String): String? {
        return try {
            val parts = token.split(".")
            if (parts.size < 2) return null
            val payload = String(Base64.decode(parts[1], Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING), Charsets.UTF_8)
            JSONObject(payload).optString("sub", null)
        } catch (_: Exception) { null }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_profile)
        bindViews()
        loadProfileFromServer()
    }

    private fun bindViews() {
        tvUserId = findViewById(R.id.tvUserId)
        tvFollowing = findViewById(R.id.tvFollowingCount)
        tvFans = findViewById(R.id.tvFansCount)
        tvVisitors = findViewById(R.id.tvVisitorsCount)
        tvLevel = findViewById(R.id.tvLevel)
        tvBalance = findViewById(R.id.tvBalance)
        ivAvatar = findViewById(R.id.ivAvatar)

        findViewById<ImageView>(R.id.btnBack).setOnClickListener { finish() }
        findViewById<LinearLayout>(R.id.cardBalance).setOnClickListener { loadWallet() }
        findViewById<LinearLayout>(R.id.menuSettings).setOnClickListener {
            Toast.makeText(this, "الإعدادات تُفتح من شاشة الإعدادات في التطبيق الرئيسي", Toast.LENGTH_SHORT).show()
        }
    }

    private suspend fun getJson(path: String, token: String): JSONArray = withContext(Dispatchers.IO) {
        val conn = URL("$SUPABASE_URL/rest/v1/$path").openConnection() as HttpURLConnection
        conn.requestMethod = "GET"
        conn.setRequestProperty("apikey", SUPABASE_PUBLISHABLE_KEY)
        conn.setRequestProperty("Authorization", "Bearer $token")
        conn.setRequestProperty("Accept", "application/json")
        conn.connectTimeout = 15000
        conn.readTimeout = 15000
        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val body = stream.bufferedReader().use { it.readText() }
        conn.disconnect()
        if (code !in 200..299) error("Supabase HTTP $code: $body")
        JSONArray(body)
    }

    private fun loadProfileFromServer() {
        val token = accessToken()
        if (token.isNullOrBlank()) {
            Toast.makeText(this, "لا توجد جلسة دخول Supabase", Toast.LENGTH_LONG).show()
            return
        }
        val uid = intent.getStringExtra("user_id") ?: userIdFromToken(token)
        if (uid.isNullOrBlank()) {
            Toast.makeText(this, "تعذر تحديد المستخدم", Toast.LENGTH_LONG).show()
            return
        }

        lifecycleScope.launch {
            try {
                val profile = getJson("profiles?id=eq.$uid&select=id,username,avatar_url,level,followers,following,visitors", token)
                if (profile.length() == 0) error("profile_not_found")
                render(profile.getJSONObject(0), uid)
                loadWallet(token, uid)
            } catch (e: Exception) {
                Toast.makeText(this@ProfileActivity, "تعذر تحميل الحساب من السيرفر", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun loadWallet() {
        val token = accessToken() ?: return
        val uid = intent.getStringExtra("user_id") ?: userIdFromToken(token) ?: return
        loadWallet(token, uid)
    }

    private fun loadWallet(token: String, uid: String) {
        lifecycleScope.launch {
            try {
                val wallet = getJson("wallets?user_id=eq.$uid&select=balance", token)
                val balance = if (wallet.length() > 0) wallet.getJSONObject(0).optLong("balance", 0L) else 0L
                tvBalance.text = String.format("%,d", balance)
            } catch (_: Exception) {
                tvBalance.text = "0"
            }
        }
    }

    private fun render(json: JSONObject, uid: String) {
        tvUserId.text = "ID:${uid.take(12)}"
        tvFollowing.text = json.optInt("following", 0).toString()
        tvFans.text = json.optInt("followers", 0).toString()
        tvVisitors.text = json.optInt("visitors", 0).toString()
        tvLevel.text = "LV.${json.optInt("level", 1)}"
    }
}
