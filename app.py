import streamlit as st
from google import genai
from google.genai import types
import json
import os
import io
import requests
import feedparser
from datetime import datetime

st.set_page_config(
    page_title="Immigration Co-Pilot",
    page_icon="",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.block-container {
    padding: 2.5rem 2rem 5rem;
    max-width: 860px;
}
h1, h2, h3 { color: #111827; }
p { color: #374151; line-height: 1.7; }

.site-header {
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 1.5rem;
    margin-bottom: 2rem;
}
.site-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #111827;
    margin: 0;
}
.site-desc {
    color: #6b7280;
    font-size: 0.95rem;
    margin-top: 0.3rem;
}

.news-item {
    border-bottom: 1px solid #f3f4f6;
    padding: 1.2rem 0;
}
.news-title {
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
    margin: 0 0 0.3rem;
}
.news-meta {
    font-size: 0.82rem;
    color: #9ca3af;
    margin-bottom: 0.5rem;
}
.news-context {
    color: #4b5563;
    font-size: 0.9rem;
    margin: 0.4rem 0 0;
    line-height: 1.6;
}
.priority-high { color: #dc2626; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.priority-medium { color: #d97706; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.priority-low { color: #059669; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }

.section-label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9ca3af;
    margin-bottom: 0.8rem;
}
.info-box {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
}
.flag-box {
    background: #fef9f0;
    border-left: 3px solid #f59e0b;
    padding: 0.8rem 1rem;
    border-radius: 0 6px 6px 0;
    margin: 0.5rem 0;
    font-size: 0.9rem;
    color: #374151;
}
.form-tag {
    display: inline-block;
    background: #eff6ff;
    color: #1d4ed8;
    padding: 0.3rem 0.8rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.85rem;
    margin: 0.2rem;
}
.step-item {
    display: flex;
    gap: 1rem;
    padding: 0.6rem 0;
    border-bottom: 1px solid #f3f4f6;
    align-items: flex-start;
}
.step-num {
    font-size: 0.8rem;
    font-weight: 700;
    color: #1d4ed8;
    padding-top: 2px;
    flex-shrink: 0;
    width: 20px;
}
.stButton > button {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1.5px solid #d1d5db !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.4rem !important;
    font-size: 0.9rem !important;
}
.stButton > button:hover {
    background: #f9fafb !important;
    color: #111827 !important;
    border-color: #9ca3af !important;
}
a { color: #1d4ed8; }
</style>
""", unsafe_allow_html=True)

# API setup
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
if not api_key:
    st.error("GEMINI_API_KEY not found. Add it to Streamlit secrets.")
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

# Read USCIS news from the JSON file saved by GitHub Actions every 2 days
def fetch_uscis_news():
    try:
        with open("data/uscis_news.json", "r") as f:
            data = json.load(f)
        items = data.get("items", [])
        fetched_at = data.get("fetched_at", "")
        if items:
            return {"source": "file", "items": items, "fetched_at": fetched_at}
    except Exception:
        pass
    return {"source": "unavailable", "items": [], "fetched_at": ""}

# Fetch Federal Register immigration rules, cached 48 hours
@st.cache_data(ttl=172800)
def fetch_federal_register():
    try:
        url = "https://www.federalregister.gov/api/v1/documents.json"
        params = {
            "per_page": 5,
            "order": "newest",
            "conditions[agencies][]": ["department-of-homeland-security", "executive-office-for-immigration-review"],
            "conditions[type][]": ["Rule", "Proposed Rule", "Notice"]
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        results = []
        for doc in data.get("results", []):
            results.append({
                "title": doc.get("title", ""),
                "link": doc.get("html_url", ""),
                "date": doc.get("publication_date", ""),
                "type": doc.get("type", ""),
                "abstract": (doc.get("abstract") or "")[:300]
            })
        return results
    except Exception:
        return []

# Use Gemini to add plain-English context to real news items, cached 48 hours
@st.cache_data(ttl=172800)
def enrich_news(news_items_json, topic_filter):
    items = json.loads(news_items_json) if isinstance(news_items_json, str) else news_items_json
    if not items:
        return []

    filtered = items
    if topic_filter != "All":
        topic_keywords = {
            "H-1B": ["h-1b", "h1b", "specialty occupation", "work visa", "h1", "employer", "petition", "cap", "lottery", "work authorization", "employment"],
            "F-1 / Students": ["f-1", "f1", "student", "opt", "stem", "daca", "cap-gap", "university", "college", "sevis"],
            "Family Green Cards": ["family", "relative", "spouse", "i-130", "i-485", "adjustment", "immediate relative", "petition", "green card"],
            "Employment Green Cards": ["employment", "eb-1", "eb-2", "eb-3", "perm", "priority date", "labor", "green card", "permanent resident"],
        }
        keywords = topic_keywords.get(topic_filter, [])
        if keywords:
            specific = [i for i in items if any(k in (i.get("title","") + i.get("summary","")).lower() for k in keywords)]
            # Use specific matches if any, otherwise show all immigration news
            filtered = specific if specific else items

    topic_instruction = ""
    if topic_filter != "All":
        topic_instruction = f'\n\nContext: the user selected "{topic_filter}". Prioritize items relevant to that group. For items that are general immigration policy (not specific to any visa type), include them — they likely affect everyone. Only skip items that are clearly DHS internal operations, staff bios, IT systems, or completely unrelated to immigration.'

    prompt = f"""You are an immigration news analyst. For each news item below, write a plain 2-sentence explanation of what it means for immigrants.

Include an item if it relates to: visas, green cards, citizenship, immigration policy, border policy, executive orders affecting immigrants, work authorization, travel restrictions, or any government action that could affect someone living in or trying to come to the US. When in doubt, include it.

Only skip items that are purely about DHS internal IT systems, staff bios, or topics with zero connection to immigrants (e.g. domestic disaster relief with no immigration angle).

News items: {json.dumps(filtered[:8])}{topic_instruction}

Priority rules — be conservative:
- "high": action needed now (imminent deadline, rule just took effect)
- "medium": important to be aware of, no immediate action
- "low": background context, long-term or unclear impact
Default to "medium" for most items.

Return a JSON array. Each object:
- "title": same title as input
- "link": same link as input
- "published": same published date as input
- "source": same source as input (e.g. "USCIS", "DHS", "White House")
- "plain_summary": 2 plain sentences — what happened and who it affects
- "priority": "high" | "medium" | "low"
- "affects": specific group (e.g. "H-1B holders", "all visa applicants", "asylum seekers")
"""
    return generate(prompt)


# Header
st.markdown("""
<div class="site-header">
    <div class="site-title">Immigration Co-Pilot</div>
    <div class="site-desc">A free tool that pulls real information from government sources and explains what it means for your case.</div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["News", "Your Situation", "Green Card Checklist", "About"])


# TAB 1 - NEWS
with tab1:
    st.markdown("### What's happening in US immigration")
    st.markdown(
        "<p style='color:#6b7280; font-size:0.9rem; margin-bottom:1.5rem;'>"
        "Updated from USCIS.gov and the Federal Register every 48 hours."
        "</p>",
        unsafe_allow_html=True
    )

    topic_filter = st.selectbox(
        "Filter by topic",
        ["All", "H-1B", "F-1 / Students", "Family Green Cards", "Employment Green Cards"],
        label_visibility="collapsed"
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        load = st.button("Load news")

    if load:
        with st.spinner("Fetching from USCIS.gov and the Federal Register..."):
            result = fetch_uscis_news()
            raw_items = result.get("items", [])
            source = result.get("source", "unavailable")

            fetched_at = result.get("fetched_at", "")
            if fetched_at:
                try:
                    fetched_date = datetime.fromisoformat(fetched_at).strftime("%B %d, %Y")
                except Exception:
                    fetched_date = datetime.now().strftime("%B %d, %Y")
            else:
                fetched_date = datetime.now().strftime("%B %d, %Y")

            if source == "file" and raw_items:
                enriched = enrich_news(json.dumps(raw_items), topic_filter) or []
                # If filter returned nothing, show all items with a note
                if not enriched and topic_filter != "All":
                    enriched = enrich_news(json.dumps(raw_items), "All") or []
                    st.markdown(
                        f"<p style='color:#9ca3af; font-size:0.82rem; margin-bottom:0.5rem;'>"
                        f"No news specifically about <strong>{topic_filter}</strong> in the latest update — showing all immigration news instead.</p>",
                        unsafe_allow_html=True
                    )
                source_note = f"From USCIS.gov — last updated {fetched_date}"
            else:
                fallback_prompt = f"""Summarize the most important US immigration developments from 2024-2025 that immigrants need to know about right now.{' Focus on: ' + topic_filter if topic_filter != 'All' else ''}

Include recent executive actions, policy changes from the Trump administration (January 2025 onwards), USCIS rule changes, visa processing changes, travel restrictions, and enforcement priorities. Cover things like:
- Executive orders affecting immigration (birthright citizenship, travel bans, deportation policies)
- H-1B lottery and rule changes
- Green card processing backlogs and priority date movements
- F-1/OPT/STEM OPT policy changes
- Changes to asylum and refugee admissions
- I-485 and adjustment of status processing updates

Rules:
- Only include things you are confident are factually accurate
- Do NOT invent specific dates — use "early 2025", "2024", or "ongoing"
- Priority: "high" only if someone needs to act now. Most are "medium". "low" for background info
- Write plainly. No hype. Two factual sentences per item.

Return a JSON array of up to 8 items. Each object:
- "title": factual headline (not sensational)
- "link": most relevant official URL (whitehouse.gov, uscis.gov, dhs.gov, state.gov, or federalregister.gov)
- "published": approximate period only ("early 2025", "2024", "ongoing")
- "plain_summary": 2 plain sentences — what changed and who it affects
- "priority": "high" | "medium" | "low"
- "affects": specific group affected
- "source": agency name (e.g. "White House", "USCIS", "DHS", "State Department")"""
                enriched = generate(fallback_prompt)
            source_note = f"Based on USCIS.gov policy updates — {datetime.now().strftime('%B %d, %Y')}"

            if not enriched:
                st.markdown("<div class='info-box'>No news available right now. Check back after the next update.</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<p style='color:#9ca3af; font-size:0.82rem; margin-bottom:1rem;'>{source_note}</p>",
                    unsafe_allow_html=True
                )
                for item in enriched:
                    p = item.get("priority", "low")
                    priority_html = f'<span class="priority-{p}">{p} priority</span>'
                    pub = item.get("published", "")[:16] if item.get("published") else ""
                    link = item.get("link", "https://www.uscis.gov/newsroom")
                    source_tag = item.get("source", "")
                    source_html = f'&nbsp;·&nbsp; <span style="color:#9ca3af; font-size:0.8rem;">{source_tag}</span>' if source_tag else ""
                    st.markdown(f"""
                    <div class="news-item">
                        <div class="news-meta">{pub} &nbsp;·&nbsp; {priority_html}{source_html} &nbsp;·&nbsp; {item.get("affects","")}</div>
                        <div class="news-title"><a href="{link}" target="_blank">{item.get("title","")}</a></div>
                        <div class="news-context">{item.get("plain_summary","")}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Federal Register always works (public API)
            st.markdown("---")
            st.markdown("<div class='section-label'>Recent regulatory activity — Federal Register</div>", unsafe_allow_html=True)
            fr_items = fetch_federal_register()
            if fr_items:
                for doc in fr_items:
                    st.markdown(f"""
                    <div class="news-item">
                        <div class="news-meta">{doc.get("date","")} &nbsp;·&nbsp; {doc.get("type","")}</div>
                        <div class="news-title"><a href="{doc.get('link','#')}" target="_blank">{doc.get("title","")}</a></div>
                        {"<div class='news-context'>" + doc.get("abstract","") + "</div>" if doc.get("abstract") else ""}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("<p style='color:#9ca3af; font-size:0.88rem;'>Federal Register data unavailable right now.</p>", unsafe_allow_html=True)
    else:
        st.markdown(
            "<div class='info-box'>"
            "This tab pulls directly from <strong>USCIS.gov</strong>'s news feed and the "
            "<strong>Federal Register</strong> — the official source for US regulatory changes. "
            "Results are cached for 48 hours so we're not hitting government servers constantly."
            "</div>",
            unsafe_allow_html=True
        )


# TAB 2 - YOUR SITUATION
with tab2:
    st.markdown("### How does the current situation affect you?")
    st.markdown(
        "<p style='color:#6b7280; font-size:0.9rem;'>"
        "Describe your visa status and what you're planning to do. "
        "You can also upload a document and we'll read your specific details from it."
        "</p>",
        unsafe_allow_html=True
    )

    visa_status = st.selectbox("Your current status", [
        "F-1 Student Visa",
        "F-1 OPT",
        "F-1 STEM OPT",
        "H-1B",
        "H-4 (dependent of H-1B holder)",
        "Green Card holder",
        "US Citizen sponsoring a family member",
        "B-1/B-2 visitor",
        "J-1",
        "L-1",
        "DACA",
        "Other"
    ])

    col_a, col_b = st.columns(2)
    with col_a:
        country = st.text_input("Country of birth", placeholder="e.g. India, Mexico, China")
    with col_b:
        uploaded = st.file_uploader("Upload a document (optional — I-20, EAD, visa, etc.)", type=["pdf", "txt"])

    concern = st.text_area(
        "What's your situation?",
        placeholder="Tell us what you're trying to do or what you're worried about. For example: I'm on F-1 OPT expiring in 4 months, trying to get H-1B, lottery results came back negative.",
        height=100
    )

    if st.button("Analyse my situation"):
        doc_context = ""
        if uploaded:
            if uploaded.type == "application/pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(io.BytesIO(uploaded.read()))
                    text = " ".join(p.extract_text() or "" for p in reader.pages)
                    doc_context = f"\n\nFrom the uploaded document:\n{text[:3000]}"
                except Exception:
                    doc_context = f"\nUploaded file: {uploaded.name}"
            else:
                doc_context = f"\n\nDocument text:\n{uploaded.read().decode('utf-8', errors='ignore')[:3000]}"

        with st.spinner("Looking at your situation..."):
            prompt = f"""You are an experienced US immigration advisor. Read this person's situation carefully and give them a clear, honest, direct assessment. Write like you're explaining this to a friend — no jargon, no filler phrases, no hedging beyond what's legally necessary.

Their situation:
- Status: {visa_status}
- Country of birth: {country or "not specified"}
- What they told us: {concern or "no details provided"}
{doc_context}

Return ONLY this JSON:
{{
  "summary": "2-3 sentences that honestly describe where they stand right now",
  "main_issues": [
    {{"issue": "specific issue or risk", "detail": "explain it plainly in 2 sentences", "urgency": "high|medium|low"}}
  ],
  "what_to_do": ["specific action", "specific action", "specific action"],
  "watch_out_for": ["thing 1", "thing 2"],
  "realistic_note": "one honest note about their situation — good or bad, just real",
  "deadlines": "any real deadlines or time-sensitive things they should know about",
  "official_resources": ["Form name or USCIS page title and URL"]
}}

Country of birth matters for priority dates — call it out if India, Mexico, Philippines, or China.
If they asked about H-1B and lost the lottery, give them real alternatives, not generic encouragement."""

            try:
                data = generate(prompt)

                st.markdown(f"""
                <div class="info-box" style="border-left: 3px solid #1d4ed8; background:#f0f7ff;">
                    <div style="font-size:0.75rem; font-weight:600; color:#1d4ed8; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.4rem;">Your situation</div>
                    <p style="margin:0; color:#111827;">{data.get("summary","")}</p>
                </div>
                """, unsafe_allow_html=True)

                if data.get("main_issues"):
                    st.markdown("**What you're dealing with**")
                    for issue in data["main_issues"]:
                        u = issue.get("urgency","low")
                        st.markdown(f"""
                        <div class="info-box">
                            <div class="priority-{u}" style="margin-bottom:0.3rem;">{u} priority</div>
                            <strong>{issue.get("issue","")}</strong>
                            <p style="margin:0.4rem 0 0; font-size:0.9rem;">{issue.get("detail","")}</p>
                        </div>
                        """, unsafe_allow_html=True)

                col_l, col_r = st.columns(2)
                with col_l:
                    if data.get("what_to_do"):
                        st.markdown("**What to do**")
                        for i, action in enumerate(data["what_to_do"], 1):
                            st.markdown(f"""
                            <div class="step-item">
                                <div class="step-num">{i}.</div>
                                <div style="color:#374151; font-size:0.92rem;">{action}</div>
                            </div>
                            """, unsafe_allow_html=True)

                    if data.get("deadlines"):
                        st.markdown("**Deadlines**")
                        st.markdown(f"<div class='flag-box'>{data['deadlines']}</div>", unsafe_allow_html=True)

                with col_r:
                    if data.get("watch_out_for"):
                        st.markdown("**Watch out for**")
                        for w in data["watch_out_for"]:
                            st.markdown(f"<div class='flag-box'>{w}</div>", unsafe_allow_html=True)

                    if data.get("realistic_note"):
                        st.markdown("**A note**")
                        st.markdown(f"<div class='info-box'>{data['realistic_note']}</div>", unsafe_allow_html=True)

                if data.get("official_resources"):
                    st.markdown("**Official resources**")
                    for r in data["official_resources"]:
                        st.markdown(f"- {r}")

            except Exception as e:
                st.error(f"Something went wrong: {e}")


# TAB 3 - GREEN CARD CHECKLIST
with tab3:
    st.markdown("### Green card document checklist")
    st.markdown(
        "<p style='color:#6b7280; font-size:0.9rem;'>"
        "Fill in your details and we'll generate a checklist of every document you need, "
        "based on your specific case. We'll also flag anything that could cause problems."
        "</p>",
        unsafe_allow_html=True
    )

    with st.form("checklist"):
        col1, col2 = st.columns(2)

        with col1:
            relationship = st.selectbox("Petition type", [
                "Spouse of a US Citizen",
                "Spouse of a Green Card holder",
                "Child of a US Citizen (under 21, unmarried)",
                "Child of a Green Card holder",
                "Parent of a US Citizen",
                "Sibling of a US Citizen"
            ])
            location = st.selectbox("Where is the applicant?", [
                "Inside the US (Adjustment of Status, I-485)",
                "Outside the US (Consular Processing)"
            ])
            country = st.text_input("Applicant's country of birth", placeholder="Important for wait times")

        with col2:
            marriage_years = 0.0
            if "Spouse" in relationship:
                marriage_years = st.number_input("Years married", min_value=0.0, max_value=60.0, value=1.0, step=0.5)
            income = st.number_input("Petitioner's annual income (USD)", min_value=0, max_value=1000000, value=55000, step=1000)
            household = st.number_input("Household size (including applicant)", min_value=1, max_value=20, value=2)
            violations = st.checkbox("Prior immigration violations, overstays, or deportation orders")

        notes = st.text_area("Anything we should know", placeholder="Previous visa denials, criminal history, other complicating factors", height=70)

        submitted = st.form_submit_button("Generate checklist")

    if submitted:
        if not country.strip():
            st.error("Country of birth is required — it affects your priority date and waiting time.")
        else:
            with st.spinner("Building your checklist..."):
                prompt = f"""You are a US immigration attorney. Generate a complete, accurate green card application checklist for this case. Be specific and thorough. Do not add generic disclaimers inside the checklist items.

Case:
- Petition type: {relationship}
- Applicant location: {location}
- Country of birth: {country}
- Years married: {marriage_years}
- Petitioner income: ${income:,}/year
- Household size: {household}
- Prior violations: {violations}
- Notes: {notes or "none"}

Return ONLY this JSON:
{{
  "forms": [
    {{"number": "I-130", "name": "Petition for Alien Relative", "fee": "$675", "filed_by": "Petitioner"}}
  ],
  "checklist": [
    {{"category": "Proof of Status", "item": "US passport or naturalization certificate", "why": "Proves petitioner is a US Citizen", "how_to_get": "Apply at travel.state.gov if expired", "required": true}}
  ],
  "red_flags": ["specific issue based on their case"],
  "income_note": "whether they meet the 125% poverty guideline and what to do if not",
  "timeline": "realistic breakdown by phase",
  "cover_letter": "complete cover letter ready to submit, addressed to USCIS, listing all enclosed documents",
  "next_steps": ["step 1", "step 2", "step 3", "step 4"]
}}

Flag conditional green card if married less than 2 years. Flag backlog wait if country is India, Mexico, Philippines, or China. Include both petitioner and applicant documents. Be complete."""

                try:
                    result = generate(prompt)

                    # Red flags first
                    flags = result.get("red_flags", [])
                    if flags:
                        st.markdown("**Things to be aware of in your case**")
                        for f in flags:
                            st.markdown(f"<div class='flag-box'>{f}</div>", unsafe_allow_html=True)
                        st.markdown("")

                    # Forms
                    st.markdown("**Forms to file**")
                    forms_html = " ".join([
                        f"<span class='form-tag'>{f.get('number','')} — {f.get('name','')} ({f.get('fee','')}, filed by {f.get('filed_by','')})</span>"
                        for f in result.get("forms", [])
                    ])
                    st.markdown(forms_html, unsafe_allow_html=True)
                    st.markdown("")

                    # Timeline and income
                    col_t, col_i = st.columns(2)
                    with col_t:
                        st.markdown("**Timeline**")
                        st.markdown(f"<div class='info-box'>{result.get('timeline','')}</div>", unsafe_allow_html=True)
                    with col_i:
                        st.markdown("**Income requirement**")
                        st.markdown(f"<div class='info-box'>{result.get('income_note','')}</div>", unsafe_allow_html=True)

                    st.markdown("")

                    # Checklist grouped by category
                    st.markdown("**Document checklist**")
                    st.markdown(
                        "<p style='color:#6b7280; font-size:0.85rem; margin-bottom:1rem;'>"
                        "Required items are marked. The rest are strongly recommended — USCIS often asks for them even if not strictly required."
                        "</p>",
                        unsafe_allow_html=True
                    )

                    categories = {}
                    for item in result.get("checklist", []):
                        cat = item.get("category", "Other")
                        categories.setdefault(cat, []).append(item)

                    for cat, items in categories.items():
                        with st.expander(f"{cat} ({len(items)} items)", expanded=True):
                            for item in items:
                                req = item.get("required", False)
                                label = "Required — " if req else ""
                                st.markdown(f"**{label}{item.get('item','')}**")
                                st.markdown(
                                    f"<span style='color:#4b5563; font-size:0.88rem;'>{item.get('why','')}</span><br>"
                                    f"<span style='color:#9ca3af; font-size:0.85rem;'>How to get it: {item.get('how_to_get','')}</span>",
                                    unsafe_allow_html=True
                                )
                                st.markdown("")

                    # Cover letter
                    st.markdown("**Cover letter**")
                    st.markdown(
                        "<p style='color:#6b7280; font-size:0.85rem;'>"
                        "Place this as the first page of your package. Add your address at the top."
                        "</p>",
                        unsafe_allow_html=True
                    )
                    st.text_area("", value=result.get("cover_letter", ""), height=320, label_visibility="collapsed")

                    # Next steps
                    st.markdown("**Next steps**")
                    for i, step in enumerate(result.get("next_steps", []), 1):
                        st.markdown(f"""
                        <div class="step-item">
                            <div class="step-num">{i}.</div>
                            <div style="font-size:0.92rem; color:#374151;">{step}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("")
                    st.markdown(
                        "<p style='color:#9ca3af; font-size:0.82rem;'>"
                        "This checklist is based on current USCIS guidelines but is not legal advice. "
                        "If your case has complications — prior deportations, criminal history, long overstays — consult an attorney."
                        "</p>",
                        unsafe_allow_html=True
                    )

                except Exception as e:
                    st.error(f"Something went wrong: {e}")


# TAB 4 - ABOUT
with tab4:
    st.markdown("### About this tool")

    st.markdown("""
    Immigration Co-Pilot is a free tool built to make US immigration information more accessible.

    Most people going through a green card or visa process can't afford an attorney — or don't know
    if they even need one. The goal here is to give you a clear starting point: what forms you need,
    what documents to gather, and what's actually happening in immigration policy right now.
    """)

    st.markdown("**Where the information comes from**")
    st.markdown("""
    - The news tab pulls directly from the [USCIS newsroom RSS feed](https://www.uscis.gov/rss/uscis-news.xml)
      and the [Federal Register API](https://www.federalregister.gov). We refresh it every 48 hours
      so we're not hammering government servers. The plain-English explanations are generated by AI
      based on the real headlines.
    - The green card checklist is built from USCIS form instructions and the Federal Poverty Guidelines.
      The AI generates it based on your specific case details.
    - Processing times change frequently. Always check [egov.uscis.gov/processing-times](https://egov.uscis.gov/processing-times/) directly.
    """)

    st.markdown("**What this is not**")
    st.markdown("""
    This is not a law firm. It doesn't give legal advice. It doesn't create an attorney-client relationship.
    If your case is complicated — prior violations, criminal history, multiple entries and exits, prior denials —
    you should talk to a licensed immigration attorney.
    """)

    st.markdown("**Privacy**")
    st.markdown("""
    Documents you upload are processed in memory and discarded when your session ends.
    We don't store personal information, document contents, or anything you enter into the forms.
    """)

    st.markdown("**Built with Gemini by Google**")
    st.markdown("""
    The AI parts of this tool are powered by Google's Gemini model. The tool was built as part of
    the Build with Gemini XPRIZE hackathon.
    """)

    st.markdown("---")
    st.markdown(
        "<p style='color:#9ca3af; font-size:0.82rem;'>Found a bug or have feedback? The tool is open source at "
        "<a href='https://github.com/sainakakkar2006/immigration-copilot'>github.com/sainakakkar2006/immigration-copilot</a></p>",
        unsafe_allow_html=True
    )
