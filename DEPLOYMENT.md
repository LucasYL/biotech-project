# 🚀 Streamlit Cloud Deployment Guide

## What is Streamlit Cloud?

Streamlit Cloud is a **free hosting platform** for Streamlit apps, perfect for showcasing your projects to potential employers!

**Your deployed app will be accessible at**: `https://your-username-biotech-project.streamlit.app`

---

## 📋 Prerequisites

- ✅ GitHub account (you have this)
- ✅ Streamlit Cloud account (free, sign up with GitHub)
- ✅ Your project pushed to GitHub (done!)

---

## 🔧 Deployment Steps

### **Step 1: Sign Up for Streamlit Cloud**

1. Go to: https://share.streamlit.io/
2. Click **"Sign up"**
3. Choose **"Continue with GitHub"**
4. Authorize Streamlit to access your repositories

---

### **Step 2: Deploy Your App**

1. **Click "New app"** in Streamlit Cloud dashboard

2. **Fill in the form**:
   ```
   Repository: LucasYL/biotech-project
   Branch: main
   Main file path: dashboard/app.py
   ```

3. **Click "Deploy"**

4. Wait 2-3 minutes for deployment (first time takes longer)

5. **Your app is live!** 🎉

---

### **Step 3: Get Your Public URL**

Your app will be available at:
```
https://lucasyl-biotech-project-dashboardapp-xxxxx.streamlit.app
```

You can customize the subdomain in settings (e.g., `actinomycete-pipeline`).

---

## 🔗 Sharing Your App

### **For Job Applications**

Add to your resume/cover letter:
```
🔗 Live Demo: https://your-app.streamlit.app
```

### **For LinkedIn/Portfolio**

Share the link with a description:
```
🧬 Just deployed my drug discovery pipeline!
This AI-powered tool reduces drug validation costs by 67%.

Live demo: [link]
GitHub: [link]

#Bioinformatics #DrugDiscovery #DataScience #Python
```

---

## ⚙️ Configuration Files

### **requirements.txt** (Already created)
```txt
streamlit>=1.28.0
pandas>=2.0.0
rdkit>=2023.3.0
networkx>=3.0
...
```

### **.streamlit/config.toml** (Already created)
```toml
[theme]
primaryColor = "#4CAF50"
backgroundColor = "#FFFFFF"
...
```

---

## 🔄 Automatic Updates

**Great news**: Once deployed, Streamlit Cloud automatically updates your app when you push to GitHub!

**Workflow**:
```bash
# Make changes locally
git add .
git commit -m "Update dashboard"
git push

# Streamlit Cloud detects the push and redeploys (2-3 min)
# Your live app is updated!
```

---

## 📊 Usage & Limits (Free Tier)

| Feature | Free Tier |
|---------|-----------|
| **Number of apps** | Unlimited public apps |
| **Resources** | 1 GB RAM, 1 CPU |
| **Sleep policy** | Sleeps after 7 days inactivity |
| **Bandwidth** | Generous (fine for portfolio) |
| **Custom domain** | Not available (use .streamlit.app) |

**Note**: If your app sleeps, it wakes up instantly when someone visits.

---

## 🐛 Troubleshooting

### **Issue: RDKit installation fails**

**Solution**: Already handled in `requirements.txt` with version specification.

### **Issue: Data files not found**

**Problem**: Streamlit Cloud runs from repository root.

**Solution**: Use relative paths in code:
```python
BASE_DIR = Path(__file__).resolve().parents[1]  # Already implemented
DATA_DIR = BASE_DIR / "intermediate"
```

### **Issue: App is slow on first load**

**Reason**: Cloud instance is "waking up" after sleep.

**Solution**: Normal behavior, subsequent loads are fast.

---

## 🎯 Best Practices

### **1. Include Sample Data**

✅ Your repo already includes example data in `intermediate/` and `outputs/`

This ensures the app works even if users don't run the pipeline.

### **2. Add Loading Indicators**

```python
with st.spinner("Loading data..."):
    df = load_data()
```

### **3. Cache Expensive Operations**

```python
@st.cache_data
def load_large_table(path):
    return pd.read_parquet(path)
```

### **4. Optimize for Mobile**

✅ Already done: `layout="wide"` adjusts to screen size

---

## 🔒 Security Notes

### **What's Public**
- ✅ Your code (already on GitHub)
- ✅ Sample data (already public)
- ✅ Dashboard UI

### **What's Private**
- ❌ No sensitive data (example data is synthetic)
- ❌ No API keys needed

**Conclusion**: Safe to deploy publicly for portfolio!

---

## 📸 Taking Screenshots

### **For README**

1. Visit your live app
2. Take screenshots of key sections:
   - Dashboard overview
   - Top candidates table
   - ADMET analysis
   - Network visualization

3. Save to `docs/screenshots/`

4. Add to README:
   ```markdown
   ![Dashboard](docs/screenshots/dashboard.png)
   ```

---

## 🎓 Demo Script (For Interviews)

**When showing your deployed app**:

```
"Let me show you the live application I built..."

[Open app]

"This is an AI-powered drug discovery pipeline. At the top, 
you can see key metrics: we've identified 3 candidates with 
100% passing the drug-likeness criteria."

[Scroll to ranked candidates]

"Here are the top-ranked compounds. The scoring combines 
evidence from genomics, metabolomics, and chemistry - similar 
to how your team would integrate multi-omics data."

[Open ADMET section]

"For each candidate, I calculated ADMET properties using RDKit. 
You can see the QED score here - 0.762 for CMP003, which is 
in the excellent range for approved drugs."

[Open evidence table]

"This evidence integration was one of the technical challenges. 
Since BGC predictions, MS features, and chemical compounds 
don't share common IDs, I developed a probabilistic linking 
system..."

[Continue based on interviewer's questions]
```

---

## 🔗 Quick Reference

**Streamlit Cloud Dashboard**: https://share.streamlit.io/

**Your App URL** (after deployment): 
```
https://lucasyl-biotech-project-dashboardapp-xxxxx.streamlit.app
```

**Update App**:
```bash
git push  # That's it!
```

**View Logs**:
Go to Streamlit Cloud dashboard → Your app → "Manage app" → "Logs"

---

## ✅ Deployment Checklist

Before deploying, ensure:

- [x] `requirements.txt` exists
- [x] `.streamlit/config.toml` exists (optional but nice)
- [x] Sample data is committed to repo
- [x] `dashboard/app.py` uses relative paths
- [x] No hardcoded absolute paths
- [x] No sensitive credentials in code

**All done!** ✅ Ready to deploy!

---

## 🎉 After Deployment

### **1. Test Your Live App**

Visit the URL and verify:
- All sections load
- Data displays correctly
- Downloads work
- No errors in browser console

### **2. Add to Portfolio**

Update your:
- Resume (Projects section)
- LinkedIn (Featured section)
- GitHub profile README
- Cover letters

### **3. Share with Network**

Post on LinkedIn:
```
Excited to share my latest project: an AI-driven drug 
discovery pipeline that reduces validation costs by 67%!

🧬 Integrates genomics, metabolomics, and chemistry
💊 Real ADMET calculations with RDKit
🕸️ Molecular similarity networks
📊 Interactive dashboard

Live demo: [your-url]
GitHub: https://github.com/LucasYL/biotech-project

Feedback welcome! #Bioinformatics #AI #DrugDiscovery
```

---

**Good luck with your deployment and job search!** 🚀

