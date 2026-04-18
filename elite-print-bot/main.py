import os
import uuid
import httpx
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from groq import Groq
from supabase import create_client, Client
from dotenv import load_dotenv
import uvicorn

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")

# ── Clients ──────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

http_client = httpx.Client(trust_env=False)
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"), http_client=http_client)

ADMIN_PASSWORD = "Bashlad2030"

# ── AI System Prompt ──────────────────────────────────────
def build_system_prompt():
    try:
        products_res = supabase.table("products").select("name, base_price, description, available_sizes, categories(name)").eq("is_active", True).execute()
        settings_res = supabase.table("settings").select("key, value").execute()
        settings = {r["key"]: r["value"] for r in settings_res.data}
        
        product_list = ""
        for p in products_res.data:
            cat = p.get("categories", {})
            cat_name = cat.get("name", "") if cat else ""
            sizes = ", ".join(p.get("available_sizes") or [])
            size_str = f" | Sizes: {sizes}" if sizes else ""
            product_list += f"\n• {p['name']} ({cat_name}): ₦{p['base_price']:,.0f}{size_str}"

        return f"""You are a friendly, energetic sales consultant for Elite Print Studio — a premium custom printing & gifting business in Ibadan, Nigeria.

PRODUCTS & PRICES (live from our catalog):
{product_list}

BUSINESS INFO:
• Location: {settings.get('business_address', 'The Polytechnic, Ibadan Sango IBD')}
• WhatsApp: {settings.get('whatsapp_number', '2348088060408')}
• Payment: {settings.get('bank_name', 'OPay')} | {settings.get('opay_number', '8088060408')} | {settings.get('account_name', 'Elite Print Studio')}
• Policy: 70% payment upfront before production begins. Balance paid on pickup/delivery.

YOUR JOB:
1. Answer questions about products, prices, turnaround time, delivery warmly and concisely.
2. When a customer wants to ORDER, collect in this order:
   a. What product + customization details (text, color, size, quantity)
   b. Full name
   c. WhatsApp number
   d. Pickup or delivery? (if delivery, get address)
   e. Then show payment details and tell them to upload their receipt
3. When customer uploads receipt, confirm order is received and tell them you'll contact them on WhatsApp when ready.
4. NEVER collect order info unless customer clearly wants to order.
5. Keep replies SHORT — max 3 sentences unless listing prices or collecting order info.
6. Be warm, professional, Ibadan business owner energy. No robotic language.
7. Turnaround time: 1-3 business days depending on product.
8. When showing payment details use this exact format:
   💳 BANK: {settings.get('bank_name', 'OPay')}
   📱 NUMBER: {settings.get('opay_number', '8088060408')}
   👤 NAME: {settings.get('account_name', 'Elite Print Studio')}
   💰 AMOUNT: [70% of total]
   Then tell them to upload their receipt below.

STYLE: Energetic, warm, concise. Use emojis sparingly. Never say "I'm an AI"."""
    except:
        return """You are a sales consultant for Elite Print Studio, a premium printing business in Ibadan. Help customers with products, prices and orders. Be warm and concise."""

# ── Page Routes ───────────────────────────────────────────
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/marketplace")
async def marketplace(request: Request):
    return templates.TemplateResponse("marketplace.html", {"request": request})

@app.get("/studio")
async def studio(request: Request):
    return templates.TemplateResponse("studio.html", {"request": request})

@app.get("/order")
async def order(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})

@app.get("/elite-admin-2025")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

# ── AI Chat ───────────────────────────────────────────────
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "")
        history = data.get("history", [])
        has_receipt = data.get("has_receipt", False)
        order_data = data.get("order_data", None)

        system_prompt = build_system_prompt()
        
        if has_receipt and order_data:
            user_message = f"[Customer uploaded payment receipt. Order details: {order_data}] {user_message}"

        messages = [{"role": "system", "content": system_prompt}]
        for h in history[-8:]:
            messages.append(h)
        messages.append({"role": "user", "content": user_message})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_tokens=200
        )
        response = completion.choices[0].message.content
        
        # Detect if AI is asking for payment
        payment_trigger = any(x in response.lower() for x in ["opay", "8088060408", "upload", "receipt", "transfer"])
        order_trigger = any(x in response.lower() for x in ["your name", "whatsapp number", "pickup or delivery", "delivery address"])
        
        return {
            "response": response,
            "payment_trigger": payment_trigger,
            "order_trigger": order_trigger
        }
    except Exception as e:
        return {"response": "Service temporarily unavailable. Please try again.", "payment_trigger": False, "order_trigger": False}

