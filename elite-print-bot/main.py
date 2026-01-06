import os
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from groq import Groq
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

http_client = httpx.Client(trust_env=False)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"), http_client=http_client)

SYSTEM_PROMPT = """
ROLE: Senior Brand Consultant at Elite Print Studio.
STYLE: Human-like, premium, and extremely concise. 
FORMATTING: Use "•" for prices. Always keep replies under 2 or 3 sentences.

GUIDELINES:
1. NO BOT-SPEAK: Never use "I'm all ears" or "masterpiece" in every reply.
2. SHORT GREETINGS: If user says "Hi", reply: "Hello! Welcome to Elite Print Studio. How can I help with your printing or gifting needs today?"
3. LOCATION: Only mention our address (The Polytechnic, Ibadan Sango IBD) IF asked.
4. PRICING: Provide specific prices only when asked. 
   • 8x10: ₦8k | 12x16: ₦16k | 24x36: ₦50k
   • Mugs: ₦4.5k | Pillows: ₦12.5k
5. PAYMENT: Show OPay 8088060408 ONLY when the customer says they are ready to order.
6. WHATSAPP RULE: Tell them they can click the WhatsApp button below to send their high-quality files and proof of payment directly to our production team.

BEHAVIOR: Be professional like a real Ibadan business owner. Do not ramble.
"""

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message")
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.4, # Lower temperature makes it more direct and less "creative"
            max_tokens=100    # Strictly limits the length of the response
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        return {"response": "Service temporarily unavailable."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

