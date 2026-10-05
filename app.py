"""
app.py — Flask Gateway & REST API Routes
National Unified Material Master Platform (Government Enterprise Edition)
"""

import os
import io
import csv
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

import pandas as pd
from flask import (
    Flask, render_template, request, jsonify, send_file, session, Response,
)
from pymongo import MongoClient

from config import (
    UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH,
    STANDARD_FIELDS, MATCH_THRESHOLD, HIGH_CONFIDENCE,
)
from services.schema_mapper import auto_map_columns, rename_dataframe_columns
from services.code_generator import (
    generate_cnmc_for_clusters, detect_category, reset_sequences,
)
from core_ai.preprocessor import preprocess_batch
from core_ai.attribute_extractor import extract_attributes_batch, extract_attributes
from core_ai.vectorizer import HybridVectorizer
from core_ai.matcher import MaterialMatcher

# Load environment variables from .env
load_dotenv()

# ── App Factory ───────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gov-cpse-platform-secret-key-2024")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

from routes.auth import auth_bp
from routes.portal_cpse import cpse_bp
from routes.portal_admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(cpse_bp)
app.register_blueprint(admin_bp)

# ── MongoDB Setup ─────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["sih_material_master"]

# Collections
col_materials = db["materials"]        # All uploaded material rows
col_uploads = db["uploads"]            # Metadata about each file upload
col_matches = db["matches"]            # Duplicate pairs detected
col_clusters = db["clusters"]          # Proposed & Approved CNMC clusters
col_audit = db["audit_logs"]           # Approval/Rejection logs
col_transfers = db["inter_cpse_transfers"]  # Inter-CPSE material requests
col_demands = db["demands"]            # Future demand aggregation
col_settings = db["platform_settings"] # Admin platform settings

# Initialize default settings if not present
if not col_settings.find_one({"key": "auto_approve_threshold"}):
    col_settings.insert_one({"key": "auto_approve_threshold", "value": 95})
if not col_settings.find_one({"key": "auto_approve_enabled"}):
    col_settings.insert_one({"key": "auto_approve_enabled", "value": False})

# Create indexes for fast lookup (silent if they exist)
col_materials.create_index("local_material_code")
col_materials.create_index("cpse_name")
col_clusters.create_index("cnmc_code", unique=True)
col_clusters.create_index("status")


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _read_upload(file_storage) -> pd.DataFrame:
    """Read uploaded CSV, TXT, or Excel into a DataFrame."""
    filename = file_storage.filename
    ext = filename.rsplit(".", 1)[1].lower()
    if ext == "csv":
        return pd.read_csv(file_storage, dtype=str).fillna("")
    elif ext == "txt":
        # Let pandas automatically infer the delimiter (tab, comma, semicolon, etc.)
        return pd.read_csv(file_storage, sep=None, engine='python', dtype=str).fillna("")
    else:
        return pd.read_excel(file_storage, dtype=str, engine="openpyxl").fillna("")


# ══════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    """Render the landing page."""
    return render_template("home.html")


# ── POST /api/upload ──────────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """
    Accept a CSV/Excel file, run AI column auto-segregation,
    and store mapped data in MongoDB.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use CSV, TXT (Tab-separated), or Excel."}), 400

    # Read file
    try:
        df = _read_upload(file)
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 400

    if df.empty:
        return jsonify({"error": "Uploaded file is empty."}), 400

    upload_id = str(uuid.uuid4())[:8]
    original_headers = list(df.columns)

    # AI Column Auto-Segregation
    mapping_result = auto_map_columns(original_headers)
    logs = [
        f"[PROCESSING]: Extracting {len(df)} rows from uploaded file '{file.filename}'...",
        f"[SCHEMA]: Detected {len(original_headers)} columns: {', '.join(original_headers)}",
    ] + mapping_result["logs"]

    # Rename columns
    df_mapped = rename_dataframe_columns(df, mapping_result)
    records = df_mapped.to_dict(orient="records")

    # Add metadata
    cpse_user = session.get("cpse_name", "Unknown")
    for row in records:
        row["_upload_id"] = upload_id
        row["_source_file"] = file.filename
        row["_uploaded_at"] = datetime.utcnow()
        # Force the logged-in user's CPSE name onto the record
        if cpse_user != "Unknown":
            row["cpse_name"] = cpse_user

    # Store in MongoDB
    if records:
        col_materials.insert_many(records)
    
    col_uploads.insert_one({
        "upload_id": upload_id,
        "filename": file.filename,
        "total_rows": len(df),
        "cpse_name": cpse_user,
        "uploaded_at": datetime.utcnow()
    })

    logs.append(f"[COMPLETE]: Upload '{upload_id}' processed successfully. {len(df)} records ingested into MongoDB.")

    # Remove MongoDB internal _id for JSON serialization
    for r in records:
        r.pop("_id", None)

    return jsonify({
        "upload_id": upload_id,
        "filename": file.filename,
        "total_rows": len(df),
        "original_headers": original_headers,
        "column_mappings": mapping_result["mappings"],
        "unmapped_columns": mapping_result["unmapped"],
        "logs": logs,
        "data": records,
    })