# ── Products API ──────────────────────────────────────────
@app.get("/api/categories")
async def get_categories():
    try:
        res = supabase.table("categories").select("*").execute()
        return {"data": res.data}
    except Exception as e:
        return {"data": [], "error": str(e)}

@app.get("/api/products")
async def get_products(category_id: str = None):
    try:
        query = supabase.table("products").select("*, categories(*), product_images(*)").eq("is_active", True)
        if category_id:
            query = query.eq("category_id", category_id)
        res = query.execute()
        return {"data": res.data}
    except Exception as e:
        return {"data": [], "error": str(e)}

@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    try:
        res = supabase.table("products").select("*, categories(*), product_images(*)").eq("id", product_id).single().execute()
        return {"data": res.data}
    except Exception as e:
        return {"data": None, "error": str(e)}

# ── Cart API ──────────────────────────────────────────────
@app.get("/api/cart/{session_id}")
async def get_cart(session_id: str):
    try:
        res = supabase.table("cart_items").select("*").eq("session_id", session_id).execute()
        return {"data": res.data}
    except Exception as e:
        return {"data": [], "error": str(e)}

@app.post("/api/cart")
async def add_to_cart(request: Request):
    try:
        data = await request.json()
        res = supabase.table("cart_items").insert(data).execute()
        return {"success": True, "data": res.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/api/cart/{item_id}")
async def update_cart_item(item_id: str, request: Request):
    try:
        data = await request.json()
        res = supabase.table("cart_items").update(data).eq("id", item_id).execute()
        return {"success": True, "data": res.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/api/cart/{item_id}")
async def delete_cart_item(item_id: str):
    try:
        supabase.table("cart_items").delete().eq("id", item_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/api/cart/session/{session_id}")
async def clear_cart(session_id: str):
    try:
        supabase.table("cart_items").delete().eq("session_id", session_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── Orders API ────────────────────────────────────────────
@app.post("/api/orders")
async def create_order(request: Request):
    try:
        data = await request.json()
        order_number = "EPS-" + str(uuid.uuid4())[:8].upper()
        total = float(data.get("total_amount", 0))
        amount_paid = round(total * 0.7, 2)
        balance_due = round(total * 0.3, 2)

        order_data = {
            "order_number": order_number,
            "customer_name": data.get("customer_name"),
            "customer_whatsapp": data.get("customer_whatsapp"),
            "delivery_type": data.get("delivery_type", "pickup"),
            "delivery_address": data.get("delivery_address", ""),
            "total_amount": total,
            "amount_paid": amount_paid,
            "balance_due": balance_due,
            "payment_proof_url": data.get("payment_proof_url", ""),
            "payment_status": "pending",
            "order_status": "pending",
            "source": data.get("source", "ai"),
            "notes": data.get("notes", "")
        }

        order_res = supabase.table("orders").insert(order_data).execute()
        order_id = order_res.data[0]["id"]

        items = data.get("items", [])
        for item in items:
            item["order_id"] = order_id
            supabase.table("order_items").insert(item).execute()

        return {"success": True, "order_number": order_number, "order_id": order_id, "amount_due": amount_paid}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── Upload APIs ───────────────────────────────────────────
@app.post("/api/upload/product-image")
async def upload_product_image(file: UploadFile = File(...), product_id: str = Form(...), is_primary: str = Form("false")):
    try:
        contents = await file.read()
        file_ext = file.filename.split(".")[-1]
        file_name = f"{product_id}/{uuid.uuid4()}.{file_ext}"
        supabase.storage.from_("product-images").upload(file_name, contents, {"content-type": file.content_type})
        url = supabase.storage.from_("product-images").get_public_url(file_name)
        supabase.table("product_images").insert({
            "product_id": product_id,
            "image_url": url,
            "is_primary": is_primary == "true"
        }).execute()
        return {"success": True, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/upload/payment-proof")
async def upload_payment_proof(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        file_ext = file.filename.split(".")[-1]
        file_name = f"proofs/{uuid.uuid4()}.{file_ext}"
        supabase.storage.from_("payment-proofs").upload(file_name, contents, {"content-type": file.content_type})
        url = supabase.storage.from_("payment-proofs").get_public_url(file_name)
        return {"success": True, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/upload/design")
async def upload_design(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        file_ext = file.filename.split(".")[-1]
        file_name = f"designs/{uuid.uuid4()}.{file_ext}"
        supabase.storage.from_("custom-designs").upload(file_name, contents, {"content-type": file.content_type})
        url = supabase.storage.from_("custom-designs").get_public_url(file_name)
        return {"success": True, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/upload/logo")
async def upload_logo(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        file_ext = file.filename.split(".")[-1]
        file_name = f"logo.{file_ext}"
        try:
            supabase.storage.from_("company-assets").remove([file_name])
        except:
            pass
        supabase.storage.from_("company-assets").upload(file_name, contents, {"content-type": file.content_type})
        url = supabase.storage.from_("company-assets").get_public_url(file_name)
        supabase.table("settings").update({"value": url}).eq("key", "logo_url").execute()
        return {"success": True, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── Admin APIs ────────────────────────────────────────────
@app.post("/api/admin/login")
async def admin_login(request: Request):
    try:
        data = await request.json()
        if data.get("password") == ADMIN_PASSWORD:
            return {"success": True}
        return {"success": False, "error": "Invalid password"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/admin/orders")
async def get_orders():
    try:
        res = supabase.table("orders").select("*, order_items(*)").order("created_at", desc=True).execute()
        return {"data": res.data}
    except Exception as e:
        return {"data": [], "error": str(e)}

@app.put("/api/admin/orders/{order_id}")
async def update_order(order_id: str, request: Request):
    try:
        data = await request.json()
        res = supabase.table("orders").update(data).eq("id", order_id).execute()
        return {"success": True, "data": res.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/admin/products")
async def create_product(request: Request):
    try:
        data = await request.json()
        res = supabase.table("products").insert(data).execute()
        return {"success": True, "data": res.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/api/admin/products/{product_id}")
async def update_product(product_id: str, request: Request):
    try:
        data = await request.json()
        res = supabase.table("products").update(data).eq("id", product_id).execute()
        return {"success": True, "data": res.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/api/admin/products/{product_id}")
async def delete_product(product_id: str):
    try:
        supabase.table("products").update({"is_active": False}).eq("id", product_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/settings")
async def get_settings():
    try:
        res = supabase.table("settings").select("*").execute()
        return {"data": {r["key"]: r["value"] for r in res.data}}
    except Exception as e:
        return {"data": {}, "error": str(e)}

@app.put("/api/admin/settings")
async def update_settings(request: Request):
    try:
        data = await request.json()
        for key, value in data.items():
            supabase.table("settings").update({"value": str(value)}).eq("key", key).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/admin/stats")
async def get_stats():
    try:
        from datetime import datetime, timedelta
        today = datetime.now().date().isoformat()
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        
        all_orders = supabase.table("orders").select("*").execute().data
        today_orders = [o for o in all_orders if o["created_at"][:10] == today]
        pending = [o for o in all_orders if o["payment_status"] == "pending"]
        in_prod = [o for o in all_orders if o["order_status"] == "in_production"]
        done = [o for o in all_orders if o["order_status"] == "done"]
        week_orders = [o for o in all_orders if o["created_at"][:10] >= week_ago]
        week_revenue = sum(float(o["amount_paid"]) for o in week_orders if o["payment_status"] == "confirmed")
        
        return {
            "total": len(all_orders),
            "today": len(today_orders),
            "pending": len(pending),
            "in_production": len(in_prod),
            "done": len(done),
            "week_revenue": week_revenue
        }
    except Exception as e:
        return {"total": 0, "today": 0, "pending": 0, "in_production": 0, "done": 0, "week_revenue": 0}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
