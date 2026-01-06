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
ROLE: Senior CSR at Elite Print Studio. 
STYLE: Very concise. Use bullet points. No long paragraphs. 
LOCATION: The Polytechnic, Ibadan Sango IBD.

PRICES:
• 8x10: ₦8k | 12x16: ₦16k | 24x36: ₦50k
• Mugs: ₦4.5k | Pillows: ₦12.5k | Clocks: ₦15k

RULES:
- Keep replies short (under 50 words).
- Use "•" for any lists.
- Mention OPay (8088060408) only if they are ready to order.
- Act like a human expert, not a bot.
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
            max_tokens=150, # Limits how long the AI can talk
            temperature=0.5 # Makes it more focused and less "wordy"
        )
        return {"response": completion.choices[0].message.content}
    except Exception as e:
        return {"response": "System busy. Please try again."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
