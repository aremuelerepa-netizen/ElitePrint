import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from groq import Groq
import uvicorn

app = FastAPI()

# Enable CORS so your frontend can talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Render will provide the API Key via Environment Variables
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Your Master Instruction Manual
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
    # This serves your HTML file when you visit the URL
    return FileResponse("index.html")

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message")
    
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )
    return {"response": completion.choices[0].message.content}

if __name__ == "__main__":
    # Render uses the PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)