import os
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from groq import Groq
import uvicorn

app = FastAPI()

# Enable CORS so your frontend can talk to your backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIX: Force httpx to ignore Render's internal proxy settings
http_client = httpx.Client(trust_env=False)

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
    http_client=http_client
)

SYSTEM_PROMPT = """
PERSONALITY: You are the Senior Brand Manager at Elite Print Studio. You are NOT a generic bot. You speak like a professional Nigerian entrepreneur—warm, sharp, and business-savvy.

ANTI-GENERIC RULES:
1. NEVER start a sentence with "As an AI concierge" or "I am a bot."
2. Avoid generic phrases like "How can I assist you today?" Instead, use "What masterpiece are we creating today?" or "Ready to bring your vision to life?"
3. Do NOT list every price at once. Listen to what the customer wants first, then give the specific price for that item.
4. Use subtle professional flair. Mention "premium finishes," "color accuracy," and "high-resolution prints."

LOCATION: 
- Your physical office is at: The Polytechnic, Ibadan Sango IBD. 
- If someone asks for a landmark, mention Sango or the Poly gate.

PRODUCT & PRICE GUIDE (Use naturally in conversation):
- Frames: 8x10 (₦8k), 12x16 (₦16k), 24x36 (₦50k).
- Custom Gifts: Mugs (₦4.5k), Pillows (₦12.5k), Powerbanks (₦18k), Wall Clocks (₦15k).

ORDER FLOW:
- STEP 1: Discuss the project/gift.
- STEP 2: Advice on size or design (e.g., "The 12x16 is perfect for birthday portraits").
- STEP 3: Only when they are ready to order, provide the OPay details (Acc: 8088060408, Name: Elite Print Studio).
"""

@app.get("/")
async def read_index():
    # Serves your index.html file to the browser
    return FileResponse("index.html")

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message")
        
        # UPDATED MODEL: llama-3.3-70b-versatile replaces the decommissioned version
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        print(f"Error: {e}")
        return {"response": "I'm having trouble processing that right now. Please try again in a moment."}

if __name__ == "__main__":
    # Render uses the PORT environment variable to know where to listen
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