# ── GET /api/download-template ────────────────────────────────────────

@app.route("/api/download-template", methods=["GET"])
def download_template():
    """Generate and return a standard CSV template."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(STANDARD_FIELDS)
    writer.writerow([
        "ONGC", "ONGC-MAT-001",
        "2 inch Stainless Steel Gate Valve, Class 150, Flanged End",
        "Size: 2 inch, Material: SS316, Rating: Class 150",
        "NOS", "50"
    ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="cpse_material_template.csv",
    )


# ── GET /api/my-catalog ──────────────────────────────────────────────

@app.route("/api/my-catalog", methods=["GET"])
def get_my_catalog():
    """Fetch all uploaded materials for the currently logged-in CPSE."""
    cpse_name = session.get("cpse_name")
    if not cpse_name:
        return jsonify({"error": "Unauthorized"}), 401
    
    query = {"cpse_name": cpse_name} if cpse_name != "Unknown" else {}
    cursor = col_materials.find(query, {"_id": 0})
    return jsonify(list(cursor))


# ── GET /api/my-analytics ─────────────────────────────────────────────

@app.route("/api/my-analytics", methods=["GET"])
def get_my_analytics():
    """CPSE-specific analytics for the logged-in company."""
    cpse_name = session.get("cpse_name")
    if not cpse_name:
        return jsonify({"error": "Unauthorized"}), 401

    total_items = col_materials.count_documents({"cpse_name": cpse_name})
    cnmc_assigned = col_materials.count_documents({"cpse_name": cpse_name, "cnmc_code": {"$exists": True, "$ne": ""}})
    pending = total_items - cnmc_assigned

    # Category breakdown for this CPSE
    cat_agg = col_materials.aggregate([
        {"$match": {"cpse_name": cpse_name}},
        {"$group": {"_id": "$material_description", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ])
    top_materials = {c["_id"][:30]: c["count"] for c in cat_agg if c["_id"]}

    # Uploads by this CPSE
    uploads = list(col_uploads.find({"cpse_name": cpse_name}, {"_id": 0}).sort("uploaded_at", -1).limit(10))

    return jsonify({
        "cpse_name": cpse_name,
        "total_items": total_items,
        "cnmc_assigned": cnmc_assigned,
        "pending": pending,
        "top_materials": top_materials,
        "recent_uploads": uploads,
    })


# ── GET /api/my-mappings ──────────────────────────────────────────────

@app.route("/api/my-mappings", methods=["GET"])
def get_my_mappings():
    """Show legacy code to CNMC mapping for the logged-in CPSE."""
    cpse_name = session.get("cpse_name")
    if not cpse_name:
        return jsonify({"error": "Unauthorized"}), 401

    cursor = col_materials.find(
        {"cpse_name": cpse_name, "cnmc_code": {"$exists": True, "$ne": ""}},
        {"_id": 0, "local_material_code": 1, "material_description": 1, "cnmc_code": 1, "status": 1}
    )
    return jsonify(list(cursor))


# ── GET /api/my-suggestions ───────────────────────────────────────────

@app.route("/api/my-suggestions", methods=["GET"])
def get_my_suggestions():
    """Show AI match suggestions relevant to the logged-in CPSE."""
    cpse_name = session.get("cpse_name")
    if not cpse_name:
        return jsonify({"error": "Unauthorized"}), 401

    # Find clusters where at least one member belongs to this CPSE
    all_clusters = list(col_clusters.find({}, {"_id": 0}))
    relevant = []
    for c in all_clusters:
        members = c.get("members", [])
        cpse_members = [m for m in members if m.get("cpse") == cpse_name]
        if cpse_members:
            relevant.append({
                "cnmc_code": c.get("cnmc_code"),
                "category": c.get("category"),
                "status": c.get("status"),
                "my_items": cpse_members,
                "other_items": [m for m in members if m.get("cpse") != cpse_name],
                "total_members": len(members),
            })

    return jsonify(relevant)


# ── GET /api/my-audit ─────────────────────────────────────────────────

@app.route("/api/my-audit", methods=["GET"])
def get_my_audit():
    """Audit trail for the logged-in CPSE's materials."""
    cpse_name = session.get("cpse_name")
    if not cpse_name:
        return jsonify({"error": "Unauthorized"}), 401

    # Get upload events
    events = []
    uploads = list(col_uploads.find({"cpse_name": cpse_name}, {"_id": 0}).sort("uploaded_at", -1))
    for u in uploads:
        events.append({
            "type": "upload",
            "description": f"File '{u.get('filename')}' uploaded ({u.get('total_rows')} rows)",
            "timestamp": u.get("uploaded_at", ""),
        })

    # Get approval/rejection events relevant to this CPSE
    all_clusters = list(col_clusters.find(
        {"status": {"$in": ["approved", "rejected"]}},
        {"_id": 0}
    ))
    for c in all_clusters:
        members = c.get("members", [])
        cpse_members = [m for m in members if m.get("cpse") == cpse_name]
        if cpse_members:
            events.append({
                "type": c.get("status"),
                "description": f"CNMC '{c.get('cnmc_code')}' was {c.get('status')} ({len(members)} items grouped)",
                "timestamp": c.get("updated_at", ""),
            })

    return jsonify(events)


