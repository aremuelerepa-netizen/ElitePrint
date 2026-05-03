"""
FrameHaus — Premium Elite E-Commerce Catalog
Flask Application Entry Point (Root-Level Structure)
"""
import os
import uuid
import json
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, flash, abort
)
from dotenv import load_dotenv
from supabase import create_client, Client
from PIL import Image

# Load environment variables from .env file
load_dotenv()

# Set template_folder and static_folder to "." to look in the root directory
app = Flask(__name__, template_folder=".", static_folder=".")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB upload limit

# ── Supabase Setup ──────────────────────────────────────────────────────────
# Ensure these keys are set in your Render Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET", "product-images")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "2348012345678")

# Initialize Clients
supabase_public: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
CATEGORIES = ["Canvas Prints", "Custom Frames", "Photo Prints", "Posters", "Mirrors", "Gift Items"]

# ── Helpers ──────────────────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the admin dashboard.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

def optimize_image(file_bytes: bytes, max_width: int = 1200) -> bytes:
    img = Image.open(BytesIO(file_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    output = BytesIO()
    img.save(output, format="JPEG", quality=85, optimize=True)
    return output.getvalue()

def upload_to_storage(file_bytes: bytes, original_filename: str) -> str:
    unique_name = f"{uuid.uuid4().hex}.jpg"
    path_in_bucket = f"products/{unique_name}"
    optimized = optimize_image(file_bytes)
    
    supabase_admin.storage.from_(STORAGE_BUCKET).upload(
        path=path_in_bucket,
        file=optimized,
        file_options={"content-type": "image/jpeg", "upsert": "false"},
    )
    return supabase_admin.storage.from_(STORAGE_BUCKET).get_public_url(path_in_bucket)

def delete_from_storage(image_url: str) -> None:
    try:
        marker = f"/object/public/{STORAGE_BUCKET}/"
        if marker in image_url:
            path = image_url.split(marker, 1)[1]
            supabase_admin.storage.from_(STORAGE_BUCKET).remove([path])
    except Exception as e:
        app.logger.warning(f"Storage deletion warning: {e}")

# ── Frontend Routes ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    # Looks for index.html in the root directory
    return render_template("index.html", whatsapp_number=WHATSAPP_NUMBER, categories=CATEGORIES)

@app.route("/api/products")
def api_products():
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()
    query = (
        supabase_public.table("products")
        .select("id, name, price, category, description, image_url, in_stock")
        .eq("active", True)
        .order("created_at", desc=True)
    )
    if category and category != "All":
        query = query.eq("category", category)
    
    response = query.execute()
    products = response.data or []
    
    if search:
        sl = search.lower()
        products = [p for p in products if sl in p["name"].lower() or sl in (p.get("description") or "").lower()]
    return jsonify(products)

# ── Admin Auth ──────────────────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        try:
            auth_response = supabase_public.auth.sign_in_with_password({"email": email, "password": password})
            if auth_response.user:
                session["admin_logged_in"] = True
                session["admin_email"] = auth_response.user.email
                session["admin_uid"] = auth_response.user.id
                flash("Welcome back!", "success")
                return redirect(url_for("admin_dashboard"))
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash("Login failed. Check your credentials.", "error")
            
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("admin_login"))

# ── Admin Dashboard & CRUD ──────────────────────────────────────────────────
@app.route("/admin")
@admin_required
def admin_dashboard():
    response = supabase_admin.table("products").select("*").order("created_at", desc=True).execute()
    products = response.data or []
    stats = {
        "total": len(products),
        "active": sum(1 for p in products if p.get("active")),
        "out_of_stock": sum(1 for p in products if not p.get("in_stock")),
        "categories": len(set(p["category"] for p in products if p.get("category"))),
    }
    return render_template("admin_dashboard.html", 
                           products=products, 
                           categories=CATEGORIES,
                           stats=stats, 
                           admin_email=session.get("admin_email"))

@app.route("/admin/products/add", methods=["POST"])
@admin_required
def admin_add_product():
    name = request.form.get("name", "").strip()
    price = request.form.get("price", "0").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    in_stock = request.form.get("in_stock") == "on"
    
    if not name or not category:
        return jsonify({"error": "Name and category are required."}), 400
    
    try:
        price_val = float(price)
    except ValueError:
        return jsonify({"error": "Price must be a number."}), 400
    
    image_url = None
    file = request.files.get("image")
    if file and file.filename and allowed_file(file.filename):
        image_url = upload_to_storage(file.read(), file.filename)
    
    payload = {
        "name": name, "price": price_val, "category": category,
        "description": description, "in_stock": in_stock, 
        "active": True, "image_url": image_url
    }
    
    result = supabase_admin.table("products").insert(payload).execute()
    if result.data:
        return jsonify({"success": True, "product": result.data[0]}), 201
    return jsonify({"error": "Database insert failed."}), 500

@app.route("/admin/products/<int:product_id>/edit", methods=["POST"])
@admin_required
def admin_edit_product(product_id):
    existing = supabase_admin.table("products").select("*").eq("id", product_id).single().execute()
    if not existing.data:
        return jsonify({"error": "Product not found."}), 404
    
    old = existing.data
    name = request.form.get("name", old["name"]).strip()
    price = request.form.get("price", str(old["price"])).strip()
    category = request.form.get("category", old["category"]).strip()
    description = request.form.get("description", old.get("description", "")).strip()
    in_stock = request.form.get("in_stock") == "on"
    active = request.form.get("active") == "on"
    
    try:
        price_val = float(price)
    except ValueError:
        return jsonify({"error": "Price must be a number."}), 400
    
    image_url = old.get("image_url")
    file = request.files.get("image")
    if file and file.filename and allowed_file(file.filename):
        if image_url:
            delete_from_storage(image_url)
        image_url = upload_to_storage(file.read(), file.filename)
    
    payload = {
        "name": name, "price": price_val, "category": category, 
        "description": description, "in_stock": in_stock, 
        "active": active, "image_url": image_url
    }
    
    result = supabase_admin.table("products").update(payload).eq("id", product_id).execute()
    if result.data:
        return jsonify({"success": True, "product": result.data[0]})
    return jsonify({"error": "Update failed."}), 500

@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def admin_delete_product(product_id):
    existing = supabase_admin.table("products").select("image_url").eq("id", product_id).single().execute()
    if existing.data and existing.data.get("image_url"):
        delete_from_storage(existing.data["image_url"])
    
    supabase_admin.table("products").delete().eq("id", product_id).execute()
    return jsonify({"success": True})

# ── Error Handlers ──────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File too large. Maximum size is 10MB."}), 413

if __name__ == "__main__":
    app.run(debug=True, port=5000)
