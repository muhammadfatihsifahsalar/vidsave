# VidSave — ভিডিও ডাউনলোডার

YouTube, Facebook, TikTok, Instagram সহ ১০০০+ সাইট থেকে সরাসরি ভিডিও ডাউনলোড করুন।

---

## 🚀 Render.com এ Deploy করার নিয়ম (ফ্রি)

### ধাপ ১ — GitHub এ আপলোড করুন
1. github.com এ যান → Sign Up / Login করুন
2. "New Repository" চাপুন
3. নাম দিন: `vidsave`
4. সব ফাইল আপলোড করুন (app.py, index.html, requirements.txt, render.yaml)
5. "Commit changes" চাপুন

### ধাপ ২ — Render.com এ Deploy করুন
1. render.com এ যান → Sign Up করুন (GitHub দিয়ে)
2. "New +" → "Web Service" চাপুন
3. আপনার `vidsave` repository সিলেক্ট করুন
4. নিচের সেটিংস দিন:
   - **Build Command:** `apt-get install -y ffmpeg && pip install -r requirements.txt`
   - **Start Command:** `python app.py`
5. "Create Web Service" চাপুন
6. ৩-৫ মিনিট অপেক্ষা করুন
7. আপনার লিংক পাবেন: `https://vidsave-xxxx.onrender.com`

---

## ✅ ফিচার
- YouTube, Facebook, TikTok, Instagram, Twitter/X সাপোর্ট
- ১০০০+ সাইট সাপোর্ট (yt-dlp powered)
- সরাসরি ডাউনলোড — কোনো থার্ড পার্টি নেই
- ভিডিও কোয়ালিটি বেছে নেওয়া যায়
- MP3 অডিও ডাউনলোড
- মোবাইল ফ্রেন্ডলি UI

---

## ⚠️ নোট
শুধুমাত্র ব্যক্তিগত ব্যবহারের জন্য।