# ── GET /api/audit-logs (Admin) ───────────────────────────────────────

@app.route("/api/audit-logs", methods=["GET"])
def get_audit_logs():
    """Full audit trail for admin."""
    logs = list(col_audit.find({}, {"_id": 0}).sort("timestamp", -1).limit(100))
    return jsonify(logs)




@app.route("/api/match", methods=["GET", "POST"])
def run_matching():
    """
    Run the full AI matching pipeline on all uploaded data across all CPSEs.
    Returns Server-Sent Events for real-time progress tracking.
    """
    def generate():
        import json as _json
        import time

        def send(pct, stage, msg):
            payload = _json.dumps({"progress": pct, "stage": stage, "message": msg})
            return f"data: {payload}\n\n"

        yield send(5, "fetch", "Fetching unapproved materials from MongoDB...")
        all_materials_cursor = col_materials.find({"status": {"$ne": "Approved"}})
        rows = list(all_materials_cursor)
        
        if not rows:
            yield send(100, "error", "No data available in MongoDB. Upload a file first.")
            return

        yield send(10, "fetch", f"Loaded {len(rows)} materials from database.")
        time.sleep(0.3)

        # Extract descriptions
        desc_field = "material_description"
        spec_field = "technical_specs"
        raw_texts = []
        for r in rows:
            desc = r.get(desc_field, "")
            spec = r.get(spec_field, "")
            combined = f"{desc} {spec}".strip()
            raw_texts.append(combined if combined else str(r.get("local_material_code", "")))

        if len(raw_texts) == 0:
            yield send(100, "error", "No records found.")
            return

        yield send(20, "preprocess", f"Pre-processing {len(raw_texts)} text descriptions...")
        time.sleep(0.2)
        processed = preprocess_batch(raw_texts)
        yield send(30, "preprocess", "Text normalization complete.")

        yield send(35, "attributes", "Extracting technical attributes (UOM, specs, dimensions)...")
        time.sleep(0.2)
        attributes = extract_attributes_batch(raw_texts)
        yield send(45, "attributes", f"Extracted attributes for {len(attributes)} items.")

        if len(raw_texts) == 1:
            yield send(60, "vectorize", "Only 1 item found. Skipping similarity matching.")
            matches = []
            clusters = [{"member_indices": [0], "metadata": {}}]
        else:
            yield send(50, "vectorize", "Building TF-IDF + Semantic vector space...")
            time.sleep(0.3)
            vectorizer = HybridVectorizer()
            vectorizer.fit(processed)
            yield send(60, "vectorize", "Hybrid vectorizer fitted successfully.")

            yield send(65, "matching", "Running pairwise similarity matching...")
            time.sleep(0.2)
            matcher = MaterialMatcher(vectorizer)
            matches = matcher.find_matches(raw_texts, processed, attributes, MATCH_THRESHOLD)
            yield send(75, "matching", f"Found {len(matches)} duplicate pairs.")

            yield send(80, "clustering", "Clustering matched items into CNMC groups...")
            time.sleep(0.2)
            clusters = matcher.cluster_materials(raw_texts, processed, attributes, MATCH_THRESHOLD)
            yield send(85, "clustering", f"Formed {len(clusters)} clusters.")

        yield send(88, "cnmc", "Generating Common National Material Codes...")
        time.sleep(0.2)
        cnmc_results = generate_cnmc_for_clusters(clusters, raw_texts)
        yield send(92, "cnmc", f"Generated {len(cnmc_results)} CNMC codes.")

        # Build & store results
        yield send(95, "store", "Storing results to MongoDB...")
        match_details = []
        for m in matches:
            ia, ib = m["idx_a"], m["idx_b"]
            match_details.append({
                "item_a": {
                    "index": ia,
                    "description": raw_texts[ia],
                    "cpse": rows[ia].get("cpse_name", ""),
                    "local_code": rows[ia].get("local_material_code", ""),
                },
                "item_b": {
                    "index": ib,
                    "description": raw_texts[ib],
                    "cpse": rows[ib].get("cpse_name", ""),
                    "local_code": rows[ib].get("local_material_code", ""),
                },
                "score": m["score"],
            })

        cluster_details = []
        for cr in cnmc_results:
            members = []
            for idx in cr["member_indices"]:
                members.append({
                    "description": raw_texts[idx],
                    "cpse": rows[idx].get("cpse_name", ""),
                    "local_code": rows[idx].get("local_material_code", ""),
                    "uom": rows[idx].get("unit_of_measure", ""),
                    "qty": rows[idx].get("stock_quantity", ""),
                })
            scores = []
            for m in matches:
                if m["idx_a"] in cr["member_indices"] and m["idx_b"] in cr["member_indices"]:
                    scores.append(m["score"])
            conf_score = round(sum(scores)/len(scores), 2) if scores else 100.0

            cluster_details.append({
                "cnmc_code": cr["cnmc_code"],
                "category": cr["category"],
                "members": members,
                "confidence_score": conf_score,
                "status": "pending",
                "created_at": datetime.utcnow()
            })

        # ── BULLETPROOF STORE: No duplicacy, approved data is sacred ──
        # 1. Matches are always fresh — wipe and re-insert
        col_matches.delete_many({})
        if match_details:
            col_matches.insert_many(match_details)

        # 2. Delete ONLY old pending clusters (approved/rejected stay untouched)
        col_clusters.delete_many({"status": "pending"})

        # 3. Insert new clusters — skip if CNMC code already exists (approved/rejected)
        #    Also apply AUTO-APPROVAL if enabled and confidence >= threshold
        auto_setting = col_settings.find_one({"key": "auto_approve_enabled"})
        threshold_setting = col_settings.find_one({"key": "auto_approve_threshold"})
        auto_enabled = auto_setting.get("value", False) if auto_setting else False
        auto_threshold = float(threshold_setting.get("value", 95)) if threshold_setting else 95.0

        new_inserted = 0
        skipped_approved = 0
        auto_approved = 0
        for c in cluster_details:
            existing = col_clusters.find_one({"cnmc_code": c["cnmc_code"]})
            if existing:
                # Already approved or rejected — don't touch it at all
                skipped_approved += 1
                continue
            else:
                # Auto-approve if enabled, confidence is high enough, AND it's not a unique item (has >1 members)
                if auto_enabled and c.get("confidence_score", 0) >= auto_threshold and len(c.get("members", [])) > 1:
                    c["status"] = "approved"
                    c["updated_by"] = "AI Auto-Approval"
                    c["updated_at"] = datetime.utcnow()
                    auto_approved += 1
                    # Also update individual materials
                    for member in c.get("members", []):
                        col_materials.update_many(
                            {"cpse_name": member.get("cpse"), "local_material_code": member.get("local_code")},
                            {"$set": {"cnmc_code": c["cnmc_code"], "status": "Approved"}}
                        )
                    # Audit log
                    col_audit.insert_one({
                        "cnmc_code": c["cnmc_code"],
                        "action": "approve",
                        "reviewer": f"AI Auto-Approval (score: {c['confidence_score']}% ≥ {auto_threshold}%)",
                        "timestamp": datetime.utcnow(),
                    })
                col_clusters.insert_one(c)
                new_inserted += 1

        all_clusters = list(col_clusters.find({}, {"_id": 0}))
        all_matches = list(col_matches.find({}, {"_id": 0}))

        auto_msg = f" | {auto_approved} auto-approved" if auto_approved > 0 else ""
        yield send(100, "complete", f"Pipeline complete! {len(all_matches)} pairs, {len(all_clusters)} clusters.{auto_msg}")

        # Final result as a special event
        final = _json.dumps({
            "progress": 100,
            "stage": "done",
            "total_items": len(raw_texts),
            "total_matches": len(all_matches),
            "total_clusters": len(all_clusters),
            "auto_approved": auto_approved,
        })
        yield f"data: {final}\n\n"

    return Response(generate(), mimetype='text/event-stream')


