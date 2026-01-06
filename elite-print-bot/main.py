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
You are the Elite Print Studio AI Concierge. 
PRICES: 
- Frames: 8x10(₦8k), 12x16(₦16k), 24x36(₦50k).
- Gifts: Mugs(₦4.5k), Pillows(₦12.5k), Powerbanks(₦18k), Wall Clocks(₦15k).
PAYMENT: If ready to pay, show OPay (Acc: 8088060408, Name: Elite Print Studio).
DIRECTIVE: Be professional. Encourage users to upload designs via the toolbelt.
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
