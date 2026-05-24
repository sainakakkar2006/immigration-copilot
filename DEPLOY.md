# Deploy to Streamlit Community Cloud — Free, No Billing

This takes about 10 minutes and gives you a live public URL like:
`https://immigration-copilot.streamlit.app`

---

## Step 1 — Push the code to GitHub

If you don't have git set up, open Terminal and run:

```bash
cd immigration-mvp   # or wherever this folder is
git init
git add .
git commit -m "Immigration Co-Pilot MVP"
```

Go to github.com → click the + icon → New Repository
- Name it: `immigration-copilot`
- Keep it Public
- Click Create Repository

GitHub will show you two commands. Run them:

```bash
git remote add origin https://github.com/YOUR_USERNAME/immigration-copilot.git
git branch -M main
git push -u origin main
```

---

## Step 2 — Deploy on Streamlit Community Cloud

1. Go to: **https://share.streamlit.io**
2. Sign up / log in with GitHub
3. Click **"New app"**
4. Select your `immigration-copilot` repository
5. Main file path: `app.py`
6. Click **"Advanced settings"**

In the **Secrets** box, paste:
```toml
GEMINI_API_KEY = "AIzaSyDKL12b_Hv95tbijAUgaGWjL_DlrWGb_6c"
```

7. Click **Deploy!**

Streamlit builds and deploys automatically. Takes about 2 minutes.
You'll get a public URL you can share with anyone.

---

## Step 3 — Share the link

Your app is now live 24/7 for free. Share the URL on:
- Reddit (r/immigration, r/USCIS, r/f1visa)
- Facebook immigration groups
- WhatsApp immigrant communities

Every update you push to GitHub auto-deploys in under 60 seconds.

---

## Running locally (for testing before deploying)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

To set your API key locally, create a file `.streamlit/secrets.toml` with:
```toml
GEMINI_API_KEY = "AIzaSyDKL12b_Hv95tbijAUgaGWjL_DlrWGb_6c"
```