# ── AUTO-APPROVAL SETTINGS ───────────────────────────────────────────

@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get all platform settings."""
    settings = {}
    for s in col_settings.find({}, {"_id": 0}):
        settings[s["key"]] = s["value"]
    return jsonify(settings)

@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update platform settings."""
    body = request.get_json(silent=True) or {}
    
    for key, value in body.items():
        col_settings.update_one(
            {"key": key},
            {"$set": {"value": value}},
            upsert=True
        )
    
    # Audit log
    col_audit.insert_one({
        "cnmc_code": "SYSTEM",
        "action": "settings_update",
        "reviewer": session.get("admin_name", "Admin"),
        "timestamp": datetime.utcnow(),
        "details": body,
    })
    
    return jsonify({"success": True, "updated": body})


# ── GET /api/recommendations ─────────────────────────────────────────

@app.route("/api/recommendations", methods=["GET"])
def get_recommendations():
    """
    Return clustered duplicates, match percentages, and proposed CNMC codes
    from MongoDB.
    """
    all_matches = list(col_matches.find({}, {"_id": 0}))
    all_clusters = list(col_clusters.find({}, {"_id": 0}))
    approved_codes = [c["cnmc_code"] for c in all_clusters if c.get("status") == "approved"]

    return jsonify({
        "matches": all_matches,
        "clusters": all_clusters,
        "approved_codes": approved_codes,
        "total_matches": len(all_matches),
        "total_clusters": len(all_clusters),
    })


