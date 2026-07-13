import streamlit as st
from google import genai
from google.genai import types
import json
import os
import re
import requests
from datetime import datetime, date, timedelta

MODEL = "gemini-2.5-flash"

st.set_page_config(
    page_title="Immigration Co-Pilot",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------------------------
# Languages — the most common languages spoken by US immigrant communities
# ---------------------------------------------------------------------------
LANGUAGES = {
    "English": "English",
    "Español": "Spanish",
    "中文": "Simplified Chinese",
    "हिन्दी": "Hindi",
    "Tagalog": "Tagalog",
    "Tiếng Việt": "Vietnamese",
    "한국어": "Korean",
    "Português": "Portuguese",
    "العربية": "Arabic",
    "Kreyòl Ayisyen": "Haitian Creole",
    "Русский": "Russian",
    "Français": "French",
}

# English base copy for the interface. Other languages are translated by
# Gemini once per language and cached for everyone.
T_EN = {
    "tagline": "Plain answers about US immigration. We read the letters, track the deadlines, and tell you what to do next, in your language. Built for families doing this without a lawyer.",
    "not_legal_advice": "This is a free information tool, not legal advice. If your case is complicated, talk to a licensed attorney. Free and low-cost help exists at immigrationlawhelp.org.",
    "tab_decode": "Decode a Letter",
    "tab_news": "News",
    "tab_situation": "Your Situation",
    "tab_opt": "OPT Deadlines",
    "tab_checklist": "Green Card Checklist",
    "tab_about": "About",
    "news_heading": "What's happening in US immigration",
    "news_filter_label": "Show news about",
    "news_loading": "Fetching the latest immigration news...",
    "news_none": "No new headlines for this topic right now. The essentials below still apply.",
    "news_latest_heading": "Latest news",
    "news_essentials_heading": "The essentials for this topic",
    "essentials_reviewed": "These don't change with the news. Checked against USCIS.gov, last reviewed July 2026.",
    "essential_tag": "always applies",
    "footer_made": "Made by Saina and Arsh, two students whose families have been through this system.",
    "footer_sources": "Everything is checked against USCIS.gov and the Federal Register. This is not a law firm.",
    "footer_feedback": "Spotted a mistake? Tell us on GitHub and we'll fix it.",
    "news_fr_heading": "Recent regulatory activity — Federal Register",
    "news_fr_unavailable": "Federal Register data unavailable right now.",
    "priority": "priority",
    "situation_heading": "How does the current situation affect you?",
    "situation_intro": "Describe your visa status and what you're planning to do. You can also upload a document — even a phone photo — and we'll read your specific details from it.",
    "situation_status_label": "Your current status",
    "situation_country_label": "Country of birth",
    "situation_country_ph": "e.g. India, Mexico, China",
    "situation_upload_label": "Upload a document (optional: I-20, EAD, visa, or a phone photo of one)",
    "situation_concern_label": "What's your situation?",
    "situation_concern_ph": "Tell us what you're trying to do or what you're worried about. For example: I'm on F-1 OPT expiring in 4 months, trying to get H-1B, lottery results came back negative.",
    "situation_button": "Analyse my situation",
    "situation_spinner": "Looking at your situation...",
    "situation_your_situation": "Your situation",
    "situation_from_doc": "What we found in your document",
    "situation_dealing": "What you're dealing with",
    "situation_what_to_do": "What to do",
    "situation_deadlines": "Deadlines",
    "situation_watch_out": "Watch out for",
    "situation_note": "A note",
    "situation_resources": "Official resources",
    "decode_heading": "Got a letter from immigration? We'll explain it.",
    "decode_intro": "Take a photo of any letter from USCIS, ICE, or the State Department, or upload the PDF. We'll tell you what it is, what it means, and exactly what to do before the deadline. Nothing you upload is stored.",
    "decode_upload_label": "Photo or PDF of your letter",
    "decode_button": "Explain this letter",
    "decode_spinner": "Reading your letter...",
    "decode_what_is": "What this letter is",
    "decode_means": "What it means for you",
    "decode_deadlines": "Your deadlines",
    "decode_days_left": "days left",
    "decode_passed": "passed",
    "decode_actions": "What to do now",
    "decode_details": "Details found in your letter",
    "decode_download_ics": "Add these deadlines to my calendar (.ics)",
    "decode_get_help": "This looks serious. Find free legal help near you at immigrationlawhelp.org. Many nonprofits handle exactly this kind of notice at no cost.",
    "decode_no_file": "Upload a photo or PDF of your letter first.",
    "opt_heading": "OPT and STEM OPT deadline calculator",
    "opt_intro": "These dates are computed directly from USCIS rules. Nothing here is estimated by AI. Enter your dates and get every deadline that applies to you, plus a calendar file so you never miss one.",
    "opt_stage_label": "Where are you now?",
    "opt_stage_student": "I'm finishing my F-1 program",
    "opt_stage_opt": "I'm on OPT and thinking about the STEM extension",
    "opt_program_end": "Program end date (on your I-20)",
    "opt_end_date": "OPT end date (on your EAD card)",
    "opt_stem_eligible": "My degree is on the STEM Designated Degree Program List",
    "opt_button": "Calculate my deadlines",
    "opt_timeline": "Your timeline",
    "opt_download_ics": "Add these deadlines to my calendar (.ics)",
    "opt_explain_spinner": "Writing your plain-language explanation...",
    "checklist_heading": "Green card document checklist",
    "checklist_intro": "Fill in your details and we'll generate a checklist of every document you need, based on your specific case. We'll also flag anything that could cause problems.",
    "checklist_petition_label": "Petition type",
    "checklist_location_label": "Where is the applicant?",
    "checklist_country_label": "Applicant's country of birth",
    "checklist_country_ph": "Important for wait times",
    "checklist_married_label": "Years married",
    "checklist_income_label": "Petitioner's annual income (USD)",
    "checklist_household_label": "Household size (including applicant)",
    "checklist_violations_label": "Prior immigration violations, overstays, or deportation orders",
    "checklist_notes_label": "Anything we should know",
    "checklist_notes_ph": "Previous visa denials, criminal history, other complicating factors",
    "checklist_button": "Generate checklist",
    "checklist_country_required": "Country of birth is required — it affects your priority date and waiting time.",
    "checklist_spinner": "Building your checklist...",
    "checklist_aware": "Things to be aware of in your case",
    "checklist_forms": "Forms to file",
    "checklist_timeline": "Timeline",
    "checklist_income": "Income requirement",
    "checklist_documents": "Document checklist",
    "checklist_required_note": "Required items are marked. The rest are strongly recommended. USCIS often asks for them even when they're not strictly required.",
    "checklist_cover": "Cover letter",
    "checklist_cover_note": "Place this as the first page of your package. Add your address at the top.",
    "checklist_cover_label": "Your cover letter",
    "checklist_next": "Next steps",
    "checklist_download": "Download my checklist",
    "checklist_disclaimer": "This checklist is based on current USCIS guidelines but is not legal advice. If your case has complications — prior deportations, criminal history, long overstays — consult an attorney.",
    "settings_language": "Language",
    "settings_text_size": "Text size",
    "text_normal": "Normal",
    "text_large": "Large",
    "text_xl": "Extra large",
    "error_generic": "Something went wrong. Please try again in a moment.",
    "required": "Required",
    "how_to_get": "How to get it",
    "filed_by": "filed by",
}

# ---------------------------------------------------------------------------
# Settings row — language and text size (rendered before everything else)
# ---------------------------------------------------------------------------
set_l, set_m, set_r = st.columns([2, 2, 3])
with set_l:
    ui_lang = st.selectbox("Language / Idioma / 语言", list(LANGUAGES.keys()), key="ui_lang")
with set_m:
    text_size = st.selectbox("Text size", ["Normal", "Large", "Extra large"], key="text_size")

BASE_FONT = {"Normal": 16, "Large": 18, "Extra large": 21}[text_size]
LANG = LANGUAGES[ui_lang]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

:root {{
    --ink: #1a202c;
    --body-text: #374151;
    --muted: #57606a;
    --line: #e4e2de;
    --paper: #faf9f7;
    --card: #ffffff;
    --brand: #1d4ed8;
    --brand-dark: #1e40af;
    --brand-tint: #eff6ff;
}}

html {{ font-size: {BASE_FONT}px; }}

html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}}

