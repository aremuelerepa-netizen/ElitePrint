import os
import uuid
import httpx
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
from dotenv import load_dotenv
import uvicorn

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="elite-print-bot")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ADMIN_PASSWORD = "Bashlad2030"

# ── Pages ─────────────────────────────────────────────────
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/about")
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/elite-admin-2025")
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

# ── Settings ──────────────────────────────────────────────
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

# ── Categories ────────────────────────────────────────────
@app.get("/api/categories")
async def get_categories():
    try:
        res = supabase.table("categories").select("*").execute()
        return {"data": res.data}
    except Exception as e:
        return {"data": [], "error": str(e)}

# ── Products ──────────────────────────────────────────────
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

# ── Cart ──────────────────────────────────────────────────
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

@app.delete("/api/cart/{item_id}")
async def remove_cart_item(item_id: str):
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

# ── Orders ────────────────────────────────────────────────
@app.post("/api/orders")
async def create_order(request: Request):
    try:
        data = await request.json()
        customer_name = str(data.get("customer_name", "")).strip()
        customer_whatsapp = str(data.get("customer_whatsapp", "")).strip()
        if not customer_name:
            return {"success": False, "error": "Customer name is required"}
        if not customer_whatsapp:
            return {"success": False, "error": "WhatsApp number is required"}
        total = float(data.get("total_amount", 0))
        if total <= 0:
            return {"success": False, "error": "Invalid order amount"}

        order_number = "EPS-" + str(uuid.uuid4())[:8].upper()
        order_payload = {
            "order_number": order_number,
            "customer_name": customer_name,
            "customer_whatsapp": customer_whatsapp,
            "delivery_type": data.get("delivery_type", "pickup"),
            "delivery_address": data.get("delivery_address", ""),
            "total_amount": total,
            "amount_paid": 0,
            "balance_due": total,
            "payment_proof_url": "",
            "payment_status": "pending",
            "order_status": "pending",
            "source": "catalog",
            "notes": data.get("notes", "")
        }
        order_res = supabase.table("orders").insert(order_payload).execute()
        if not order_res.data:
            return {"success": False, "error": "Database error"}
        order_id = order_res.data[0]["id"]

        for item in data.get("items", []):
            try:
                item["order_id"] = order_id
                supabase.table("order_items").insert(item).execute()
            except Exception as ie:
                print(f"Item error: {ie}")

        # Clear cart
        session_id = data.get("session_id", "")
        if session_id:
            supabase.table("cart_items").delete().eq("session_id", session_id).execute()

        return {"success": True, "order_number": order_number}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── Admin Orders ──────────────────────────────────────────
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
        pending = [o for o in all_orders if o["order_status"] == "pending"]
        in_prod = [o for o in all_orders if o["order_status"] == "in_production"]
        done = [o for o in all_orders if o["order_status"] == "done"]
        week_orders = [o for o in all_orders if o["created_at"][:10] >= week_ago]
        return {
            "total": len(all_orders), "today": len(today_orders),
            "pending": len(pending), "in_production": len(in_prod),
            "done": len(done), "week_orders": len(week_orders)
        }
    except Exception as e:
        return {"total": 0, "today": 0, "pending": 0, "in_production": 0, "done": 0, "week_orders": 0}

# ── Reviews ───────────────────────────────────────────────
@app.get("/api/reviews")
async def get_reviews():
    try:
        res = supabase.table("reviews").select("*").eq("is_active", True).order("created_at", desc=True).execute()
        return {"data": res.data}
    except Exception as e:
        return {"data": [], "error": str(e)}

@app.post("/api/admin/reviews")
async def add_review(request: Request):
    try:
        data = await request.json()
        res = supabase.table("reviews").insert(data).execute()
        return {"success": True, "data": res.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/api/admin/reviews/{review_id}")
async def delete_review(review_id: str):
    try:
        supabase.table("reviews").delete().eq("id", review_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── Portfolio ─────────────────────────────────────────────
@app.get("/api/portfolio")
async def get_portfolio():
    try:
        res = supabase.table("portfolio_items").select("*").eq("is_active", True).order("sort_order").execute()
        return {"data": res.data}
    except Exception as e:
        return {"data": [], "error": str(e)}

@app.post("/api/admin/portfolio")
async def add_portfolio(request: Request):
    try:
        data = await request.json()
        res = supabase.table("portfolio_items").insert(data).execute()
        return {"success": True, "data": res.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/api/admin/portfolio/{item_id}")
async def delete_portfolio(item_id: str):
    try:
        supabase.table("portfolio_items").delete().eq("id", item_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── Uploads ───────────────────────────────────────────────
@app.post("/api/upload/product-image")
async def upload_product_image(file: UploadFile = File(...), product_id: str = Form(...), is_primary: str = Form("false")):
    try:
        contents = await file.read()
        file_ext = file.filename.split(".")[-1]
        file_name = f"{product_id}/{uuid.uuid4()}.{file_ext}"
        supabase.storage.from_("product-images").upload(file_name, contents, {"content-type": file.content_type})
        url = supabase.storage.from_("product-images").get_public_url(file_name)
        supabase.table("product_images").insert({"product_id": product_id, "image_url": url, "is_primary": is_primary == "true"}).execute()
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

@app.post("/api/upload/portfolio")
async def upload_portfolio_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        file_ext = file.filename.split(".")[-1]
        file_name = f"portfolio/{uuid.uuid4()}.{file_ext}"
        supabase.storage.from_("portfolio-images").upload(file_name, contents, {"content-type": file.content_type})
        url = supabase.storage.from_("portfolio-images").get_public_url(file_name)
        return {"success": True, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/upload/owner-photo")
async def upload_owner_photo(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        file_ext = file.filename.split(".")[-1]
        file_name = f"owner.{file_ext}"
        try:
            supabase.storage.from_("company-assets").remove([file_name])
        except:
            pass
        supabase.storage.from_("company-assets").upload(file_name, contents, {"content-type": file.content_type})
        url = supabase.storage.from_("company-assets").get_public_url(file_name)
        supabase.table("settings").update({"value": url}).eq("key", "about_owner_photo_url").execute()
        return {"success": True, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── Admin Auth ────────────────────────────────────────────
@app.post("/api/admin/login")
async def admin_login(request: Request):
    try:
        data = await request.json()
        if data.get("password") == ADMIN_PASSWORD:
            return {"success": True}
        return {"success": False, "error": "Invalid password"}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