# ── POST /api/approve ────────────────────────────────────────────────

@app.route("/api/approve", methods=["POST"])
def approve_match():
    """
    Approve or reject a CNMC cluster.
    """
    body = request.get_json(silent=True) or {}
    cnmc_code = body.get("cnmc_code")
    action = body.get("action", "approve")  # approve or reject
    reviewer = body.get("reviewer", "Super Admin")

    if not cnmc_code:
        return jsonify({"error": "cnmc_code is required"}), 400

    target_cluster = col_clusters.find_one({"cnmc_code": cnmc_code})
    if not target_cluster:
        return jsonify({"error": f"Cluster {cnmc_code} not found in DB"}), 404

    now = datetime.utcnow()
    status = "approved" if action == "approve" else "rejected"

    # Update cluster status
    col_clusters.update_one(
        {"cnmc_code": cnmc_code},
        {"$set": {
            "status": status,
            "updated_by": reviewer,
            "updated_at": now
        }}
    )

    # If approved, update the individual materials in the catalog
    if status == "approved":
        for member in target_cluster.get("members", []):
            col_materials.update_many(
                {"cpse_name": member.get("cpse"), "local_material_code": member.get("local_code")},
                {"$set": {
                    "cnmc_code": cnmc_code,
                    "status": "Approved"
                }}
            )
    else:
        for member in target_cluster.get("members", []):
            col_materials.update_many(
                {"cpse_name": member.get("cpse"), "local_material_code": member.get("local_code")},
                {"$unset": {"cnmc_code": ""},
                 "$set": {"status": "Rejected"}}
            )

    # Audit log
    col_audit.insert_one({
        "cnmc_code": cnmc_code,
        "action": action,
        "reviewer": reviewer,
        "timestamp": now,
    })

    return jsonify({
        "cnmc_code": cnmc_code,
        "action": action,
        "status": status,
        "reviewer": reviewer,
    })


# ── POST /api/search ─────────────────────────────────────────────────

@app.route("/api/search", methods=["POST"])
def search_materials():
    """
    Search across all CPSEs by CNMC code, local code, or description.
    """
    body = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    search_type = body.get("search_type", "description")

    if not query:
        return jsonify({"error": "Query is required"}), 400

    results = []
    
    if search_type == "cnmc":
        # Find clusters matching CNMC code (regex, case-insensitive)
        matched_clusters = col_clusters.find({"cnmc_code": {"$regex": query, "$options": "i"}})
        for cluster in matched_clusters:
            for member in cluster.get("members", []):
                member["cnmc_code"] = cluster["cnmc_code"]
                member["status"] = cluster["status"]
                results.append(member)

    elif search_type == "local_code":
        cursor = col_materials.find({"local_material_code": {"$regex": query, "$options": "i"}}, {"_id": 0})
        results = list(cursor)

    else:  # description search
        # Search in description or specs
        cursor = col_materials.find({
            "$or": [
                {"material_description": {"$regex": query, "$options": "i"}},
                {"technical_specs": {"$regex": query, "$options": "i"}}
            ]
        }, {"_id": 0})
        results = list(cursor)

    return jsonify({
        "query": query,
        "search_type": search_type,
        "total_results": len(results),
        "results": results,
    })