.stApp {{ background: var(--paper); }}

.block-container {{
    padding: 2rem 2rem 6rem;
    max-width: 880px;
}}
@media (max-width: 640px) {{
    .block-container {{ padding: 1.2rem 1rem 4rem; }}
}}

h1, h2, h3,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {{
    font-family: 'Fraunces', Georgia, 'Times New Roman', serif !important;
    color: var(--ink);
    letter-spacing: -0.012em;
    line-height: 1.22;
    font-weight: 600;
}}
h3, .stMarkdown h3, [data-testid="stMarkdownContainer"] h3 {{
    font-size: clamp(1.35rem, 1.05rem + 1.1vw, 1.65rem);
    padding-top: 0.4rem;
}}
p {{ color: var(--body-text); line-height: 1.65; max-width: 70ch; }}
li {{ line-height: 1.65; }}

*:focus-visible {{
    outline: 3px solid var(--brand) !important;
    outline-offset: 2px;
    border-radius: 4px;
}}
@media (prefers-reduced-motion: reduce) {{
    * {{ animation: none !important; transition: none !important; }}
}}

.site-header {{
    border-bottom: 1px solid var(--line);
    padding-bottom: 1.6rem;
    margin-bottom: 1.4rem;
}}
.site-title {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: clamp(1.8rem, 1.4rem + 1.6vw, 2.3rem);
    font-weight: 700;
    letter-spacing: -0.015em;
    color: var(--ink);
    margin: 0;
}}
.site-title::after {{
    content: "";
    display: block;
    width: 3.5rem;
    height: 4px;
    border-radius: 2px;
    background: var(--brand);
    margin-top: 0.6rem;
}}
.site-desc {{
    color: var(--muted);
    font-size: 1rem;
    line-height: 1.6;
    margin-top: 0.7rem;
    max-width: 62ch;
}}
.advice-note {{
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 0.7rem 1.1rem;
    font-size: 0.85rem;
    line-height: 1.55;
    color: var(--muted);
    margin-bottom: 1.4rem;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}}

/* Tabs: bigger targets, clear active state */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0.15rem;
    border-bottom: 1px solid var(--line);
}}
.stTabs [data-baseweb="tab"] {{
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--muted);
    padding: 0.7rem 0.95rem;
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: var(--ink);
    font-weight: 600;
}}

/* News as cards */
.news-item {{
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
    margin: 0 0 0.8rem;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    transition: box-shadow 0.15s ease, border-color 0.15s ease;
}}
.news-item:hover {{
    border-color: #c9d2e8;
    box-shadow: 0 3px 10px rgba(16, 24, 40, 0.07);
}}
.news-title {{
    font-size: 1.02rem;
    font-weight: 600;
    line-height: 1.45;
    color: var(--ink);
    margin: 0 0 0.3rem;
}}
.news-title a {{ text-decoration: none; }}
.news-title a:hover {{ text-decoration: underline; text-underline-offset: 3px; }}
.news-meta {{
    font-size: 0.8rem;
    color: var(--muted);
    margin-bottom: 0.5rem;
}}
.news-context {{
    color: var(--body-text);
    font-size: 0.92rem;
    margin: 0.4rem 0 0;
    line-height: 1.6;
}}

/* Priority pills — sentence case reads calmer than shouting caps */
.priority-high, .priority-medium, .priority-low {{
    display: inline-block;
    padding: 0.12rem 0.55rem;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 600;
    vertical-align: 1px;
}}
.priority-high {{ background: #fef2f2; color: #b91c1c; }}
.priority-medium {{ background: #fffbeb; color: #b45309; }}
.priority-low {{ background: #ecfdf5; color: #047857; }}
.pill-essential {{
    display: inline-block;
    padding: 0.12rem 0.55rem;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 600;
    background: var(--brand-tint);
    color: var(--brand);
    vertical-align: 1px;
}}
/* Essentials read as an editorial list, not another wall of cards */
.plain-item {{
    padding: 0.95rem 0;
    border-bottom: 1px solid var(--line);
}}
.site-footer {{
    margin-top: 3.5rem;
    padding-top: 1.3rem;
    border-top: 1px solid var(--line);
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.75;
}}

.section-label {{
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.8rem;
}}
.info-box {{
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    line-height: 1.6;
}}
.flag-box {{
    background: #fffaf0;
    border: 1px solid #fde8c3;
    border-left: 3px solid #f59e0b;
    padding: 0.8rem 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--body-text);
}}
.form-tag {{
    display: inline-block;
    background: var(--brand-tint);
    color: var(--brand);
    padding: 0.35rem 0.8rem;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.85rem;
    margin: 0.2rem;
}}
.step-item {{
    display: flex;
    gap: 0.9rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--line);
    align-items: flex-start;
}}
.step-item:last-child {{ border-bottom: none; }}
.step-num {{
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--brand);
    background: var(--brand-tint);
    border-radius: 999px;
    width: 1.5rem;
    height: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}}
.deadline-row {{
    display: flex;
    gap: 1rem;
    padding: 0.85rem 1rem;
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 10px;
    margin-bottom: 0.6rem;
    align-items: flex-start;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}}
.deadline-date {{
    font-weight: 700;
    color: var(--ink);
    flex-shrink: 0;
    width: 140px;
    font-size: 0.92rem;
    line-height: 1.4;
}}
.deadline-what {{
    color: var(--body-text);
    font-size: 0.92rem;
    line-height: 1.6;
}}
.deadline-past {{ opacity: 0.5; }}

/* Buttons: filled primary CTAs, quiet secondary */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    border-radius: 8px;
    font-weight: 600;
    padding: 0.55rem 1.5rem;
    font-size: 0.93rem;
    border: 1.5px solid #d0d7de;
    background: var(--card);
    color: var(--ink);
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
    border-color: var(--brand);
    color: var(--brand);
    background: var(--card);
}}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
    background: var(--brand) !important;
    color: #ffffff !important;
    border: 1.5px solid var(--brand) !important;
}}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {{
    background: var(--brand-dark) !important;
    border-color: var(--brand-dark) !important;
    color: #ffffff !important;
}}

