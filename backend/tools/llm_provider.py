import os
import httpx
import json
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

class LLMProvider:
    """Professional Multi-Provider AI Hub: Gemini, OpenAI, Groq."""
    
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.client = httpx.AsyncClient(timeout=30)

    async def ask(self, prompt: str, system_prompt: str = "", provider: str = "auto") -> str:
        # 1. Manual Choice: Gemini
        if provider == "gemini":
            if not self.gemini_key: return "❌ Lỗi: Bạn chưa nhập GEMINI_API_KEY vào file .env"
            return await self._call_gemini(prompt, system_prompt)
            
        # 2. Manual Choice: OpenAI
        if provider == "openai":
            if not self.openai_key: return "❌ Lỗi: Bạn chưa nhập OPENAI_API_KEY vào file .env"
            return await self._call_openai(prompt, system_prompt)
        
        # 3. Manual Choice: Groq
        if provider == "groq":
            if not self.groq_key: return "❌ Lỗi: Bạn chưa nhập GROQ_API_KEY vào file .env"
            return await self._call_groq(prompt, system_prompt)

        # 4. Auto Mode (Smart Selection)
        providers_to_try = []
        if self.groq_key and "gsk_" in self.groq_key: providers_to_try.append(("groq", self._call_groq))
        if self.gemini_key and "AIza" in self.gemini_key: providers_to_try.append(("gemini", self._call_gemini))
        if self.openai_key and "sk-" in self.openai_key: providers_to_try.append(("openai", self._call_openai))
        
        last_error = ""
        for name, func in providers_to_try:
            res = await func(prompt, system_prompt)
            if "❌" not in res: return res
            last_error = res

        # 5. Last resort fallback
        if last_error: return last_error
        return await self._call_public_proxy(prompt, system_prompt)

    async def _call_gemini(self, prompt, system):
        # Try both v1 and v1beta to ensure compatibility
        for version in ["v1", "v1beta"]:
            url = f"https://generativelanguage.googleapis.com/{version}/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
            try:
                payload = {"contents": [{"parts": [{"text": f"System: {system}\n\nUser: {prompt}"}]}]}
                resp = await self.client.post(url, json=payload)
                if resp.status_code == 200:
                    return resp.json()['candidates'][0]['content']['parts'][0]['text']
                error_msg = f"Gemini Error ({resp.status_code}): {resp.json().get('error', {}).get('message', 'Unknown error')}"
            except:
                error_msg = "Gemini Connection Failed"
        return f"❌ {error_msg}. Hãy kiểm tra lại Key trên Google AI Studio."

    async def _call_openai(self, prompt, system):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        }
        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            return f"❌ OpenAI Error ({resp.status_code}): {resp.json().get('error', {}).get('message', 'Check key/quota')}"
        except: return "❌ OpenAI Connection Failed"

    async def _call_groq(self, prompt, system):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-8b-instant", # Updated model
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        }
        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            return f"❌ Groq Error ({resp.status_code}): {resp.json().get('error', {}).get('message', 'Check key')}"
        except: return "❌ Groq Connection Failed"

    async def _call_public_proxy(self, prompt, system):
        return (
            "🤖 **[Thông báo hệ thống AI]**\n\n"
            "Hiện tại chưa có API Key nào hoạt động. Vui lòng nhập API Key (Gemini/OpenAI/Groq) vào file `.env` "
            "để trải nghiệm sức mạnh trí tuệ nhân tạo thực thụ!"
        )