# ── GET /api/analytics ───────────────────────────────────────────────

@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    """
    Calculate dynamic metrics directly from MongoDB collections.
    """
    total_materials = col_materials.count_documents({})
    total_uploads = col_uploads.count_documents({})

    # Unique CPSEs
    cpses = col_materials.distinct("cpse_name")

    # Cluster stats
    total_clusters = col_clusters.count_documents({})
    approved_count = col_clusters.count_documents({"status": "approved"})
    pending_count = col_clusters.count_documents({"status": "pending"})
    rejected_count = col_clusters.count_documents({"status": "rejected"})
    reapproval_count = col_clusters.count_documents({"status": "re-approval"})

    total_matches = col_matches.count_documents({})

    # Category breakdown (using MongoDB Aggregation)
    category_counts = {}
    agg_cats = col_clusters.aggregate([{"$group": {"_id": "$category", "count": {"$sum": 1}}}])
    for c in agg_cats:
        category_counts[c["_id"] or "GENERAL"] = c["count"]

    # CPSE-wise material counts
    cpse_counts = {}
    agg_cpse = col_materials.aggregate([{"$group": {"_id": "$cpse_name", "count": {"$sum": 1}}}])
    for c in agg_cpse:
        if c["_id"]:
            cpse_counts[c["_id"].strip()] = c["count"]

    # Stock aggregation for approved clusters (demand aggregation logic)
    demand_aggregation = []
    approved_clusters = col_clusters.find({"status": "approved"})
    for cluster in approved_clusters:
        total_qty = 0
        cpse_breakdown = {}
        for member in cluster.get("members", []):
            try:
                qty = float(member.get("qty", 0) or 0)
            except (ValueError, TypeError):
                qty = 0
            total_qty += qty
            cpse = member.get("cpse", "Unknown")
            cpse_breakdown[cpse] = cpse_breakdown.get(cpse, 0) + qty

        demand_aggregation.append({
            "cnmc_code": cluster["cnmc_code"],
            "category": cluster.get("category", ""),
            "total_quantity": total_qty,
            "cpse_breakdown": cpse_breakdown,
            "member_count": len(cluster.get("members", [])),
        })

    return jsonify({
        "total_materials": total_materials,
        "total_uploads": total_uploads,
        "total_cpses": len(cpses),
        "cpse_list": sorted([c for c in cpses if c]),
        "total_clusters": total_clusters,
        "approved_clusters": approved_count,
        "pending_clusters": pending_count,
        "rejected_clusters": rejected_count,
        "reapproval_clusters": reapproval_count,
        "total_duplicate_pairs": total_matches,
        "category_breakdown": category_counts,
        "cpse_material_counts": cpse_counts,
        "demand_aggregation": demand_aggregation,
        "duplicates_reduced_pct": round(
            (total_matches / total_materials * 100) if total_materials > 0 else 0, 1
        ),
    })


# ── GET /api/demand-aggregation ───────────────────────────────────────

@app.route("/api/demand-aggregation", methods=["GET"])
def demand_aggregation():
    """
    Fetch aggregated required quantities across CPSEs mapped to same CNMC code.
    """
    aggregation = []
    approved_clusters = col_clusters.find({"status": "approved"})

    for cluster in approved_clusters:
        total_qty = 0
        cpse_details = []
        for member in cluster.get("members", []):
            try:
                qty = float(member.get("qty", 0) or 0)
            except (ValueError, TypeError):
                qty = 0
            total_qty += qty
            cpse_details.append({
                "cpse": member.get("cpse", ""),
                "local_code": member.get("local_code", ""),
                "description": member.get("description", ""),
                "quantity": qty,
                "uom": member.get("uom", ""),
            })

        aggregation.append({
            "cnmc_code": cluster["cnmc_code"],
            "category": cluster.get("category", ""),
            "total_aggregated_quantity": total_qty,
            "cpse_count": len(cpse_details),
            "details": cpse_details,
        })

    return jsonify({
        "total_aggregated_groups": len(aggregation),
        "aggregation": aggregation,
    })


# ── INTER-CPSE TRANSFERS ──────────────────────────────────────────────