/* Inputs: white on paper, comfortable */
[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input {{
    background: var(--card);
    border-radius: 8px;
}}
.stExpander {{
    background: var(--card);
    border-radius: 10px;
}}

a {{ color: var(--brand); text-underline-offset: 3px; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    api_key = ""
api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    st.error("GEMINI_API_KEY not found. Add it to Streamlit secrets.")
    st.stop()

# 30s timeout so one slow API call can never hang the whole page
client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30_000))


def _parse_json(text):
    """Parse JSON out of a model response, tolerating markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"[\[{].*[\]}]", text, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def generate(contents):
    """JSON-mode generation. `contents` may be a string or list of parts."""
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    return _parse_json(response.text)


def generate_grounded(prompt):
    """Generation with live Google Search grounding. Returns parsed JSON or None."""
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
        )
        return _parse_json(response.text)
    except Exception:
        return None


def lang_rule(lang):
    if lang == "English":
        return ""
    return f"\n\nIMPORTANT: Write every user-facing text value in {lang}. Keep form numbers (I-130, I-485), agency names (USCIS, DHS), URLs, and JSON keys exactly as they are."


# ---------------------------------------------------------------------------
# Interface translation — one Gemini call per language, cached for everyone
# ---------------------------------------------------------------------------
@st.cache_data(ttl=None, show_spinner=False)
def translate_ui(lang):
    if lang == "English":
        return T_EN
    try:
        prompt = f"""Translate the VALUES of this JSON object into {lang} for a US immigration help website used by immigrant families.
Rules:
- Plain, warm, everyday language a non-lawyer understands. Match the tone of the English.
- Keep immigration terms people see on official documents in English with a translation in parentheses where helpful: OPT, STEM OPT, EAD, I-20, SEVIS, Green Card, USCIS, H-1B, F-1.
- Keep URLs, form numbers, and the string "immigrationlawhelp.org" unchanged.
- Return ONLY the JSON object with the same keys.

{json.dumps(T_EN, ensure_ascii=False)}"""
        result = generate(prompt)
        # Every key must survive translation; fill any gaps from English
        return {k: result.get(k) or v for k, v in T_EN.items()}
    except Exception:
        return T_EN


if LANG != "English":
    with st.spinner("Translating..."):
        T = translate_ui(LANG)
else:
    T = T_EN

# ---------------------------------------------------------------------------
# News data sources
# ---------------------------------------------------------------------------
def fetch_uscis_news():
    """Read the news JSON saved by the GitHub Action every 2 days."""
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


@st.cache_data(ttl=172800)
def fetch_federal_register():
    try:
        url = "https://www.federalregister.gov/api/v1/documents.json"
        params = {
            "per_page": 5,
            "order": "newest",
            "conditions[agencies][]": ["u-s-citizenship-and-immigration-services", "executive-office-for-immigration-review"],
            "conditions[type][]": ["RULE", "PRORULE", "NOTICE"]
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


TOPIC_FOCUS = {
    "H-1B": """Focus ONLY on H-1B visa topics: cap registration, lottery results, petition rules, RFE trends, employer sponsorship, H-1B to green card (EB-2/EB-3) pathways, and H-4 EAD. Do not include asylum, F-1, family green cards, or unrelated immigration topics.""",
    "F-1 / Students": """Focus ONLY on F-1 student visa topics: OPT, STEM OPT, cap-gap, SEVIS, university enrollment rules, and CPT. Do not include H-1B, green cards, asylum, or unrelated topics.""",
    "Family Green Cards": """Focus ONLY on family-based green card topics: I-130 petitions, priority dates for family categories, adjustment of status (I-485), consular processing, spousal visas, and immediate relative categories. Do not include employment visas, asylum, or unrelated topics.""",
    "Employment Green Cards": """Focus ONLY on employment-based green card topics: EB-1, EB-2, EB-3, PERM labor certification, priority date movement, national interest waivers, and I-140 petitions. Do not include family green cards, work visas, or unrelated topics.""",
}


@st.cache_data(ttl=172800, show_spinner=False)
def enrich_news(news_items_json, topic_filter, lang):
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
        specific = [i for i in items if any(k in (i.get("title", "") + i.get("summary", "")).lower() for k in keywords)]
        if not specific:
            # Nothing in the file matches this topic — let the live-search
            # fallback supply topic-specific news instead of showing
            # the same unrelated items for every topic.
            return []
        filtered = specific

    topic_instruction = ""
    if topic_filter != "All":
        topic_instruction = f'\n\nSTRICT TOPIC FILTER: the user selected "{topic_filter}". Only include items genuinely relevant to that topic ({TOPIC_FOCUS.get(topic_filter, "")}). Skip every item that is not about this topic, even if it is important general immigration news. If no items qualify, return an empty JSON array.'

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
- "title": headline (translate it if writing in another language)
- "link": same link as input
- "published": same published date as input
- "source": same source as input (e.g. "USCIS", "DHS", "White House")
- "plain_summary": 2 plain sentences — what happened and who it affects
- "priority": "high" | "medium" | "low"
- "affects": specific group (e.g. "H-1B holders", "all visa applicants", "asylum seekers")
{lang_rule(lang)}"""
    return generate(prompt)


@st.cache_data(ttl=21600, show_spinner=False)
def grounded_news(topic, lang):
    """Live news via Gemini + Google Search grounding. Returns list or None."""
    focus = TOPIC_FOCUS.get(topic, "Cover H-1B, family green cards, employment green cards, F-1/OPT, asylum policy, and general USCIS processing updates.") if topic != "All" else \
        "Cover H-1B, family green cards, employment green cards, F-1/OPT, asylum policy, and general USCIS processing updates."

    today = date.today().strftime("%B %d, %Y")
    prompt = f"""Search the web for the most important US immigration news and policy changes from the last 30 days (today is {today}).

{focus}

Rules:
- Only include real, verifiable news you found through search. Prefer official sources: uscis.gov, dhs.gov, state.gov, federalregister.gov, whitehouse.gov.
- Most items should be "medium" priority. Only use "high" if action is genuinely needed now.
- Write in plain English, two sentences per item. No hype.
{lang_rule(lang)}

Return ONLY a JSON array of 5-7 items, no other text. Each object:
- "title": clear, factual headline
- "link": source URL you found
- "published": date or period from the source
- "plain_summary": 2 plain sentences — what it is and who it affects
- "priority": "high" | "medium" | "low"
- "affects": specific group (e.g. "H-1B cap registrants", "F-1 OPT applicants")
- "source": agency or publication name"""
    result = generate_grounded(prompt)
    if isinstance(result, list) and result:
        return result
    return None


@st.cache_data(ttl=172800, show_spinner=False)
def knowledge_fallback(topic, lang):
    """Last resort: Gemini training knowledge, no invented dates."""
    if topic != "All":
        focus = TOPIC_FOCUS.get(topic, f"Focus specifically on {topic}.")
    else:
        focus = "Cover H-1B, family green cards, employment green cards, F-1/OPT, asylum policy, and general USCIS processing updates."

    prompt = f"""You are an immigration expert. Someone just opened an immigration tool and needs to know what's important right now.

{focus}

List the most important things they should know that are still relevant and actionable today.

Rules:
- Only include things that are factually accurate and still relevant to this specific topic
- Do NOT include topics outside the focus area above
- Do NOT invent specific dates — use "recent", "ongoing", or a year
- Most items should be "medium" priority. Only use "high" if action is genuinely needed now.
- Write in plain English, two sentences per item. No hype.
{lang_rule(lang)}

Return a JSON array of 5-7 items. Each object:
- "title": clear, factual headline
- "link": best official URL (uscis.gov, whitehouse.gov, dhs.gov, state.gov, federalregister.gov)
- "published": time period ("recent", "ongoing")
- "plain_summary": 2 plain sentences — what it is and who it affects
- "priority": "high" | "medium" | "low"
- "affects": specific group (e.g. "H-1B cap registrants", "F-1 OPT applicants")
- "source": agency (e.g. "USCIS", "White House", "DHS")"""
    return generate(prompt)


# ---------------------------------------------------------------------------
# Evergreen essentials — curated in code so every topic always has content.
# These are stable rules from statute/regulation, not news; the AI never
# generates them, only translates them.
# ---------------------------------------------------------------------------
ESSENTIALS = {
    "All": [
        {"title": "Never miss a deadline on a USCIS notice",
         "summary": "Deadlines on Requests for Evidence and other notices are strict. Missing one usually means a denial. Read every letter the day it arrives and calendar the response date immediately.",
         "link": "https://www.uscis.gov/forms/filing-guidance/responding-to-a-request-for-evidence-or-notice-of-intent-to-deny"},
        {"title": "Report your address within 10 days of moving",
         "summary": "Almost everyone who is not a US citizen must file Form AR-11 within 10 days of changing address. It takes 5 minutes online and protects you from missing mail about your case.",
         "link": "https://www.uscis.gov/ar-11"},
        {"title": "Check your case status and processing times yourself",
         "summary": "You can track any receipt number free at the official USCIS case status page, and see how long your form type is taking at your service center. No one can speed this up for a fee.",
         "link": "https://egov.uscis.gov/casestatus/landing.do"},
        {"title": "Beware of notario fraud",
         "summary": "Only licensed attorneys and DOJ-accredited representatives can give immigration legal advice. A 'notario' or consultant who promises results is a red flag. Free or low-cost real help exists.",
         "link": "https://www.uscis.gov/scams-fraud-and-misconduct/avoid-scams"},
        {"title": "Keep copies of everything",
         "summary": "Photocopy or scan every page you send to the government and use tracked mail. Your own complete file is often the only record you can rely on later.",
         "link": "https://www.uscis.gov/forms/filing-guidance"},
    ],
    "H-1B": [
        {"title": "The H-1B lottery registration happens every March",
         "summary": "Your employer registers you electronically in early March for a job starting October 1. If you miss the window, you wait a full year, so talk to your employer well before spring.",
         "link": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations"},
        {"title": "You have a 60-day grace period if you lose your job",
         "summary": "After a layoff you get up to 60 days (or until your I-94 expires, whichever is shorter) to find a new sponsor, change status, or leave. A new employer can file a transfer petition during this window.",
         "link": "https://www.uscis.gov/working-in-the-united-states/information-for-employers-and-employees/options-for-nonimmigrant-workers-following-termination-of-employment"},
        {"title": "H-1B lets you pursue a green card",
         "summary": "Unlike many visas, being on H-1B while applying for permanent residence is fully allowed. Ask your employer about starting the PERM process early, because backlogs are long for some countries.",
         "link": "https://www.uscis.gov/working-in-the-united-states/permanent-workers"},
        {"title": "Your H-4 spouse may be able to work",
         "summary": "If your I-140 immigrant petition is approved, your spouse can apply for an H-4 work permit (EAD). Many families miss this benefit entirely.",
         "link": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-4-spouses"},
    ],
    "F-1 / Students": [
        {"title": "Apply for OPT in the 90-day window before your program ends",
         "summary": "USCIS can receive your OPT application up to 90 days before your program end date and no later than 60 days after. Applying early matters. Approvals take months and you cannot work until approved.",
         "link": "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students"},
        {"title": "Watch your unemployment days on OPT",
         "summary": "You get a maximum of 90 days without a job on regular OPT, and 150 total if you extend with STEM OPT. Going over can end your status, so report every job to your school's international office.",
         "link": "https://studyinthestates.dhs.gov/sevis-help-hub/student-records/fm-student-employment/f-1-optional-practical-training-opt"},
        {"title": "Keep your SEVIS record accurate",
         "summary": "Report address and employer changes to your Designated School Official within 10 days. A clean SEVIS record is what keeps your status alive. Most preventable problems start here.",
         "link": "https://studyinthestates.dhs.gov/"},
        {"title": "On-campus work is capped at 20 hours a week during term",
         "summary": "Working more than 20 hours a week on campus during the semester is a status violation, even if your employer schedules it. Full time is allowed during official breaks.",
         "link": "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/students-and-employment"},
        {"title": "Cap-gap protects you between OPT and H-1B",
         "summary": "If your employer files an H-1B petition while your OPT is valid and you're selected, your status and work authorization automatically extend until the H-1B starts October 1.",
         "link": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations/extension-of-post-completion-optional-practical-training-opt-and-f-1-status-for-eligible-students"},
    ],
    "Family Green Cards": [
        {"title": "Immediate relatives of US citizens have no waiting line",
         "summary": "Spouses, parents, and unmarried children under 21 of US citizens are never subject to annual limits. The only wait is processing time. All other family categories wait for a priority date.",
         "link": "https://www.uscis.gov/family/family-of-us-citizens"},
        {"title": "Check the Visa Bulletin every month if you're in a preference category",
         "summary": "The State Department publishes wait-line movement monthly. Your place in line is your priority date, which is the date the I-130 was filed. Nothing moves your case until that date is current.",
         "link": "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html"},
        {"title": "The sponsor must earn 125% of the poverty guideline",
         "summary": "Whoever files the I-864 Affidavit of Support must show income at 125% of the federal poverty level for their household size. If they fall short, a joint sponsor can sign too.",
         "link": "https://www.uscis.gov/i-864p"},
        {"title": "Married under 2 years? Your green card will be conditional",
         "summary": "You'll get a 2-year conditional card and must file Form I-751 in the 90 days before it expires to get the permanent one. Missing that window is one of the most common and serious mistakes.",
         "link": "https://www.uscis.gov/green-card/after-we-grant-your-green-card/conditional-permanent-residence"},
        {"title": "Don't travel abroad with a pending I-485 unless you have advance parole",
         "summary": "Leaving the US while your adjustment of status is pending, without an approved travel document, usually means your application is considered abandoned.",
         "link": "https://www.uscis.gov/i-131"},
    ],
    "Employment Green Cards": [
        {"title": "Your priority date is your place in line — check it monthly",
         "summary": "The date your PERM or I-140 was filed is your priority date. Compare it against the monthly Visa Bulletin to know when you can file the final step.",
         "link": "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html"},
        {"title": "India and China face the longest EB-2/EB-3 backlogs",
         "summary": "If you were born in India or China, expect multi-year waits in the main employment categories. Where you were born controls the line, not your citizenship or where you live.",
         "link": "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html"},
        {"title": "After I-140 approval plus 180 days, you can change jobs",
         "summary": "Once your I-485 has been pending 180 days with an approved I-140, you can move to a same-or-similar job with a new employer without restarting the green card process.",
         "link": "https://www.uscis.gov/working-in-the-united-states/permanent-workers"},
        {"title": "EB-1 and National Interest Waiver skip the PERM step",
         "summary": "Extraordinary-ability, outstanding-researcher, and NIW cases don't need labor certification, which can cut a year or more off the process. Worth assessing if you have a strong research or achievement record.",
         "link": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-first-preference-eb-1"},
    ],
}


@st.cache_data(ttl=None, show_spinner=False)
def translated_essentials(topic, lang):
    items = ESSENTIALS.get(topic, [])
    if lang == "English" or not items:
        return items
    try:
        prompt = f"""Translate the "title" and "summary" values of each item into {lang} for a US immigration help site. Plain, warm, everyday language. Keep form numbers (I-751, AR-11), program names (OPT, STEM OPT, PERM, SEVIS, H-1B, EB-2), and "link" values exactly unchanged.

Return ONLY the JSON array with the same structure.

{json.dumps(items, ensure_ascii=False)}"""
        result = generate(prompt)
        if isinstance(result, list) and len(result) == len(items):
            # Never let translation drop or alter the official links
            for translated, original in zip(result, items):
                translated["link"] = original["link"]
            return result
    except Exception:
        pass
    return items


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(f"""
<div class="site-header">
    <div class="site-title">Immigration Co-Pilot</div>
    <div class="site-desc">{T["tagline"]}</div>
</div>
<div class="advice-note">{T["not_legal_advice"].replace("immigrationlawhelp.org", "<a href='https://www.immigrationlawhelp.org' target='_blank'>immigrationlawhelp.org</a>")}</div>
""", unsafe_allow_html=True)

tab_decode, tab1, tab2, tab_opt, tab3, tab4 = st.tabs([
    T["tab_decode"], T["tab_news"], T["tab_situation"], T["tab_opt"], T["tab_checklist"], T["tab_about"]
])


# ---------------------------------------------------------------------------
# TAB — DECODE A LETTER (flagship: photo of a USCIS notice → plain answer)
# ---------------------------------------------------------------------------
def parse_iso_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def decode_deadlines_to_ics(key_dates):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Immigration Co-Pilot//Letter Deadlines//EN",
    ]
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for i, d in enumerate(key_dates):
        day_obj = parse_iso_date(d.get("date", ""))
        if not day_obj:
            continue
        day = day_obj.strftime("%Y%m%d")
        what = d.get("what", "Immigration deadline")
        lines += [
            "BEGIN:VEVENT",
            f"UID:letter-{i}-{day}@immigration-copilot",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{day}",
            f"SUMMARY:Immigration deadline: {what[:70]}",
            f"DESCRIPTION:{what}",
            "BEGIN:VALARM",
            "TRIGGER:-P14D",
            "ACTION:DISPLAY",
            "DESCRIPTION:Immigration deadline in 2 weeks",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


with tab_decode:
    st.markdown(f"### {T['decode_heading']}")
    st.markdown(f"<p style='color:#4b5563; font-size:0.9rem;'>{T['decode_intro']}</p>", unsafe_allow_html=True)

    letter = st.file_uploader(
        T["decode_upload_label"],
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        key="letter_upload",
    )

    if st.button(T["decode_button"], type="primary"):
        if not letter:
            st.warning(T["decode_no_file"])
        else:
            with st.spinner(T["decode_spinner"]):
                today = date.today().isoformat()
                prompt = f"""You are helping someone who just received a letter from a US government immigration agency and is scared and confused. The letter is attached (it may be a photo taken with a phone — read it carefully even if tilted or blurry).

Today's date is {today}.

Identify what this letter is and explain it at a 5th-grade reading level. Common types: Receipt Notice (I-797C), Request for Evidence (RFE), Notice of Intent to Deny (NOID), Approval Notice, Denial, Notice to Appear (NTA), biometrics appointment, interview notice.

Return ONLY this JSON:
{{
  "doc_type": "what kind of letter this is, in plain words (e.g. 'Request for Evidence — USCIS is asking you for more proof')",
  "agency": "who sent it (USCIS, ICE, EOIR, State Department)",
  "urgency": "high|medium|low",
  "what_it_means": "3-4 plain sentences: what happened, what the government wants, and what happens if you do nothing. Be honest but calm.",
  "details": [{{"field": "e.g. Receipt number, Form type, Case type, Office", "value": "exact value from the letter"}}],
  "key_dates": [{{"date": "YYYY-MM-DD", "what": "what must happen by this date, in plain words"}}],
  "actions": ["specific step 1", "specific step 2", "specific step 3"],
  "needs_lawyer": true or false — true if this is a denial, NOID, NTA, court notice, or anything involving deportation or serious consequences
}}

Rules:
- Only report dates and values actually printed in the letter. Never invent them. If no dates are visible, return an empty key_dates list.
- Convert any date you find to YYYY-MM-DD format.
- If the image is unreadable, set doc_type to "Could not read this document" and explain what to try in what_it_means (better lighting, flat surface, all corners visible).{lang_rule(LANG)}"""

                try:
                    file_bytes = letter.read()
                    mime = letter.type or "application/pdf"
                    st.session_state["decode_result"] = generate([
                        types.Part.from_bytes(data=file_bytes, mime_type=mime),
                        prompt,
                    ])
                except Exception:
                    st.session_state["decode_result"] = None
                    st.error(T["error_generic"])

    decoded = st.session_state.get("decode_result")
    if decoded:
        u = decoded.get("urgency", "medium")
        st.markdown(f"""
        <div class="info-box" style="border-left: 3px solid #1d4ed8; background:#f0f7ff;">
            <div style="font-size:0.75rem; font-weight:600; color:#1d4ed8; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.4rem;">{T["decode_what_is"]} · <span class="priority-{u}">{u} {T["priority"]}</span></div>
            <p style="margin:0 0 0.2rem; color:#111827; font-weight:600;">{decoded.get("doc_type", "")}</p>
            <p style="margin:0; color:#4b5563; font-size:0.88rem;">{decoded.get("agency", "")}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**{T['decode_means']}**")
        st.markdown(f"<div class='info-box'>{decoded.get('what_it_means', '')}</div>", unsafe_allow_html=True)

        key_dates = [d for d in decoded.get("key_dates", []) if parse_iso_date(d.get("date", ""))]
        if key_dates:
            st.markdown(f"**{T['decode_deadlines']}**")
            today = date.today()
            for d in sorted(key_dates, key=lambda x: x["date"]):
                day_obj = parse_iso_date(d["date"])
                days_away = (day_obj - today).days
                when = f"{days_away} {T['decode_days_left']}" if days_away >= 0 else T["decode_passed"]
                past = days_away < 0
                st.markdown(f"""
                <div class="deadline-row{' deadline-past' if past else ''}">
                    <div class="deadline-date">{day_obj.strftime("%b %d, %Y")}<br>
                    <span style="font-weight:400; color:{'#6b7280' if past else '#b91c1c'}; font-size:0.8rem;">{when}</span></div>
                    <div class="deadline-what">{d.get("what", "")}</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("")
            st.download_button(
                T["decode_download_ics"],
                data=decode_deadlines_to_ics(key_dates),
                file_name="letter-deadlines.ics",
                mime="text/calendar",
            )

        if decoded.get("actions"):
            st.markdown(f"**{T['decode_actions']}**")
            for i, action in enumerate(decoded["actions"], 1):
                st.markdown(f"""
                <div class="step-item">
                    <div class="step-num">{i}.</div>
                    <div style="color:#374151; font-size:0.92rem;">{action}</div>
                </div>
                """, unsafe_allow_html=True)

        if decoded.get("details"):
            st.markdown(f"**{T['decode_details']}**")
            detail_rows = "".join(
                f"<div class='step-item'><div style='font-weight:600; color:#111827; font-size:0.9rem; width:200px; flex-shrink:0;'>{d.get('field', '')}</div>"
                f"<div style='color:#374151; font-size:0.9rem;'>{d.get('value', '')}</div></div>"
                for d in decoded["details"]
            )
            st.markdown(f"<div class='info-box'>{detail_rows}</div>", unsafe_allow_html=True)

        if decoded.get("needs_lawyer"):
            help_link = "<a href='https://www.immigrationlawhelp.org' target='_blank'>immigrationlawhelp.org</a>"
            help_text = T["decode_get_help"].replace("immigrationlawhelp.org", help_link)
            st.markdown(f"<div class='flag-box'>{help_text}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TAB 1 — NEWS (auto-loads, no button)
# ---------------------------------------------------------------------------
with tab1:
    st.markdown(f"### {T['news_heading']}")

    topic_filter = st.selectbox(
        T["news_filter_label"],
        ["All", "H-1B", "F-1 / Students", "Family Green Cards", "Employment Green Cards"],
    )

    with st.spinner(T["news_loading"]):
        result = fetch_uscis_news()
        raw_items = result.get("items", [])
        source = result.get("source", "unavailable")

        fetched_at = result.get("fetched_at", "")
        try:
            fetched_date = datetime.fromisoformat(fetched_at).strftime("%B %d, %Y") if fetched_at else datetime.now().strftime("%B %d, %Y")
        except Exception:
            fetched_date = datetime.now().strftime("%B %d, %Y")

        enriched = []
        source_note = ""

        if source == "file" and raw_items:
            try:
                enriched = enrich_news(json.dumps(raw_items), topic_filter, LANG) or []
            except Exception:
                enriched = []
            if enriched:
                source_note = f"From USCIS.gov and other official sources, last updated {fetched_date}"

        # Live search grounding only when there's nothing to show. It's the
        # slowest call, so keep it out of the common path.
        if not enriched:
            live = grounded_news(topic_filter, LANG) or []
            seen_titles = {i.get("title", "").lower() for i in enriched}
            fresh = [i for i in live if i.get("title", "").lower() not in seen_titles]
            if fresh:
                enriched = enriched + fresh
                source_note = (source_note + " · plus live Google Search of official sources") if source_note \
                    else "Found through a live Google Search of official sources just now"

        # Last resort: model knowledge, clearly labeled
        if not enriched:
            try:
                enriched = knowledge_fallback(topic_filter, LANG)
            except Exception:
                enriched = []
            if enriched:
                source_note = "Based on recent USCIS and policy updates"

        # If every AI path failed, still show the real government headlines
        # (only for "All" — raw headlines aren't filtered by topic)
        if not enriched and raw_items and topic_filter == "All":
            enriched = [{
                "title": i.get("title", ""),
                "link": i.get("link", ""),
                "published": i.get("published", ""),
                "source": i.get("source", ""),
                "plain_summary": (i.get("summary", "") or "")[:220],
                "priority": "medium",
                "affects": "",
            } for i in raw_items[:8]]
            source_note = f"Official headlines from USCIS.gov and other government sources, last updated {fetched_date}"

    st.markdown(f"<div class='section-label'>{T['news_latest_heading']}</div>", unsafe_allow_html=True)
    if not enriched:
        st.markdown(f"<div class='info-box'>{T['news_none']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"<p style='color:#6b7280; font-size:0.82rem; margin-bottom:1rem;'>{source_note}</p>",
            unsafe_allow_html=True
        )
        for item in enriched:
            p = item.get("priority", "low")
            priority_html = f'<span class="priority-{p}">{p} {T["priority"]}</span>'
            pub = item.get("published", "")[:16] if item.get("published") else ""
            link = item.get("link", "https://www.uscis.gov/newsroom")
            source_tag = item.get("source", "")
            source_html = f'&nbsp;·&nbsp; <span style="color:#6b7280; font-size:0.8rem;">{source_tag}</span>' if source_tag else ""
            st.markdown(f"""
            <div class="news-item">
                <div class="news-meta">{pub} &nbsp;·&nbsp; {priority_html}{source_html} &nbsp;·&nbsp; {item.get("affects", "")}</div>
                <div class="news-title"><a href="{link}" target="_blank" rel="noopener">{item.get("title", "")}</a></div>
                <div class="news-context">{item.get("plain_summary", "")}</div>
            </div>
            """, unsafe_allow_html=True)

    # Evergreen essentials — always shown, whatever the news cycle is doing
    essentials = translated_essentials(topic_filter, LANG)
    if essentials:
        st.markdown("---")
        st.markdown(f"<div class='section-label'>{T['news_essentials_heading']}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='color:#6b7280; font-size:0.82rem; margin-bottom:0.4rem;'>{T['essentials_reviewed']}</p>",
            unsafe_allow_html=True
        )
        for item in essentials:
            st.markdown(f"""
            <div class="plain-item">
                <div class="news-title"><a href="{item.get("link", "")}" target="_blank" rel="noopener">{item.get("title", "")}</a>
                &nbsp;<span class="pill-essential">{T["essential_tag"]}</span></div>
                <div class="news-context">{item.get("summary", "")}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div class='section-label'>{T['news_fr_heading']}</div>", unsafe_allow_html=True)
    fr_items = fetch_federal_register()
    if fr_items:
        for doc in fr_items:
            st.markdown(f"""
            <div class="news-item">
                <div class="news-meta">{doc.get("date", "")} &nbsp;·&nbsp; {doc.get("type", "")}</div>
                <div class="news-title"><a href="{doc.get('link', '#')}" target="_blank" rel="noopener">{doc.get("title", "")}</a></div>
                {"<div class='news-context'>" + doc.get("abstract", "") + "</div>" if doc.get("abstract") else ""}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color:#6b7280; font-size:0.88rem;'>{T['news_fr_unavailable']}</p>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TAB 2 — YOUR SITUATION (Gemini reads PDFs and photos natively)
# ---------------------------------------------------------------------------
with tab2:
    st.markdown(f"### {T['situation_heading']}")
    st.markdown(
        f"<p style='color:#4b5563; font-size:0.9rem;'>{T['situation_intro']}</p>",
        unsafe_allow_html=True
    )

    visa_status = st.selectbox(T["situation_status_label"], [
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
        country = st.text_input(T["situation_country_label"], placeholder=T["situation_country_ph"])
    with col_b:
        uploaded = st.file_uploader(
            T["situation_upload_label"],
            type=["pdf", "txt", "png", "jpg", "jpeg", "webp"]
        )

    concern = st.text_area(
        T["situation_concern_label"],
        placeholder=T["situation_concern_ph"],
        height=100
    )

    if st.button(T["situation_button"], type="primary"):
        with st.spinner(T["situation_spinner"]):
            prompt = f"""You are an experienced US immigration advisor. Read this person's situation carefully and give them a clear, honest, direct assessment. Write like you're explaining this to a friend — no jargon, no filler phrases, no hedging beyond what's legally necessary.

Their situation:
- Status: {visa_status}
- Country of birth: {country or "not specified"}
- What they told us: {concern or "no details provided"}

{"They also attached a document (included with this message). Read it carefully — it may be an I-20, EAD card, visa stamp, approval notice, or a photo of one. Extract the specific facts: document type, names of forms, visa category, SEVIS number, program dates, expiration dates, receipt numbers. Use those real details in your assessment, and list what you found." if uploaded else ""}

Return ONLY this JSON:
{{
  "summary": "2-3 sentences that honestly describe where they stand right now",
  "document_details": [{{"field": "what was found (e.g. Document type, OPT end date, SEVIS number)", "value": "the exact value from the document"}}],
  "main_issues": [
    {{"issue": "specific issue or risk", "detail": "explain it plainly in 2 sentences", "urgency": "high|medium|low"}}
  ],
  "what_to_do": ["specific action", "specific action", "specific action"],
  "watch_out_for": ["thing 1", "thing 2"],
  "realistic_note": "one honest note about their situation — good or bad, just real",
  "deadlines": "any real deadlines or time-sensitive things they should know about",
  "official_resources": ["Form name or USCIS page title and URL"]
}}

If no document was attached, return an empty list for "document_details". Never invent document values.
Country of birth matters for priority dates — call it out if India, Mexico, Philippines, or China.
If they asked about H-1B and lost the lottery, give them real alternatives, not generic encouragement.{lang_rule(LANG)}"""

            try:
                if uploaded:
                    file_bytes = uploaded.read()
                    mime = uploaded.type or "application/pdf"
                    if uploaded.name.lower().endswith(".txt"):
                        contents = [prompt + "\n\nDocument text:\n" + file_bytes.decode("utf-8", errors="ignore")[:8000]]
                    else:
                        contents = [
                            types.Part.from_bytes(data=file_bytes, mime_type=mime),
                            prompt,
                        ]
                else:
                    contents = prompt

                st.session_state["situation_result"] = generate(contents)
            except Exception:
                st.session_state["situation_result"] = None
                st.error(T["error_generic"])

    data = st.session_state.get("situation_result")
    if data:
        st.markdown(f"""
        <div class="info-box" style="border-left: 3px solid #1d4ed8; background:#f0f7ff;">
            <div style="font-size:0.75rem; font-weight:600; color:#1d4ed8; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.4rem;">{T["situation_your_situation"]}</div>
            <p style="margin:0; color:#111827;">{data.get("summary", "")}</p>
        </div>
        """, unsafe_allow_html=True)

        if data.get("document_details"):
            st.markdown(f"**{T['situation_from_doc']}**")
            doc_rows = "".join(
                f"<div class='step-item'><div style='font-weight:600; color:#111827; font-size:0.9rem; width:200px; flex-shrink:0;'>{d.get('field', '')}</div>"
                f"<div style='color:#374151; font-size:0.9rem;'>{d.get('value', '')}</div></div>"
                for d in data["document_details"]
            )
            st.markdown(f"<div class='info-box'>{doc_rows}</div>", unsafe_allow_html=True)

        if data.get("main_issues"):
            st.markdown(f"**{T['situation_dealing']}**")
            for issue in data["main_issues"]:
                u = issue.get("urgency", "low")
                st.markdown(f"""
                <div class="info-box">
                    <div class="priority-{u}" style="margin-bottom:0.3rem;">{u} {T["priority"]}</div>
                    <strong>{issue.get("issue", "")}</strong>
                    <p style="margin:0.4rem 0 0; font-size:0.9rem;">{issue.get("detail", "")}</p>
                </div>
                """, unsafe_allow_html=True)

        col_l, col_r = st.columns(2)
        with col_l:
            if data.get("what_to_do"):
                st.markdown(f"**{T['situation_what_to_do']}**")
                for i, action in enumerate(data["what_to_do"], 1):
                    st.markdown(f"""
                    <div class="step-item">
                        <div class="step-num">{i}.</div>
                        <div style="color:#374151; font-size:0.92rem;">{action}</div>
                    </div>
                    """, unsafe_allow_html=True)

            if data.get("deadlines"):
                st.markdown(f"**{T['situation_deadlines']}**")
                st.markdown(f"<div class='flag-box'>{data['deadlines']}</div>", unsafe_allow_html=True)

        with col_r:
            if data.get("watch_out_for"):
                st.markdown(f"**{T['situation_watch_out']}**")
                for w in data["watch_out_for"]:
                    st.markdown(f"<div class='flag-box'>{w}</div>", unsafe_allow_html=True)

            if data.get("realistic_note"):
                st.markdown(f"**{T['situation_note']}**")
                st.markdown(f"<div class='info-box'>{data['realistic_note']}</div>", unsafe_allow_html=True)

        if data.get("official_resources"):
            st.markdown(f"**{T['situation_resources']}**")
            for r in data["official_resources"]:
                st.markdown(f"- {r}")


# ---------------------------------------------------------------------------
# TAB — OPT / STEM OPT DEADLINE CALCULATOR (deterministic date math)
# ---------------------------------------------------------------------------
def build_opt_deadlines(stage, key_date, stem_eligible):
    """All rules computed in Python from USCIS regulations — no AI dates."""
    deadlines = []
    if stage == "student":
        program_end = key_date
        deadlines.append({
            "date": program_end - timedelta(days=90),
            "what": "Earliest day USCIS can receive your OPT application (Form I-765) — 90 days before your program end date. Apply as early as you can.",
            "key": "opt_window_open",
        })
        deadlines.append({
            "date": program_end,
            "what": "Program end date on your I-20. Your F-1 on-campus work authorization ends here.",
            "key": "program_end",
        })
        deadlines.append({
            "date": program_end + timedelta(days=60),
            "what": "LAST day USCIS can receive your OPT application, and the last day of your 60-day grace period to leave the US, change status, or transfer if you don't apply.",
            "key": "opt_window_close",
        })
        if stem_eligible:
            deadlines.append({
                "date": program_end + timedelta(days=60),
                "what": "If your OPT is approved, remember: you can later extend with 24-month STEM OPT. We'll compute those dates once you have your EAD end date.",
                "key": "stem_reminder",
            })
    else:
        opt_end = key_date
        deadlines.append({
            "date": opt_end - timedelta(days=90),
            "what": "Earliest day to file your 24-month STEM OPT extension (Form I-765 with I-983 training plan) — 90 days before your OPT ends.",
            "key": "stem_window_open",
        })
        deadlines.append({
            "date": opt_end,
            "what": "OPT end date on your EAD. USCIS must RECEIVE your STEM extension application before this date. If filed on time, you can keep working up to 180 days while it's pending.",
            "key": "opt_end",
        })
        deadlines.append({
            "date": opt_end + timedelta(days=60),
            "what": "End of your 60-day grace period if you do not file the STEM extension — leave the US, change status, or start a new program by this date.",
            "key": "grace_end",
        })
    return sorted(deadlines, key=lambda d: d["date"])


def deadlines_to_ics(deadlines):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Immigration Co-Pilot//OPT Deadlines//EN",
    ]
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for i, d in enumerate(deadlines):
        day = d["date"].strftime("%Y%m%d")
        summary = d["what"].split(".")[0][:80]
        lines += [
            "BEGIN:VEVENT",
            f"UID:opt-{i}-{day}@immigration-copilot",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{day}",
            f"SUMMARY:Immigration deadline: {summary}",
            f"DESCRIPTION:{d['what']}",
            "BEGIN:VALARM",
            "TRIGGER:-P14D",
            "ACTION:DISPLAY",
            "DESCRIPTION:Immigration deadline in 2 weeks",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


@st.cache_data(ttl=None, show_spinner=False)
def explain_opt_plan(stage, key_date_iso, stem_eligible, lang):
    prompt = f"""A student is using an OPT deadline calculator. Their stage: {"finishing their F-1 program" if stage == "student" else "currently on OPT, considering STEM extension"}. Key date: {key_date_iso}. STEM-eligible degree: {stem_eligible}.

In 4-5 plain sentences, explain what their timeline means and the single most important thing to not miss. Mention the unemployment day limits (90 days on OPT, 150 total on STEM OPT). No legal advice disclaimer needed. Warm, direct tone.{lang_rule(lang)}

Return ONLY this JSON: {{"explanation": "your 4-5 sentences"}}"""
    try:
        return generate(prompt).get("explanation", "")
    except Exception:
        return ""


with tab_opt:
    st.markdown(f"### {T['opt_heading']}")
    st.markdown(f"<p style='color:#4b5563; font-size:0.9rem;'>{T['opt_intro']}</p>", unsafe_allow_html=True)

    stage_label = st.radio(
        T["opt_stage_label"],
        [T["opt_stage_student"], T["opt_stage_opt"]],
    )
    stage = "student" if stage_label == T["opt_stage_student"] else "on_opt"

    col_d, col_s = st.columns(2)
    with col_d:
        key_date = st.date_input(
            T["opt_program_end"] if stage == "student" else T["opt_end_date"],
            value=date.today() + timedelta(days=120),
            min_value=date.today() - timedelta(days=365),
            max_value=date.today() + timedelta(days=365 * 3),
        )
    with col_s:
        stem_eligible = st.checkbox(T["opt_stem_eligible"], value=(stage == "on_opt"))

    if st.button(T["opt_button"], type="primary"):
        st.session_state["opt_result"] = {
            "deadlines": build_opt_deadlines(stage, key_date, stem_eligible),
            "stage": stage,
            "key_date": key_date.isoformat(),
            "stem": stem_eligible,
        }

    opt_result = st.session_state.get("opt_result")
    if opt_result:
        st.markdown(f"**{T['opt_timeline']}**")
        today = date.today()
        for d in opt_result["deadlines"]:
            past = d["date"] < today
            days_away = (d["date"] - today).days
            when = f"{days_away} days" if days_away >= 0 else "passed"
            st.markdown(f"""
            <div class="deadline-row{' deadline-past' if past else ''}">
                <div class="deadline-date">{d["date"].strftime("%b %d, %Y")}<br>
                <span style="font-weight:400; color:#6b7280; font-size:0.8rem;">{when}</span></div>
                <div class="deadline-what">{d["what"]}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        st.download_button(
            T["opt_download_ics"],
            data=deadlines_to_ics(opt_result["deadlines"]),
            file_name="immigration-deadlines.ics",
            mime="text/calendar",
        )

        with st.spinner(T["opt_explain_spinner"]):
            explanation = explain_opt_plan(opt_result["stage"], opt_result["key_date"], opt_result["stem"], LANG)
        if explanation:
            st.markdown(f"<div class='info-box'>{explanation}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TAB 3 — GREEN CARD CHECKLIST
# ---------------------------------------------------------------------------
with tab3:
    st.markdown(f"### {T['checklist_heading']}")
    st.markdown(
        f"<p style='color:#4b5563; font-size:0.9rem;'>{T['checklist_intro']}</p>",
        unsafe_allow_html=True
    )

    with st.form("checklist"):
        col1, col2 = st.columns(2)

        with col1:
            relationship = st.selectbox(T["checklist_petition_label"], [
                "Spouse of a US Citizen",
                "Spouse of a Green Card holder",
                "Child of a US Citizen (under 21, unmarried)",
                "Child of a Green Card holder",
                "Parent of a US Citizen",
                "Sibling of a US Citizen"
            ])
            location = st.selectbox(T["checklist_location_label"], [
                "Inside the US (Adjustment of Status, I-485)",
                "Outside the US (Consular Processing)"
            ])
            gc_country = st.text_input(T["checklist_country_label"], placeholder=T["checklist_country_ph"])

        with col2:
            marriage_years = 0.0
            if "Spouse" in relationship:
                marriage_years = st.number_input(T["checklist_married_label"], min_value=0.0, max_value=60.0, value=1.0, step=0.5)
            income = st.number_input(T["checklist_income_label"], min_value=0, max_value=1000000, value=55000, step=1000)
            household = st.number_input(T["checklist_household_label"], min_value=1, max_value=20, value=2)
            violations = st.checkbox(T["checklist_violations_label"])

        notes = st.text_area(T["checklist_notes_label"], placeholder=T["checklist_notes_ph"], height=70)

        submitted = st.form_submit_button(T["checklist_button"], type="primary")

    if submitted:
        if not gc_country.strip():
            st.error(T["checklist_country_required"])
        else:
            with st.spinner(T["checklist_spinner"]):
                prompt = f"""You are a US immigration attorney. Generate a complete, accurate green card application checklist for this case. Be specific and thorough. Do not add generic disclaimers inside the checklist items.

Case:
- Petition type: {relationship}
- Applicant location: {location}
- Country of birth: {gc_country}
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

Flag conditional green card if married less than 2 years. Flag backlog wait if country is India, Mexico, Philippines, or China. Include both petitioner and applicant documents. Be complete.
The cover letter must always stay in English (USCIS requires English), but everything else follows the language rule.{lang_rule(LANG)}"""

                try:
                    st.session_state["checklist_result"] = generate(prompt)
                except Exception:
                    st.session_state["checklist_result"] = None
                    st.error(T["error_generic"])

    result = st.session_state.get("checklist_result")
    if result:
        flags = result.get("red_flags", [])
        if flags:
            st.markdown(f"**{T['checklist_aware']}**")
            for f in flags:
                st.markdown(f"<div class='flag-box'>{f}</div>", unsafe_allow_html=True)
            st.markdown("")

        st.markdown(f"**{T['checklist_forms']}**")
        forms_html = " ".join([
            f"<span class='form-tag'>{f.get('number', '')} — {f.get('name', '')} ({f.get('fee', '')}, {T['filed_by']} {f.get('filed_by', '')})</span>"
            for f in result.get("forms", [])
        ])
        st.markdown(forms_html, unsafe_allow_html=True)
        st.markdown("")

        col_t, col_i = st.columns(2)
        with col_t:
            st.markdown(f"**{T['checklist_timeline']}**")
            st.markdown(f"<div class='info-box'>{result.get('timeline', '')}</div>", unsafe_allow_html=True)
        with col_i:
            st.markdown(f"**{T['checklist_income']}**")
            st.markdown(f"<div class='info-box'>{result.get('income_note', '')}</div>", unsafe_allow_html=True)

        st.markdown("")

        st.markdown(f"**{T['checklist_documents']}**")
        st.markdown(
            f"<p style='color:#4b5563; font-size:0.85rem; margin-bottom:1rem;'>{T['checklist_required_note']}</p>",
            unsafe_allow_html=True
        )

        categories = {}
        for item in result.get("checklist", []):
            cat = item.get("category", "Other")
            categories.setdefault(cat, []).append(item)

        for cat, items in categories.items():
            with st.expander(f"{cat} ({len(items)})", expanded=True):
                for item in items:
                    req = item.get("required", False)
                    label = f"{T['required']} — " if req else ""
                    st.markdown(f"**{label}{item.get('item', '')}**")
                    st.markdown(
                        f"<span style='color:#4b5563; font-size:0.88rem;'>{item.get('why', '')}</span><br>"
                        f"<span style='color:#6b7280; font-size:0.85rem;'>{T['how_to_get']}: {item.get('how_to_get', '')}</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown("")

        st.markdown(f"**{T['checklist_cover']}**")
        st.markdown(
            f"<p style='color:#4b5563; font-size:0.85rem;'>{T['checklist_cover_note']}</p>",
            unsafe_allow_html=True
        )
        st.text_area(T["checklist_cover_label"], value=result.get("cover_letter", ""), height=320, label_visibility="collapsed")

        st.markdown(f"**{T['checklist_next']}**")
        for i, step in enumerate(result.get("next_steps", []), 1):
            st.markdown(f"""
            <div class="step-item">
                <div class="step-num">{i}.</div>
                <div style="font-size:0.92rem; color:#374151;">{step}</div>
            </div>
            """, unsafe_allow_html=True)

        # Downloadable copy — share it with a family member or attorney
        def checklist_as_text(r):
            out = ["IMMIGRATION CO-PILOT — GREEN CARD CHECKLIST", f"Generated {date.today().strftime('%B %d, %Y')}", ""]
            if r.get("red_flags"):
                out.append("THINGS TO BE AWARE OF:")
                out += [f"  ! {f}" for f in r["red_flags"]]
                out.append("")
            out.append("FORMS TO FILE:")
            out += [f"  - {f.get('number', '')} {f.get('name', '')} ({f.get('fee', '')}, filed by {f.get('filed_by', '')})" for f in r.get("forms", [])]
            out += ["", "DOCUMENT CHECKLIST:"]
            for item in r.get("checklist", []):
                req = "[REQUIRED] " if item.get("required") else "[  ] "
                out.append(f"  {req}{item.get('item', '')} — {item.get('why', '')}")
            out += ["", f"TIMELINE: {r.get('timeline', '')}", "", f"INCOME: {r.get('income_note', '')}", "", "NEXT STEPS:"]
            out += [f"  {i}. {s}" for i, s in enumerate(r.get("next_steps", []), 1)]
            out += ["", "COVER LETTER:", "", r.get("cover_letter", ""), "",
                    "Generated by Immigration Co-Pilot. Not legal advice."]
            return "\n".join(out)

        st.markdown("")
        st.download_button(
            T["checklist_download"],
            data=checklist_as_text(result),
            file_name="green-card-checklist.txt",
            mime="text/plain",
        )

        st.markdown("")
        st.markdown(
            f"<p style='color:#6b7280; font-size:0.82rem;'>{T['checklist_disclaimer']}</p>",
            unsafe_allow_html=True
        )


# ---------------------------------------------------------------------------
# TAB 4 — ABOUT
# ---------------------------------------------------------------------------
with tab4:
    st.markdown("### About this tool")

    st.markdown("""
    Immigration Co-Pilot is a free tool built to make US immigration information more accessible.

    Most people going through a green card or visa process can't afford an attorney, or don't know
    if they even need one. The goal here is to give you a clear starting point: what forms you need,
    what documents to gather, and what's actually happening in immigration policy right now,
    in your own language.
    """)

    st.markdown("**Who made this**")
    st.markdown("""
    We're Saina and Arsh, two students. Our families went through this system, and we watched
    the people around us pay for answers that were sitting on USCIS.gov the whole time, or worse,
    miss deadlines because a scary letter sat unopened in a drawer.

    So we built the tool we wished our parents had: something that reads the letter, tells you
    the deadline, and says what to do next in the language you think in. It's free, it stays free,
    and every line of code is public. If it helps your family, that's the whole point.
    """)

    st.markdown("**Where the information comes from**")
    st.markdown("""
    - The news tab pulls directly from the [USCIS newsroom RSS feed](https://www.uscis.gov/rss/uscis-news.xml)
      and the [Federal Register API](https://www.federalregister.gov), refreshed every 48 hours.
      When those sources are quiet, the app searches the live web through Google and cites what it finds.
      The plain-English explanations are generated by AI based on the real headlines.
    - The OPT deadline calculator computes dates directly from USCIS regulations in code —
      the AI only explains them, it never invents them.
    - The green card checklist is built from USCIS form instructions and the Federal Poverty Guidelines.
      The AI generates it based on your specific case details.
    - Processing times change frequently. Always check [egov.uscis.gov/processing-times](https://egov.uscis.gov/processing-times/) directly.
    """)

    st.markdown("**Free legal help**")
    st.markdown("""
    - [immigrationlawhelp.org](https://www.immigrationlawhelp.org) — directory of free and low-cost nonprofit legal services
    - [USCIS list of pro bono legal service providers](https://www.uscis.gov/citizenship/civic-integration/find-help-in-your-community)
    - [EOIR list of accredited representatives](https://www.justice.gov/eoir/recognized-organizations-and-accredited-representatives)
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
    The AI parts of this tool are powered by Google's Gemini model: it reads uploaded documents
    (including photos), searches the live web for current policy news, translates the entire
    interface into 12 languages, and writes every plain-language explanation.
    The tool was built as part of the Build with Gemini XPRIZE hackathon.
    """)

    st.markdown("---")
    st.markdown(
        "<p style='color:#6b7280; font-size:0.82rem;'>Found a bug or have feedback? The tool is open source at "
        "<a href='https://github.com/sainakakkar2006/immigration-copilot'>github.com/sainakakkar2006/immigration-copilot</a></p>",
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# Footer — who made this, on every page
# ---------------------------------------------------------------------------
st.markdown(f"""
<div class="site-footer">
    {T["footer_made"]}
    {T["footer_sources"]}<br>
    <a href="https://github.com/sainakakkar2006/immigration-copilot" target="_blank" rel="noopener">Open source on GitHub</a>
    &nbsp;·&nbsp; <a href="https://github.com/sainakakkar2006/immigration-copilot/issues" target="_blank" rel="noopener">{T["footer_feedback"]}</a>
    &nbsp;·&nbsp; <a href="https://www.immigrationlawhelp.org" target="_blank" rel="noopener">immigrationlawhelp.org</a>
</div>
""", unsafe_allow_html=True)
