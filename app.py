import streamlit as st
import google.generativeai as genai
import json
import os
import io

st.set_page_config(
    page_title="Immigration Co-Pilot",
    page_icon="🗽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .news-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin: 0.8rem 0;
    }
    .badge {
        display: inline-block;
        background: #e8f0fe;
        color: #1a73e8;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .form-card {
        background: #e8f0fe;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        margin: 0.4rem;
    }
    .flag-box {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
    }
    .good-news-box {
        background: #d4edda;
        border-left: 4px solid #28a745;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
    }
    h1 { text-align: center; }
    .subtitle { text-align: center; color: #666; font-size: 1.1rem; margin-top: -0.5rem; margin-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

# ── API setup ──────────────────────────────────────────────────────────────────
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
if not api_key:
    st.error("⚠️ GEMINI_API_KEY not found. Add it to Streamlit secrets or as an environment variable.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("# 🗽 Immigration Co-Pilot")
st.markdown('<p class="subtitle">Your free AI guide to navigating US immigration — news, impact analysis, and personalized checklists.</p>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📰 Immigration News Hub", "🔍 How This Affects Me", "📋 Green Card Checklist"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IMMIGRATION NEWS HUB
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("What's happening in US immigration right now")
    st.caption("AI-curated summaries of the latest policy changes, court rulings, and USCIS updates — explained in plain English.")

    col_filter, col_btn = st.columns([3, 1])
    with col_filter:
        topic = st.selectbox(
            "Filter by topic:",
            ["All Topics", "H-1B Visas", "F-1 & Student Visas (OPT/STEM OPT)",
             "Family Green Cards", "Employment Green Cards", "DACA", "Travel & Entry", "Processing Times"]
        )
    with col_btn:
        st.write("")
        st.write("")
        load_btn = st.button("🔄 Load Updates", use_container_width=True)

    if load_btn:
        with st.spinner("Fetching latest immigration updates..."):
            topic_clause = f" Focus specifically on: {topic}." if topic != "All Topics" else ""
            prompt = f"""You are a US immigration news analyst. Summarize the 5 most important and current US immigration developments that immigrants and visa holders need to know about in 2025.{topic_clause}

Return ONLY a JSON array with exactly 5 objects, each with:
- "headline": clear, informative headline (max 15 words)
- "category": one of: H-1B | F-1/OPT | Family Immigration | Employment Green Card | DACA | Policy/Law | Processing Times
- "summary": 2-3 sentences — what happened and why it matters
- "impact": who is most affected (be specific, e.g. "Indian-born H-1B holders waiting for green cards")
- "action": one concrete thing affected people should do
- "urgency": "High" | "Medium" | "Low"

Be factual and accurate. Cover real policy changes, court decisions, processing time shifts, and executive actions."""

            try:
                resp = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
                items = json.loads(resp.text)

                urgency_colors = {"High": "#dc3545", "Medium": "#fd7e14", "Low": "#28a745"}
                urgency_icons  = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}

                for item in items:
                    u = item.get("urgency", "Low")
                    color = urgency_colors.get(u, "#28a745")
                    icon  = urgency_icons.get(u, "🟢")
                    st.markdown(f"""
                    <div class="news-card" style="border-left: 4px solid {color};">
                        <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                            <span class="badge">{item.get('category','')}</span>
                            <span style="font-size:0.85rem; color:#666;">{icon} {u} priority</span>
                        </div>
                        <h4 style="margin:0.3rem 0 0.5rem;">{item.get('headline','')}</h4>
                        <p style="margin:0 0 0.4rem; color:#333;">{item.get('summary','')}</p>
                        <p style="margin:0 0 0.4rem;"><strong>Who's affected:</strong> {item.get('impact','')}</p>
                        <div style="background:#f8f9fa; border-radius:6px; padding:0.5rem 0.8rem; margin-top:0.5rem;">
                            <strong>What to do:</strong> {item.get('action','')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Failed to load news: {e}")
    else:
        st.info("👆 Select a topic above and click **Load Updates** to see the latest immigration news.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HOW THIS AFFECTS ME
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Tell us your situation — we'll explain what it means for you")
    st.caption("Upload your visa document or just describe your status. We'll connect the latest immigration news to your specific case.")

    col_l, col_r = st.columns(2)

    with col_l:
        visa_status = st.selectbox(
            "Your current visa / immigration status *",
            [
                "F-1 Student Visa",
                "F-1 OPT (Optional Practical Training)",
                "F-1 STEM OPT Extension",
                "H-1B Work Visa",
                "H-4 Dependent (spouse of H-1B)",
                "Green Card Holder (Permanent Resident)",
                "US Citizen sponsoring a family member",
                "B-1/B-2 Visitor Visa",
                "J-1 Exchange Visitor",
                "L-1 Intracompany Transfer",
                "DACA / Undocumented",
                "Other / Not sure"
            ]
        )
        country = st.text_input("Country of birth", placeholder="e.g. India, Mexico, China, Philippines")
        concern = st.text_area(
            "What's your biggest concern or next step?",
            placeholder="e.g. I'm on F-1 OPT expiring in 6 months and need H-1B. I'm worried about the lottery odds.",
            height=110
        )

    with col_r:
        st.write("**Upload a document (optional)**")
        st.caption("Upload your I-20, visa stamp, EAD card, I-797 approval notice, or any immigration document for a more personalised analysis.")
        uploaded = st.file_uploader(
            "Choose file",
            type=["pdf", "txt"],
            label_visibility="collapsed"
        )
        if uploaded:
            st.success(f"✅ {uploaded.name} uploaded")

    analyze_btn = st.button("🔍 Analyse My Situation", use_container_width=True, type="primary")

    if analyze_btn:
        doc_context = ""
        if uploaded:
            if uploaded.type == "application/pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(io.BytesIO(uploaded.read()))
                    text = " ".join(p.extract_text() or "" for p in reader.pages)
                    doc_context = f"\n\nExtracted text from uploaded document:\n{text[:3000]}"
                except Exception:
                    doc_context = f"\nUser uploaded a document: {uploaded.name}"
            elif uploaded.type == "text/plain":
                doc_context = f"\n\nContents of uploaded document:\n{uploaded.read().decode('utf-8', errors='ignore')[:3000]}"

        with st.spinner("Analysing your situation..."):
            prompt = f"""You are an expert US immigration advisor. Analyse this person's immigration situation and explain clearly how current US immigration policies, news, and trends affect them personally.

Their situation:
- Visa / status: {visa_status}
- Country of birth: {country or "Not specified"}
- Main concern: {concern or "General guidance"}
{doc_context}

Return ONLY a JSON object with this exact structure:
{{
  "situation_summary": "2-3 sentence plain-English summary of their current position",
  "key_impacts": [
    {{"title": "short title", "description": "detailed explanation of how a current policy/news item affects them", "urgency": "High|Medium|Low"}}
  ],
  "immediate_actions": ["specific action 1", "action 2", "action 3"],
  "things_to_watch": ["thing 1", "thing 2"],
  "good_news": "any positive aspects, opportunities, or reassurances",
  "key_dates": "important deadlines or dates they should be aware of",
  "helpful_resources": ["USCIS form or resource 1", "resource 2"]
}}

Be specific, factual, and genuinely helpful. Consider their country of birth for priority date backlogs if relevant."""

            try:
                resp = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
                data = json.loads(resp.text)

                st.success("✅ Analysis complete")
                st.info(data.get("situation_summary", ""))

                st.subheader("How current immigration news affects you")
                for impact in data.get("key_impacts", []):
                    u = impact.get("urgency", "Low")
                    icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(u, "🟢")
                    with st.expander(f"{icon} {impact.get('title','')}", expanded=(u == "High")):
                        st.write(impact.get("description", ""))

                ca, cb = st.columns(2)
                with ca:
                    st.subheader("✅ What you should do now")
                    for a in data.get("immediate_actions", []):
                        st.markdown(f"• {a}")
                    st.subheader("📅 Key dates & deadlines")
                    st.write(data.get("key_dates", "No urgent deadlines identified."))

                with cb:
                    st.subheader("👀 Things to watch")
                    for t in data.get("things_to_watch", []):
                        st.markdown(f"• {t}")
                    st.subheader("✨ Good news")
                    st.markdown(f'<div class="good-news-box">{data.get("good_news","")}</div>', unsafe_allow_html=True)

                st.subheader("📚 Helpful resources")
                for r in data.get("helpful_resources", []):
                    st.markdown(f"• {r}")

            except Exception as e:
                st.error(f"Analysis failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GREEN CARD CHECKLIST BUILDER
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Get your personalised green card document checklist")
    st.caption("Answer a few questions and we'll generate every document you need, a cover letter, red flags, and a realistic timeline.")

    with st.form("checklist_form"):
        c1, c2 = st.columns(2)

        with c1:
            relationship = st.selectbox(
                "Who are you petitioning for? *",
                [
                    "Spouse — petitioner is a US Citizen",
                    "Spouse — petitioner is a Green Card holder",
                    "Child (unmarried, under 21) — petitioner is a US Citizen",
                    "Child — petitioner is a Green Card holder",
                    "Parent — petitioner is a US Citizen",
                    "Sibling — petitioner is a US Citizen"
                ]
            )
            applicant_location = st.selectbox(
                "Where is the applicant right now? *",
                [
                    "Inside the US → Adjustment of Status (Form I-485)",
                    "Outside the US → Consular Processing"
                ]
            )
            country_of_birth = st.text_input(
                "Applicant's country of birth *",
                placeholder="e.g. India, Mexico, Philippines"
            )

        with c2:
            marriage_duration = 0.0
            if "Spouse" in relationship:
                marriage_duration = st.number_input(
                    "How long have you been married? (years)",
                    min_value=0.0, max_value=60.0, value=1.0, step=0.5
                )
            petitioner_income = st.number_input(
                "Petitioner's annual income (USD) *",
                min_value=0, max_value=1000000, value=55000, step=1000
            )
            household_size = st.number_input(
                "Total household size (including applicant) *",
                min_value=1, max_value=20, value=2
            )
            prior_violations = st.checkbox(
                "Has the applicant had any prior immigration violations, overstays, or deportation orders?"
            )

        extra = st.text_area(
            "Anything else we should know? (optional)",
            placeholder="e.g. Previous visa denials, pending criminal matters, prior US entries, medical conditions...",
            height=80
        )

        submit_btn = st.form_submit_button("📋 Generate My Checklist", use_container_width=True, type="primary")

    if submit_btn:
        if not country_of_birth.strip():
            st.error("Please enter the applicant's country of birth.")
        else:
            with st.spinner("Building your personalised checklist..."):
                prompt = f"""You are a licensed US immigration attorney. Generate a comprehensive, personalised green card application checklist for this specific case.

Case details:
- Relationship / petition type: {relationship}
- Applicant location: {applicant_location}
- Applicant country of birth: {country_of_birth}
- Marriage duration: {marriage_duration} years
- Petitioner annual income: ${petitioner_income:,}
- Household size: {household_size}
- Prior violations: {prior_violations}
- Additional notes: {extra or "None"}

Return ONLY a JSON object with this structure:
{{
  "forms_needed": [
    {{"form": "I-130", "name": "Petition for Alien Relative", "fee": "$675", "who_files": "Petitioner (US Citizen or LPR)"}}
  ],
  "evidence_checklist": [
    {{"category": "Proof of Relationship", "item": "Marriage certificate", "description": "Original or certified copy issued by the registrar", "how_to_get": "Vital records office in the country/state of marriage", "critical": true}}
  ],
  "red_flags": ["Specific warnings relevant to their situation"],
  "timeline_estimate": "Realistic end-to-end timeline",
  "income_analysis": "Whether petitioner meets 125% Federal Poverty Guideline and what to do if they don't",
  "cover_letter_draft": "A complete, professional cover letter ready to include in the filing package",
  "next_steps": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]
}}

Include ALL required forms AND common supporting documents. Flag if marriage under 2 years triggers a conditional green card. Note priority date backlogs for the applicant's country if relevant. Be thorough and accurate."""

                try:
                    resp = model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.2,
                            response_mime_type="application/json"
                        )
                    )
                    cl = json.loads(resp.text)

                    st.success("✅ Your personalised checklist is ready!")

                    # Red flags
                    flags = cl.get("red_flags", [])
                    if flags:
                        st.subheader("⚠️ Important flags in your case")
                        for f in flags:
                            st.markdown(f'<div class="flag-box">⚠️ {f}</div>', unsafe_allow_html=True)

                    # Forms
                    st.subheader("📄 Forms you need to file")
                    form_cols = st.columns(min(len(cl.get("forms_needed", [])), 4))
                    for i, frm in enumerate(cl.get("forms_needed", [])):
                        with form_cols[i % len(form_cols)]:
                            st.markdown(f"""
                            <div class="form-card">
                                <h3 style="color:#1a73e8; margin:0;">{frm.get('form','')}</h3>
                                <p style="font-size:0.82rem; margin:0.3rem 0;">{frm.get('name','')}</p>
                                <p style="color:#666; font-size:0.78rem;">Fee: {frm.get('fee','See USCIS.gov')}<br>Filed by: {frm.get('who_files','')}</p>
                            </div>
                            """, unsafe_allow_html=True)

                    # Timeline + income
                    t1, t2 = st.columns(2)
                    with t1:
                        st.subheader("⏱️ Timeline estimate")
                        st.info(cl.get("timeline_estimate", ""))
                    with t2:
                        st.subheader("💰 Income requirement")
                        st.write(cl.get("income_analysis", ""))

                    # Evidence checklist grouped by category
                    st.subheader("📋 Evidence checklist")
                    categories: dict = {}
                    for item in cl.get("evidence_checklist", []):
                        cat = item.get("category", "Other")
                        categories.setdefault(cat, []).append(item)

                    for cat, items in categories.items():
                        with st.expander(f"📁 {cat}  ({len(items)} item{'s' if len(items)>1 else ''})", expanded=True):
                            for item in items:
                                crit = item.get("critical", False)
                                label = "🔴 **[REQUIRED]** " if crit else ""
                                st.markdown(f"{label}**{item.get('item','')}**")
                                st.markdown(f"&nbsp;&nbsp;&nbsp;{item.get('description','')}")
                                st.markdown(f"&nbsp;&nbsp;&nbsp;*How to get it: {item.get('how_to_get','')}*")
                                st.divider()

                    # Cover letter
                    st.subheader("✉️ Cover letter draft")
                    st.caption("Copy this, add your address, and include it at the top of your filing package.")
                    st.text_area("", value=cl.get("cover_letter_draft", ""), height=320, label_visibility="collapsed")

                    # Next steps
                    st.subheader("👣 Your next steps")
                    for i, step in enumerate(cl.get("next_steps", []), 1):
                        st.markdown(f"**{i}.** {step}")

                    st.divider()
                    st.caption("⚠️ This tool provides general guidance only and is not legal advice. For complex or high-stakes cases, consult a licensed immigration attorney.")

                except Exception as e:
                    st.error(f"Failed to generate checklist: {e}")