@app.route("/api/network-availability/<cnmc_code>", methods=["GET"])
def get_network_availability(cnmc_code):
    """Find other CPSEs that have this CNMC code in stock."""
    current_cpse = session.get("cpse_name")
    if not current_cpse:
        return jsonify({"error": "Unauthorized"}), 401

    cnmc_code = cnmc_code.split(" ")[0].strip()

    if not cnmc_code.startswith("CNMC-"):
        local_mat = col_materials.find_one({"cpse_name": current_cpse, "local_material_code": cnmc_code})
        if local_mat and local_mat.get("cnmc_code"):
            cnmc_code = local_mat["cnmc_code"]

    # Find materials with this CNMC, excluding the current CPSE
    matches = list(col_materials.find({
        "cnmc_code": cnmc_code,
        "cpse_name": {"$ne": current_cpse}
    }, {"_id": 0}))

    # Aggregate by CPSE
    availability = {}
    for m in matches:
        cpse = m.get("cpse_name")
        qty = float(m.get("stock_quantity", 0) or 0)
        price = m.get("price", "N/A")
        if cpse not in availability:
            availability[cpse] = {"qty": 0, "uom": m.get("unit_of_measure", "EA"), "desc": m.get("material_description"), "price": price}
        availability[cpse]["qty"] += qty

    results = [{"cpse": k, "quantity": v["qty"], "uom": v["uom"], "description": v["desc"], "price": v["price"]} for k, v in availability.items() if v["qty"] > 0]
    return jsonify({"cnmc_code": cnmc_code, "availability": results})

@app.route("/api/request-transfer", methods=["POST"])
def request_transfer():
    body = request.get_json(silent=True) or {}
    requester = session.get("cpse_name")
    if not requester:
        return jsonify({"error": "Unauthorized"}), 401

    col_transfers.insert_one({
        "transfer_id": f"TRN-{str(uuid.uuid4())[:8].upper()}",
        "cnmc_code": body.get("cnmc_code"),
        "from_cpse": body.get("target_cpse"),
        "to_cpse": requester,
        "requested_qty": body.get("quantity"),
        "status": "Pending",
        "created_at": datetime.utcnow()
    })
    return jsonify({"success": True})

@app.route("/api/my-transfers", methods=["GET"])
def get_my_transfers():
    cpse = session.get("cpse_name")
    if not cpse:
        return jsonify({"error": "Unauthorized"}), 401

    incoming = list(col_transfers.find({"from_cpse": cpse}, {"_id": 0}).sort("created_at", -1))
    outgoing = list(col_transfers.find({"to_cpse": cpse}, {"_id": 0}).sort("created_at", -1))
    return jsonify({"incoming": incoming, "outgoing": outgoing})


@app.route("/api/my-demands", methods=["GET"])
def get_my_demands():
    cpse = session.get("cpse_name")
    if not cpse:
        return jsonify({"error": "Unauthorized"}), 401
    demands = list(col_demands.find({"cpse_name": cpse}, {"_id": 0}).sort("created_at", -1))
    return jsonify(demands)

@app.route("/api/submit-demand", methods=["POST"])
def submit_demand():
    body = request.get_json(silent=True) or {}
    cpse = session.get("cpse_name")
    if not cpse:
        return jsonify({"error": "Unauthorized"}), 401
    
    input_code = body.get("cnmc_code", "").split(" ")[0].strip()
    cnmc_code = input_code
    if not input_code.startswith("CNMC-"):
        local_mat = col_materials.find_one({"cpse_name": cpse, "local_material_code": input_code})
        if local_mat and local_mat.get("cnmc_code"):
            cnmc_code = local_mat["cnmc_code"]
        else:
            return jsonify({"error": "Invalid CNMC or Local Code"}), 400

    col_demands.insert_one({
        "demand_id": f"DMD-{str(uuid.uuid4())[:8].upper()}",
        "cpse_name": cpse,
        "cnmc_code": cnmc_code,
        "quantity": float(body.get("quantity", 0)),
        "target_date": body.get("target_date"),
        "created_at": datetime.utcnow()
    })
    return jsonify({"success": True})
@app.route("/api/update-price", methods=["POST"])
def update_price():
    cpse = session.get("cpse_name")
    if not cpse:
        return jsonify({"error": "Unauthorized"}), 401
    
    body = request.get_json(silent=True) or {}
    local_code = body.get("local_code")
    new_price = body.get("price")
    
    if not local_code or new_price is None:
        return jsonify({"error": "Missing parameters"}), 400
        
    try:
        new_price = float(new_price)
    except ValueError:
        return jsonify({"error": "Invalid price format"}), 400
        
    result = col_materials.update_one(
        {"cpse_name": cpse, "local_material_code": local_code},
        {"$set": {"price": new_price}}
    )
    
    if result.modified_count == 0:
        return jsonify({"error": "Material not found or price unchanged"}), 404
        
    return jsonify({"success": True, "new_price": new_price})


