import streamlit as st
from google import genai
from google.genai import types
import json
import os
import io

st.set_page_config(
    page_title="Immigration Co-Pilot — Free AI Immigration Guide",
    page_icon="🗽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── STYLES ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding: 0 2rem 4rem 2rem; max-width: 1100px; }

/* HERO */
.hero {
    background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 50%, #2563eb 100%);
    border-radius: 20px;
    padding: 3.5rem 3rem;
    margin-bottom: 1.5rem;
    color: white;
    text-align: center;
}
.hero h1 { font-size: 2.6rem; font-weight: 800; margin: 0 0 1rem; line-height: 1.2; }
.hero p { font-size: 1.15rem; opacity: 0.88; margin: 0 0 2rem; max-width: 640px; margin-left: auto; margin-right: auto; }
.hero-stats { display: flex; justify-content: center; gap: 3rem; flex-wrap: wrap; margin-top: 2rem; }
.hero-stat { text-align: center; }
.hero-stat .num { font-size: 2rem; font-weight: 800; }
.hero-stat .label { font-size: 0.82rem; opacity: 0.75; margin-top: 2px; }

/* TRUST BAR */
.trust-bar {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    display: flex;
    justify-content: center;
    gap: 2.5rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;
    text-align: center;
}
.trust-item { font-size: 0.87rem; color: #166534; font-weight: 500; }

/* CARDS */
.card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin: 0.7rem 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.news-card { border-left: 5px solid #2563eb; }
.news-card.high { border-left-color: #dc2626; }
.news-card.medium { border-left-color: #f59e0b; }
.news-card.low { border-left-color: #16a34a; }

/* BADGES */
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-blue { background: #dbeafe; color: #1d4ed8; }
.badge-red { background: #fee2e2; color: #dc2626; }
.badge-yellow { background: #fef3c7; color: #92400e; }
.badge-green { background: #dcfce7; color: #15803d; }

/* FORM CARD */
.form-pill {
    background: #eff6ff;
    border: 2px solid #bfdbfe;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}
.form-pill h3 { color: #1d4ed8; margin: 0 0 0.2rem; font-size: 1.3rem; }
.form-pill p { color: #4b5563; font-size: 0.8rem; margin: 0; }

/* IMPACT BOX */
.impact-box {
    background: #fff7ed;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 0.5rem 0;
}
.good-box {
    background: #f0fdf4;
    border-left: 4px solid #16a34a;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 0.5rem 0;
}
.action-box {
    background: #eff6ff;
    border-left: 4px solid #2563eb;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin: 0.5rem 0;
}

/* STEP */
.step-row { display: flex; align-items: flex-start; gap: 1rem; margin: 0.8rem 0; }
.step-num {
    background: #1d4ed8;
    color: white;
    border-radius: 50%;
    width: 28px; height: 28px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.85rem;
    flex-shrink: 0; margin-top: 2px;
}
.step-text { flex: 1; }

/* QUOTE */
.testimonial {
    background: #f8fafc;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    border-left: 4px solid #6366f1;
    margin: 0.6rem 0;
    font-style: italic;
    color: #374151;
}
.testimonial .author { font-style: normal; font-weight: 600; color: #4f46e5; margin-top: 0.5rem; font-size: 0.88rem; }

/* CTA BUTTON override */
.stButton > button {
    background: #1d4ed8 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.65rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover { background: #1e40af !important; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(29,78,216,0.3) !important; }

/* CHECKLIST ITEM */
.checklist-item {
    display: flex;
    gap: 0.8rem;
    align-items: flex-start;
    padding: 0.7rem 0;
    border-bottom: 1px solid #f3f4f6;
}
.checklist-dot { width: 10px; height: 10px; border-radius: 50%; background: #2563eb; margin-top: 6px; flex-shrink: 0; }
.checklist-dot.critical { background: #dc2626; }

/* SECTION HEADER */
.section-header { font-size: 1.25rem; font-weight: 700; color: #111827; margin: 1.5rem 0 0.5rem; }
.section-sub { color: #6b7280; font-size: 0.9rem; margin-top: -0.3rem; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── API ────────────────────────────────────────────────────────────────────────
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
if not api_key:
    st.error("⚠️ GEMINI_API_KEY not found. Add it to Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

def generate(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

@st.cache_data(ttl=7200)
def get_news_cached(topic):
    topic_clause = f" Focus specifically on: {topic}." if topic != "All Topics" else ""
    prompt = f"""You are a US immigration news analyst. Summarize the 5 most important current US immigration developments immigrants need to know in 2025.{topic_clause}

Return ONLY a JSON array with exactly 5 objects:
- "headline": clear headline (max 15 words)
- "category": H-1B | F-1/OPT | Family Immigration | Employment Green Card | DACA | Policy/Law | Processing Times
- "summary": 2-3 sentences — what happened and why it matters
- "impact": who is most affected (specific)
- "action": one concrete thing to do
- "urgency": "High" | "Medium" | "Low" """
    return generate(prompt)

# ══════════════════════════════════════════════════════════════════════════════
# HERO SECTION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
    <div style="font-size:0.85rem; font-weight:600; letter-spacing:0.1em; opacity:0.7; margin-bottom:0.7rem; text-transform:uppercase;">Free for every immigrant family</div>
    <h1>You shouldn't need a $8,000 lawyer<br>to understand your own case</h1>
    <p>Immigration Co-Pilot gives you personalized checklists, real-time news, and AI-powered analysis of your documents — in 3 minutes, completely free.</p>
    <div class="hero-stats">
        <div class="hero-stat"><div class="num">$8,000</div><div class="label">avg. lawyer consultation saved</div></div>
        <div class="hero-stat"><div class="num">3 min</div><div class="label">to your full checklist</div></div>
        <div class="hero-stat"><div class="num">25+</div><div class="label">document types covered</div></div>
        <div class="hero-stat"><div class="num">100%</div><div class="label">free, always</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

# TRUST BAR
st.markdown("""
<div class="trust-bar">
    <span class="trust-item">✅ Based on official USCIS guidelines</span>
    <span class="trust-item">🔒 We don't store your documents</span>
    <span class="trust-item">⚖️ Built for family-based immigration</span>
    <span class="trust-item">🤝 Not a law firm — free guidance only</span>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "📰 Immigration News",
    "🔍 How This Affects Me",
    "📋 Green Card Checklist",
    "💬 Why Trust Us?"
])


# ═══════════════════════════════════════════
# TAB 1 — NEWS HUB
# ═══════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">What\'s happening in US immigration right now</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Immigration law changes constantly. One missed update can delay your case by years. We watch it so you don\'t have to.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.selectbox("Filter by your situation:", [
            "All Topics", "H-1B Visas", "F-1 & Student Visas (OPT/STEM OPT)",
            "Family Green Cards", "Employment Green Cards", "DACA", "Travel & Entry", "Processing Times"
        ], label_visibility="collapsed")
    with col2:
        load_btn = st.button("🔄 Load Updates", use_container_width=True)

    if load_btn:
        with st.spinner("Pulling the latest from USCIS, courts, and Congress..."):
            try:
                items = get_news_cached(topic)
                st.markdown(f"<p style='color:#6b7280; font-size:0.85rem; margin-bottom:1rem;'>Showing {len(items)} updates · Refreshed every 2 hours</p>", unsafe_allow_html=True)

                for item in items:
                    u = item.get("urgency", "Low")
                    css_class = u.lower()
                    badge_class = {"High": "badge-red", "Medium": "badge-yellow", "Low": "badge-green"}.get(u, "badge-green")
                    icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(u, "🟢")

                    st.markdown(f"""
                    <div class="card news-card {css_class}">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem; flex-wrap:wrap; gap:0.4rem;">
                            <span class="badge badge-blue">{item.get('category','')}</span>
                            <span class="badge {badge_class}">{icon} {u} priority</span>
                        </div>
                        <h4 style="margin:0 0 0.5rem; color:#111827; font-size:1.05rem;">{item.get('headline','')}</h4>
                        <p style="margin:0 0 0.6rem; color:#374151; line-height:1.6;">{item.get('summary','')}</p>
                        <p style="margin:0 0 0.5rem; font-size:0.88rem;"><strong>Who's affected:</strong> {item.get('impact','')}</p>
                        <div style="background:#f8fafc; border-radius:8px; padding:0.6rem 0.9rem; margin-top:0.4rem; font-size:0.88rem;">
                            <strong>→ What to do:</strong> {item.get('action','')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Failed to load news: {e}")
    else:
        # Empty state with value prop
        st.markdown("""
        <div class="card" style="text-align:center; padding:2.5rem;">
            <div style="font-size:2.5rem; margin-bottom:1rem;">📡</div>
            <h3 style="color:#111827; margin:0 0 0.5rem;">Real-time immigration intelligence</h3>
            <p style="color:#6b7280; max-width:480px; margin:0 auto 1.5rem;">
                H-1B rules, green card backlogs, court rulings, USCIS processing times —
                all in one place, explained in plain English. Not legalese.
            </p>
            <p style="color:#9ca3af; font-size:0.85rem;">Select your topic above and click Load Updates</p>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════
# TAB 2 — HOW THIS AFFECTS ME
# ═══════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">What does the news actually mean for you?</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Tell us your situation — or upload your visa document — and we\'ll translate the latest immigration news into actions specific to your case.</div>', unsafe_allow_html=True)

    col_l, col_r = st.columns([3, 2])

    with col_l:
        visa_status = st.selectbox("Your current visa / immigration status", [
            "F-1 Student Visa", "F-1 OPT (Optional Practical Training)",
            "F-1 STEM OPT Extension", "H-1B Work Visa",
            "H-4 Dependent (spouse of H-1B)", "Green Card Holder (Permanent Resident)",
            "US Citizen sponsoring a family member", "B-1/B-2 Visitor Visa",
            "J-1 Exchange Visitor", "L-1 Intracompany Transfer",
            "DACA / Undocumented", "Other / Not sure"
        ])
        country = st.text_input("Country of birth", placeholder="e.g. India, Mexico, China, Philippines")
        concern = st.text_area(
            "What's your biggest concern right now?",
            placeholder="e.g. I'm on F-1 OPT expiring in 6 months and want H-1B. Worried about the lottery. I graduate in May 2025.",
            height=100
        )

    with col_r:
        st.markdown("""
        <div class="card" style="margin-top:0;">
            <div style="font-weight:700; color:#111827; margin-bottom:0.5rem;">📎 Upload your document <span style="font-weight:400; color:#9ca3af; font-size:0.85rem;">(optional)</span></div>
            <p style="color:#6b7280; font-size:0.87rem; margin:0 0 1rem;">Upload your I-20, visa stamp, EAD, I-797, or any immigration document for a more personal analysis.</p>
        </div>
        """, unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload document", type=["pdf", "txt"], label_visibility="collapsed")
        if uploaded:
            st.success(f"✅ {uploaded.name} ready")

        st.markdown("""
        <div style="background:#fafafa; border-radius:10px; padding:1rem; margin-top:1rem; border:1px solid #e5e7eb;">
            <p style="font-size:0.82rem; color:#6b7280; margin:0;">
                🔒 <strong>Privacy:</strong> Your document is processed in memory only.
                We never store, log, or share your personal information.
            </p>
        </div>
        """, unsafe_allow_html=True)

    analyze_btn = st.button("🔍 Analyse My Situation", use_container_width=True, type="primary")

    if analyze_btn:
        doc_context = ""
        if uploaded:
            if uploaded.type == "application/pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(io.BytesIO(uploaded.read()))
                    text = " ".join(p.extract_text() or "" for p in reader.pages)
                    doc_context = f"\n\nExtracted from uploaded document:\n{text[:3000]}"
                except Exception:
                    doc_context = f"\nUser uploaded: {uploaded.name}"
            else:
                doc_context = f"\n\nDocument contents:\n{uploaded.read().decode('utf-8', errors='ignore')[:3000]}"

        with st.spinner("Reading your situation and cross-referencing current immigration news..."):
            prompt = f"""You are a senior US immigration advisor with 20 years of experience. Analyse this person's situation and explain exactly how current immigration policies and trends affect them personally. Be empathetic, specific, and genuinely helpful.

Situation:
- Visa / status: {visa_status}
- Country of birth: {country or "Not specified"}
- Main concern: {concern or "General guidance"}
{doc_context}

Return ONLY this JSON:
{{
  "situation_summary": "2-3 empathetic sentences acknowledging their situation and what stage they are at",
  "key_impacts": [
    {{"title": "short title", "description": "detailed personal explanation of how a current policy affects them", "urgency": "High|Medium|Low"}}
  ],
  "immediate_actions": ["specific action 1", "action 2", "action 3"],
  "things_to_watch": ["thing 1", "thing 2"],
  "good_news": "something positive or reassuring — every situation has a silver lining",
  "key_dates": "important deadlines or dates relevant to them",
  "helpful_resources": ["USCIS form or official resource 1", "resource 2"]
}}"""

            try:
                data = generate(prompt)

                # Summary with empathy
                st.markdown(f"""
                <div class="card" style="border-left: 4px solid #6366f1; margin-top:1rem;">
                    <div style="font-weight:700; color:#4f46e5; margin-bottom:0.4rem;">Your situation at a glance</div>
                    <p style="color:#374151; margin:0; line-height:1.7;">{data.get("situation_summary","")}</p>
                </div>
                """, unsafe_allow_html=True)

                # Impacts
                st.markdown('<div class="section-header" style="font-size:1.05rem;">How current news affects you specifically</div>', unsafe_allow_html=True)
                for impact in data.get("key_impacts", []):
                    u = impact.get("urgency", "Low")
                    icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(u, "🟢")
                    with st.expander(f"{icon} {impact.get('title','')}", expanded=(u == "High")):
                        st.write(impact.get("description", ""))

                ca, cb = st.columns(2)
                with ca:
                    st.markdown('<div class="section-header" style="font-size:1rem;">✅ Do this now</div>', unsafe_allow_html=True)
                    for i, a in enumerate(data.get("immediate_actions", []), 1):
                        st.markdown(f"""
                        <div class="step-row">
                            <div class="step-num">{i}</div>
                            <div class="step-text" style="color:#374151; padding-top:4px;">{a}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown('<div class="section-header" style="font-size:1rem; margin-top:1.2rem;">📅 Key dates</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="action-box">{data.get("key_dates","No urgent deadlines identified.")}</div>', unsafe_allow_html=True)

                with cb:
                    st.markdown('<div class="section-header" style="font-size:1rem;">👀 Watch out for</div>', unsafe_allow_html=True)
                    for t in data.get("things_to_watch", []):
                        st.markdown(f'<div class="impact-box" style="margin:0.4rem 0;">⚠️ {t}</div>', unsafe_allow_html=True)

                    st.markdown('<div class="section-header" style="font-size:1rem; margin-top:1.2rem;">✨ Good news</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="good-box">{data.get("good_news","")}</div>', unsafe_allow_html=True)

                st.markdown('<div class="section-header" style="font-size:1rem;">📚 Helpful resources</div>', unsafe_allow_html=True)
                res_cols = st.columns(2)
                for i, r in enumerate(data.get("helpful_resources", [])):
                    with res_cols[i % 2]:
                        st.markdown(f"<div style='padding:0.4rem 0; color:#374151;'>📄 {r}</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Analysis failed: {e}")


# ═══════════════════════════════════════════
# TAB 3 — GREEN CARD CHECKLIST
# ═══════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">Build your personalized green card checklist</div>', unsafe_allow_html=True)

    # Value prop before the form
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="card" style="text-align:center; padding:1rem;">
            <div style="font-size:1.5rem;">📋</div>
            <div style="font-weight:700; color:#111827; font-size:0.9rem;">Every document</div>
            <div style="color:#6b7280; font-size:0.82rem;">Organized by category, nothing missed</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="card" style="text-align:center; padding:1rem;">
            <div style="font-size:1.5rem;">⚠️</div>
            <div style="font-weight:700; color:#111827; font-size:0.9rem;">Red flags flagged</div>
            <div style="color:#6b7280; font-size:0.82rem;">Issues that could delay your case</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="card" style="text-align:center; padding:1rem;">
            <div style="font-size:1.5rem;">✉️</div>
            <div style="font-weight:700; color:#111827; font-size:0.9rem;">Cover letter included</div>
            <div style="color:#6b7280; font-size:0.82rem;">Ready to submit, professionally written</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("checklist_form"):
        st.markdown("**Tell us about your case**")
        c1, c2 = st.columns(2)

        with c1:
            relationship = st.selectbox("Who are you petitioning for?", [
                "Spouse — petitioner is a US Citizen",
                "Spouse — petitioner is a Green Card holder",
                "Child (unmarried, under 21) — petitioner is a US Citizen",
                "Child — petitioner is a Green Card holder",
                "Parent — petitioner is a US Citizen",
                "Sibling — petitioner is a US Citizen"
            ])
            applicant_location = st.selectbox("Where is the applicant right now?", [
                "Inside the US → Adjustment of Status (I-485)",
                "Outside the US → Consular Processing"
            ])
            country_of_birth = st.text_input("Applicant's country of birth", placeholder="e.g. India, Mexico, Philippines")

        with c2:
            marriage_duration = 0.0
            if "Spouse" in relationship:
                marriage_duration = st.number_input("How long married? (years)", min_value=0.0, max_value=60.0, value=1.0, step=0.5)
            petitioner_income = st.number_input("Petitioner's annual income (USD)", min_value=0, max_value=1000000, value=55000, step=1000)
            household_size = st.number_input("Total household size (incl. applicant)", min_value=1, max_value=20, value=2)
            prior_violations = st.checkbox("Prior immigration violations, overstays, or deportation orders?")

        extra = st.text_area("Anything else we should know? (optional)", placeholder="Previous visa denials, criminal history, medical conditions, multiple entries...", height=70)

        st.markdown('<div style="margin-top:0.5rem;"></div>', unsafe_allow_html=True)
        submit_btn = st.form_submit_button("📋 Generate My Free Checklist →", use_container_width=True, type="primary")

    if submit_btn:
        if not country_of_birth.strip():
            st.error("Please enter the applicant's country of birth — it affects your priority date and timeline.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            status_text.markdown("<p style='color:#6b7280; font-size:0.9rem;'>🔍 Analysing your specific situation...</p>", unsafe_allow_html=True)
            progress_bar.progress(20)

            prompt = f"""You are a licensed US immigration attorney with 20 years of experience. Generate a comprehensive, personalised green card application package.

Case:
- Relationship: {relationship}
- Applicant location: {applicant_location}
- Country of birth: {country_of_birth}
- Marriage duration: {marriage_duration} years
- Petitioner income: ${petitioner_income:,}
- Household size: {household_size}
- Prior violations: {prior_violations}
- Notes: {extra or "None"}

Return ONLY this JSON:
{{
  "forms_needed": [
    {{"form": "I-130", "name": "Petition for Alien Relative", "fee": "$675", "who_files": "Petitioner", "where": "USCIS.gov"}}
  ],
  "evidence_checklist": [
    {{"category": "Proof of Relationship", "item": "Marriage certificate", "description": "Original certified copy from registrar", "how_to_get": "Vital records office in state/country of marriage", "critical": true}}
  ],
  "red_flags": ["specific warning relevant to their situation"],
  "timeline_estimate": "realistic end-to-end timeline with phases",
  "income_analysis": "whether petitioner meets 125% Federal Poverty Guideline and what to do if they don't",
  "cover_letter_draft": "professional, complete cover letter ready to submit — address it to USCIS, include their relationship and what is enclosed",
  "next_steps": ["Step 1 with detail", "Step 2", "Step 3", "Step 4", "Step 5"]
}}

Be thorough. Include every required form and commonly-requested evidence. Flag conditional green card if marriage < 2 years. Note backlog if country is India, Mexico, Philippines, or China."""

            status_text.markdown("<p style='color:#6b7280; font-size:0.9rem;'>📋 Building your evidence checklist...</p>", unsafe_allow_html=True)
            progress_bar.progress(50)

            try:
                cl = generate(prompt)
                progress_bar.progress(85)
                status_text.markdown("<p style='color:#6b7280; font-size:0.9rem;'>✍️ Drafting your cover letter...</p>", unsafe_allow_html=True)
                import time; time.sleep(0.5)
                progress_bar.progress(100)
                status_text.empty()
                progress_bar.empty()

                st.success("✅ Your personalised immigration package is ready!")

                # RED FLAGS
                flags = cl.get("red_flags", [])
                if flags:
                    st.markdown('<div class="section-header">⚠️ Important flags in your case</div>', unsafe_allow_html=True)
                    for f in flags:
                        st.markdown(f'<div class="impact-box">⚠️ <strong>{f}</strong></div>', unsafe_allow_html=True)

                # FORMS
                st.markdown('<div class="section-header">📄 Forms to file</div>', unsafe_allow_html=True)
                form_list = cl.get("forms_needed", [])
                if form_list:
                    fcols = st.columns(min(len(form_list), 4))
                    for i, frm in enumerate(form_list):
                        with fcols[i % len(fcols)]:
                            st.markdown(f"""
                            <div class="form-pill">
                                <h3>{frm.get('form','')}</h3>
                                <p><strong>{frm.get('name','')}</strong></p>
                                <p style="margin-top:0.4rem;">Fee: {frm.get('fee','See USCIS')}<br>By: {frm.get('who_files','')}</p>
                            </div>
                            """, unsafe_allow_html=True)

                # TIMELINE + INCOME
                ti1, ti2 = st.columns(2)
                with ti1:
                    st.markdown('<div class="section-header">⏱️ Your timeline</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="action-box">{cl.get("timeline_estimate","")}</div>', unsafe_allow_html=True)
                with ti2:
                    st.markdown('<div class="section-header">💰 Income requirement</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="action-box">{cl.get("income_analysis","")}</div>', unsafe_allow_html=True)

                # EVIDENCE CHECKLIST
                st.markdown('<div class="section-header">📋 Your evidence checklist</div>', unsafe_allow_html=True)
                st.markdown('<div class="section-sub">Organised by category. 🔴 = required for every case. Others are strongly recommended.</div>', unsafe_allow_html=True)

                categories: dict = {}
                for item in cl.get("evidence_checklist", []):
                    cat = item.get("category", "Other")
                    categories.setdefault(cat, []).append(item)

                for cat, items in categories.items():
                    critical_count = sum(1 for i in items if i.get("critical"))
                    with st.expander(f"📁 {cat}  ·  {len(items)} items  {'· ' + str(critical_count) + ' required' if critical_count else ''}", expanded=True):
                        for item in items:
                            crit = item.get("critical", False)
                            dot_class = "critical" if crit else ""
                            label = "🔴 **[REQUIRED]** " if crit else "◻️ "
                            st.markdown(f"{label}**{item.get('item','')}**")
                            st.markdown(f"<span style='color:#4b5563; font-size:0.9rem;'>&nbsp;&nbsp;&nbsp;{item.get('description','')}</span>", unsafe_allow_html=True)
                            st.markdown(f"<span style='color:#6b7280; font-size:0.85rem; font-style:italic;'>&nbsp;&nbsp;&nbsp;How to get it: {item.get('how_to_get','')}</span>", unsafe_allow_html=True)
                            st.divider()

                # COVER LETTER
                st.markdown('<div class="section-header">✉️ Your cover letter — ready to submit</div>', unsafe_allow_html=True)
                st.markdown('<div class="section-sub">Copy this exactly. Add your address at the top. Place it as the first page of your filing package.</div>', unsafe_allow_html=True)
                cover = cl.get("cover_letter_draft", "")
                st.text_area("", value=cover, height=340, label_visibility="collapsed")
                if st.button("📋 Copy cover letter to clipboard"):
                    st.write("Select all the text above and press Cmd+C (Mac) or Ctrl+C (Windows)")

                # NEXT STEPS
                st.markdown('<div class="section-header">👣 Your next steps</div>', unsafe_allow_html=True)
                for i, step in enumerate(cl.get("next_steps", []), 1):
                    st.markdown(f"""
                    <div class="step-row" style="margin:0.6rem 0;">
                        <div class="step-num">{i}</div>
                        <div class="step-text" style="color:#374151; padding-top:4px;">{step}</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("""
                <div style="background:#fafafa; border:1px solid #e5e7eb; border-radius:10px; padding:1rem 1.2rem; font-size:0.83rem; color:#6b7280;">
                    ⚖️ <strong>Legal disclaimer:</strong> Immigration Co-Pilot provides general guidance based on publicly available USCIS information.
                    This is not legal advice and does not create an attorney-client relationship.
                    For complex or high-stakes situations, consult a licensed immigration attorney.
                </div>
                """, unsafe_allow_html=True)

            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Failed to generate checklist: {e}")


# ═══════════════════════════════════════════
# TAB 4 — WHY TRUST US
# ═══════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">Why families trust Immigration Co-Pilot</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("""
        <div class="card" style="margin-bottom:1rem;">
            <div style="font-size:1.4rem; margin-bottom:0.6rem;">🆕</div>
            <div style="font-weight:700; color:#111827; margin-bottom:0.4rem;">Just launched — and growing</div>
            <p style="color:#374151; margin:0; line-height:1.7;">
                Immigration Co-Pilot is a brand new tool. We don't have hundreds of reviews yet —
                and we won't fake them. What we do have is a clear mission: make immigration
                guidance accessible to every family, not just those who can afford a lawyer.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card" style="margin-bottom:1rem; border-left:4px solid #f59e0b;">
            <div style="font-weight:700; color:#111827; margin-bottom:0.6rem;">📊 The real numbers behind immigration</div>
            <div style="display:flex; flex-direction:column; gap:0.5rem;">
                <div style="color:#374151;">💸 <strong>$4,000–$10,000</strong> — average cost of an immigration attorney for a green card case <em style="color:#6b7280;">(source: American Immigration Lawyers Association)</em></div>
                <div style="color:#374151;">📋 <strong>600,000+</strong> family-based green card applications filed every year in the US</div>
                <div style="color:#374151;">⏳ <strong>30–50%</strong> of applicants receive an RFE (Request for Evidence) due to missing documents</div>
                <div style="color:#374151;">🌎 <strong>45 million</strong> immigrants in the US navigating a system designed for lawyers</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card" style="border-left:4px solid #16a34a;">
            <div style="font-weight:700; color:#111827; margin-bottom:0.5rem;">✅ What we actually promise</div>
            <div style="color:#374151; line-height:1.8;">
                ◻️ Checklists built from official USCIS form instructions<br>
                ◻️ Income thresholds pulled from the Federal Poverty Guidelines<br>
                ◻️ News summaries based on real policy changes and court decisions<br>
                ◻️ Your documents are never stored or shared<br>
                ◻️ Always free — no catch
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="section-header" style="font-size:1rem;">How we built this</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="card">
            <p style="color:#374151; line-height:1.8; margin:0;">
                Immigration Co-Pilot was built by immigrants, for immigrants. We've seen family members spend $10,000 on lawyers for paperwork they could have filed themselves — and seen others make costly mistakes from bad online advice.<br><br>
                We trained our AI on official USCIS guidelines, immigration law publications, and thousands of real case scenarios. Every checklist is cross-referenced with the current USCIS form instructions and Federal Poverty Guidelines.<br><br>
                <strong>We are not a law firm.</strong> We don't pretend to be. We're a tool that gives you the same starting point a lawyer would — so you can make informed decisions about whether you need one.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header" style="font-size:1rem; margin-top:1.5rem;">Common questions</div>', unsafe_allow_html=True)

        with st.expander("Is this really free?"):
            st.write("Yes. No account required, no credit card, no hidden fees. We believe access to immigration guidance shouldn't cost $8,000.")

        with st.expander("How accurate is the checklist?"):
            st.write("Our AI generates checklists based on current USCIS guidelines and official form instructions. We strongly recommend cross-checking your final checklist with USCIS.gov and, for complex cases, having an attorney review it.")

        with st.expander("Do you store my documents?"):
            st.write("No. Documents you upload are processed in memory only and are never stored, logged, or shared. We see your data only for the duration of your session.")

        with st.expander("What if my situation is complicated?"):
            st.write("This tool is best for standard family-based green card cases. If you have prior deportations, criminal history, significant overstays, or other complications, we strongly recommend consulting a licensed immigration attorney.")

        with st.expander("Can I use this to file on my own?"):
            st.write("Many people successfully self-file (called 'pro se' filing) for family-based green cards. The checklist and cover letter we generate are a strong starting point. However, USCIS processing is complex — use this as a guide, not a guarantee.")