@app.route("/api/my-codes", methods=["GET"])
def get_my_codes():
    cpse = session.get("cpse_name")
    if not cpse:
        return jsonify([])
    
    # Get all local materials for this CPSE
    materials = list(col_materials.find({"cpse_name": cpse}, {"local_material_code": 1, "material_description": 1, "cnmc_code": 1, "_id": 0}))
    
    suggestions = []
    for m in materials:
        if m.get("local_material_code"):
            suggestions.append(f"{m['local_material_code']} - {m.get('material_description', '')}")
        if m.get("cnmc_code"):
            suggestions.append(f"{m['cnmc_code']} - {m.get('material_description', '')}")
            
    # Also get all approved CNMC codes from clusters to suggest them globally
    clusters = list(col_clusters.find({"status": "approved"}, {"cnmc_code": 1, "description": 1, "_id": 0}))
    for c in clusters:
        if c.get("cnmc_code"):
            suggestions.append(f"{c['cnmc_code']} - {c.get('description', '')}")
            
    # Remove duplicates
    suggestions = list(set(suggestions))
    return jsonify(suggestions)

@app.route("/api/national-demand", methods=["GET"])
def get_national_demand():
    # Group demands by CNMC Code
    pipeline = [
        {"$group": {
            "_id": "$cnmc_code",
            "total_quantity": {"$sum": "$quantity"},
            "cpse_count": {"$addToSet": "$cpse_name"},
            "details": {"$push": {"cpse": "$cpse_name", "quantity": "$quantity", "date": "$target_date"}}
        }},
        {"$sort": {"total_quantity": -1}}
    ]
    aggregated = list(col_demands.aggregate(pipeline))
    results = []
    for d in aggregated:
        # get category from clusters
        cluster = col_clusters.find_one({"cnmc_code": d["_id"]})
        cat = cluster.get("category", "Uncategorized") if cluster else "Unknown"
        results.append({
            "cnmc_code": d["_id"],
            "category": cat,
            "total_quantity": d["total_quantity"],
            "cpse_count": len(d["cpse_count"]),
            "details": d["details"]
        })
    return jsonify(results)


# ── GET /api/inventory-overview ───────────────────────────────────────

@app.route("/api/inventory-overview", methods=["GET"])
def inventory_overview():
    """
    National Inventory Overview — for each approved CNMC code, show:
    - Combined total quantity across all CPSEs
    - Individual CPSE-wise quantity breakdown
    - Representative description, category, UOM
    """
    approved_clusters = list(col_clusters.find({"status": "approved"}, {"_id": 0}))

    overview = []
    for cluster in approved_clusters:
        total_qty = 0
        cpse_breakdown = []
        representative_desc = ""
        uom = ""
        for member in cluster.get("members", []):
            try:
                qty = float(member.get("qty", 0) or 0)
            except (ValueError, TypeError):
                qty = 0
            total_qty += qty
            cpse_breakdown.append({
                "cpse": member.get("cpse", "Unknown"),
                "local_code": member.get("local_code", ""),
                "description": member.get("description", ""),
                "quantity": qty,
                "uom": member.get("uom", ""),
            })
            if not representative_desc and member.get("description"):
                representative_desc = member["description"]
            if not uom and member.get("uom"):
                uom = member["uom"]

        # Also check materials collection for price info
        price_info = []
        for member in cluster.get("members", []):
            mat = col_materials.find_one(
                {"cpse_name": member.get("cpse"), "local_material_code": member.get("local_code")},
                {"_id": 0, "price": 1}
            )
            price_info.append({
                "cpse": member.get("cpse", "Unknown"),
                "price": mat.get("price", "N/A") if mat else "N/A",
            })

        overview.append({
            "cnmc_code": cluster["cnmc_code"],
            "category": cluster.get("category", "GENERAL"),
            "description": representative_desc,
            "uom": uom,
            "total_quantity": total_qty,
            "cpse_count": len(cpse_breakdown),
            "cpse_breakdown": cpse_breakdown,
            "price_info": price_info,
        })

    # Sort by total quantity descending
    overview.sort(key=lambda x: x["total_quantity"], reverse=True)

    return jsonify({
        "total_items": len(overview),
        "overview": overview,
    })


# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)

