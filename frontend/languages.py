"""
WASTE IQ – Multilingual Support
Languages: English (en), Hindi (hi), Malayalam (ml), Tamil (ta), Telugu (te)
Usage: from languages import t, set_language
"""

import streamlit as st

TRANSLATIONS = {
    # ── Navigation ─────────────────────────────────────────────────────────
    "nav_dashboard":        {"en": "Dashboard",       "hi": "डैशबोर्ड",       "ml": "ഡാഷ്ബോർഡ്",     "ta": "டாஷ்போர்டு",     "te": "డాష్‌బోర్డ్"},
    "nav_classify":         {"en": "Classify Waste",  "hi": "अपशिष्ट वर्गीकरण","ml": "മാലിന്യ തരംതിരിവ്","ta": "கழிவு வகைப்படுத்தல்","te": "వ్యర్థాల వర్గీకరణ"},
    "nav_complaints":       {"en": "Complaints",      "hi": "शिकायतें",        "ml": "പരാതികൾ",        "ta": "புகார்கள்",        "te": "ఫిర్యాదులు"},
    "nav_route":            {"en": "My Route",        "hi": "मेरा मार्ग",      "ml": "എന്റെ റൂട്ട്",    "ta": "என் பாதை",        "te": "నా మార్గం"},
    "nav_rewards":          {"en": "Rewards",         "hi": "पुरस्कार",        "ml": "പ്രതിഫലങ്ങൾ",    "ta": "வெகுமதிகள்",      "te": "బహుమతులు"},
    "nav_notifications":    {"en": "Notifications",   "hi": "सूचनाएं",         "ml": "അറിയിപ്പുകൾ",    "ta": "அறிவிப்புகள்",    "te": "నోటిఫికేషన్లు"},
    "nav_profile":          {"en": "Profile",         "hi": "प्रोफ़ाइल",       "ml": "പ്രൊഫൈൽ",        "ta": "சுயவிவரம்",       "te": "ప్రొఫైల్"},
    "nav_admin":            {"en": "Admin Panel",     "hi": "व्यवस्थापक पैनल","ml": "അഡ്മിൻ പാനൽ",   "ta": "நிர்வாக குழு",    "te": "అడ్మిన్ విండో"},
    "nav_logout":           {"en": "Logout",          "hi": "लॉगआउट",         "ml": "ലോഗ്ഔട്ട്",      "ta": "வெளியேறு",        "te": "లాగ్అవుట్"},

    # ── Auth ───────────────────────────────────────────────────────────────
    "auth_login":           {"en": "Sign In",         "hi": "साइन इन",         "ml": "സൈൻ ഇൻ",         "ta": "உள்நுழை",         "te": "సైన్ ఇన్"},
    "auth_signup":          {"en": "Create Account",  "hi": "खाता बनाएं",      "ml": "അക്കൗണ്ട് ഉണ്ടാക്കുക","ta": "கணக்கை உருவாக்கு","te": "ఖాతా సృష్టించు"},
    "auth_email":           {"en": "Email Address",   "hi": "ईमेल पता",        "ml": "ഇ-മെയിൽ",        "ta": "மின்னஞ்சல்",       "te": "ఇమెయిల్"},
    "auth_password":        {"en": "Password",        "hi": "पासवर्ड",         "ml": "പാസ്‌വേഡ്",       "ta": "கடவுச்சொல்",      "te": "పాస్‌వర్డ్"},
    "auth_name":            {"en": "Full Name",       "hi": "पूरा नाम",        "ml": "പൂർണ്ണ നാമം",    "ta": "முழு பெயர்",      "te": "పూర్తి పేరు"},
    "auth_role":            {"en": "Select Role",     "hi": "भूमिका चुनें",   "ml": "റോൾ തിരഞ്ഞെടുക്കുക","ta": "பங்கை தேர்ந்தெடு","te": "పాత్ర ఎంచుకోండి"},
    "auth_welcome":         {"en": "Welcome to WASTE IQ","hi": "WASTE IQ में आपका स्वागत है","ml": "WASTE IQ-ലേക്ക് സ്വാഗതം","ta": "WASTE IQ-க்கு வரவேற்கிறோம்","te": "WASTE IQ కి స్వాగతం"},
    "auth_tagline":         {"en": "Smart Waste. Cleaner Cities.","hi": "स्मार्ट अपशिष्ट। स्वच्छ शहर।","ml": "സ്മാർട്ട് മാലിന്യം. ശുദ്ധമായ നഗരങ്ങൾ.","ta": "ஸ்மார்ட் கழிவு. சுத்தமான நகரங்கள்.","te": "స్మార్ట్ వ్యర్థాలు. శుభ్రమైన నగరాలు."},

    # ── Dashboard ──────────────────────────────────────────────────────────
    "dash_total_class":     {"en": "Total Classifications","hi": "कुल वर्गीकरण","ml": "ആകെ വർഗ്ഗീകരണങ്ങൾ","ta": "மொத்த வகைப்பாடு","te": "మొత్తం వర్గీకరణలు"},
    "dash_total_points":    {"en": "Total Points",    "hi": "कुल अंक",         "ml": "ആകെ പോയിന്റ്",   "ta": "மொத்த புள்ளிகள்", "te": "మొత్తం పాయింట్లు"},
    "dash_complaints":      {"en": "Active Complaints","hi": "सक्रिय शिकायतें","ml": "സജീവ പരാതികൾ",   "ta": "செயலில் புகார்கள்","te": "చురుకైన ఫిర్యాదులు"},
    "dash_bins_at_risk":    {"en": "Bins at Risk",    "hi": "जोखिम में डिब्बे","ml": "അപകടകരമായ ബക്കറ്റുകൾ","ta": "ஆபத்தில் உள்ள குப்பை","te": "ప్రమాదంలో ఉన్న బిన్లు"},
    "dash_today_route":     {"en": "Today's Route",   "hi": "आज का मार्ग",     "ml": "ഇന്നത്തെ റൂട്ട്", "ta": "இன்றைய பாதை",     "te": "ఈరోజు మార్గం"},
    "dash_history":         {"en": "Waste History",   "hi": "अपशिष्ट इतिहास", "ml": "മാലിന്യ ചരിത്രം", "ta": "கழிவு வரலாறு",    "te": "వ్యర్థాల చరిత్ర"},
    "dash_good_morning":    {"en": "Good morning",    "hi": "सुप्रभात",         "ml": "സുപ്രഭാതം",       "ta": "காலை வணக்கம்",    "te": "శుభోదయం"},
    "dash_good_afternoon":  {"en": "Good afternoon",  "hi": "शुभ अपराह्न",    "ml": "ശുഭ ഉച്ചയ്ക്ക്", "ta": "மதிய வணக்கம்",   "te": "శుభ మధ్యాహ్నం"},
    "dash_good_evening":    {"en": "Good evening",    "hi": "शुभ संध्या",      "ml": "ശുഭ സന്ധ്യ",     "ta": "மாலை வணக்கம்",   "te": "శుభ సాయంత్రం"},

    # ── Classifier ─────────────────────────────────────────────────────────
    "cls_upload":           {"en": "Upload Image",    "hi": "चित्र अपलोड करें","ml": "ചിത്രം അപ്‌ലോഡ് ചെയ്യുക","ta": "படத்தை பதிவேற்று","te": "చిత్రం అప్‌లోడ్ చేయండి"},
    "cls_camera":           {"en": "Use Camera",      "hi": "कैमरा उपयोग करें","ml": "ക്യാമറ ഉപയോഗിക്കുക","ta": "கேமரா பயன்படுத்து","te": "కెమెరా ఉపయోగించండి"},
    "cls_result":           {"en": "Classification Result","hi": "वर्गीकरण परिणाम","ml": "വർഗ്ഗീകരണ ഫലം","ta": "வகைப்பாட்டு முடிவு","te": "వర్గీకరణ ఫలితం"},
    "cls_object":           {"en": "Detected Object", "hi": "पता लगाई वस्तु",  "ml": "കണ്ടെത്തിയ വസ്തു","ta": "கண்டறியப்பட்ட பொருள்","te": "గుర్తించిన వస్తువు"},
    "cls_category":         {"en": "Waste Category",  "hi": "अपशिष्ट श्रेणी", "ml": "മാലിന്യ വർഗ്ഗം",  "ta": "கழிவு வகை",       "te": "వ్యర్థాల వర్గం"},
    "cls_confidence":       {"en": "Confidence",      "hi": "विश्वास",         "ml": "ആത്മവിശ്വാസം",   "ta": "நம்பகத்தன்மை",   "te": "నమ్మకం"},
    "cls_disposal":         {"en": "Disposal Instructions","hi": "निपटान निर्देश","ml": "നിർമ്മാർജ്ജന നിർദ്ദേശങ്ങൾ","ta": "அகற்றல் வழிமுறைகள்","te": "వదిలించుకోవడానికి సూచనలు"},
    "cls_tip":              {"en": "Recycling Tip",   "hi": "पुनर्चक्रण टिप",  "ml": "റീസൈക്ലിങ് ടിപ്","ta": "மறுசுழற்சி குறிப்பு","te": "రీసైక్లింగ్ చిట్కా"},

    # ── Complaints ─────────────────────────────────────────────────────────
    "comp_new":             {"en": "New Complaint",   "hi": "नई शिकायत",       "ml": "പുതിയ പരാതി",    "ta": "புதிய புகார்",    "te": "కొత్త ఫిర్యాదు"},
    "comp_title":           {"en": "Issue Title",     "hi": "समस्या शीर्षक",   "ml": "പ്രശ്ന ശീർഷകം",  "ta": "சிக்கல் தலைப்பு", "te": "సమస్య శీర్షిక"},
    "comp_desc":            {"en": "Description",     "hi": "विवरण",           "ml": "വിവരണം",         "ta": "விளக்கம்",        "te": "వివరణ"},
    "comp_status_open":     {"en": "Open",            "hi": "खुला",            "ml": "തുറന്നത്",       "ta": "திறந்த",          "te": "తెరుచుకుంది"},
    "comp_status_resolved": {"en": "Resolved",        "hi": "हल किया",         "ml": "പരിഹരിച്ചു",     "ta": "தீர்க்கப்பட்டது","te": "పరిష్కరించబడింది"},
    "comp_submit":          {"en": "Submit Complaint","hi": "शिकायत दर्ज करें","ml": "പരാതി സമർപ്പിക്കുക","ta": "புகார் அளி",     "te": "ఫిర్యాదు సమర్పించండి"},

    # ── Driver ─────────────────────────────────────────────────────────────
    "driver_mark_collected":{"en": "Mark Collected",  "hi": "एकत्रित चिह्नित करें","ml": "ശേഖരിച്ചതായി അടയാളപ്പെടുത്തുക","ta": "சேகரிக்கப்பட்டதாக குறி","te": "సేకరించినట్టు గుర్తించండి"},
    "driver_bins":          {"en": "Assigned Bins",   "hi": "सौंपे गए डिब्बे","ml": "നിയോഗിക്കപ്പെട്ട ബക്കറ്റുകൾ","ta": "ஒதுக்கப்பட்ட குப்பைகள்","te": "కేటాయించిన బిన్లు"},
    "driver_distance":      {"en": "Total Distance",  "hi": "कुल दूरी",        "ml": "ആകെ ദൂരം",        "ta": "மொத்த தூரம்",     "te": "మొత్తం దూరం"},
    "driver_eta":           {"en": "Est. Time",       "hi": "अनुमानित समय",    "ml": "ആനുമാനിക സമയം",  "ta": "மதிப்பீட்டு நேரம்","te": "అంచనా సమయం"},

    # ── General ────────────────────────────────────────────────────────────
    "btn_save":             {"en": "Save",            "hi": "सहेजें",          "ml": "സംരക്ഷിക്കുക",   "ta": "சேமி",            "te": "సేవ్ చేయండి"},
    "btn_cancel":           {"en": "Cancel",          "hi": "रद्द करें",       "ml": "റദ്ദാക്കുക",      "ta": "ரத்து செய்",      "te": "రద్దు చేయండి"},
    "btn_refresh":          {"en": "Refresh",         "hi": "रीफ्रेश",         "ml": "പുതുക്കുക",       "ta": "புதுப்பி",        "te": "రిఫ్రెష్"},
    "btn_export_csv":       {"en": "Export CSV",      "hi": "CSV निर्यात",     "ml": "CSV കയറ്റുമതി",   "ta": "CSV ஏற்றுமதி",    "te": "CSV ఎగుమతి"},
    "btn_export_pdf":       {"en": "Download Report", "hi": "रिपोर्ट डाउनलोड","ml": "റിപ്പോർട്ട് ഡൗൺലോഡ്","ta": "அறிக்கையை இறக்கு","te": "రిపోర్ట్ డౌన్‌లోడ్"},
    "lbl_language":         {"en": "Language",        "hi": "भाषा",            "ml": "ഭാഷ",             "ta": "மொழி",            "te": "భాష"},
    "lbl_dark_mode":        {"en": "Dark Mode",       "hi": "डार्क मोड",       "ml": "ഡാർക്ക് മോഡ്",   "ta": "இருண்ட முறை",    "te": "డార్క్ మోడ్"},
    "lbl_ward":             {"en": "Ward",            "hi": "वार्ड",           "ml": "വാർഡ്",           "ta": "வார்டு",          "te": "వార్డు"},
    "lbl_fill_level":       {"en": "Fill Level",      "hi": "भरण स्तर",        "ml": "നിറ നില",         "ta": "நிரப்பு நிலை",   "te": "నింపే స్థాయి"},
    "lbl_status":           {"en": "Status",          "hi": "स्थिति",          "ml": "നില",             "ta": "நிலை",            "te": "స్థితి"},
    "lbl_risk":             {"en": "Risk Level",      "hi": "जोखिम स्तर",      "ml": "അപകട നില",        "ta": "ஆபத்து நிலை",    "te": "ప్రమాద స్థాయి"},
    "msg_loading":          {"en": "Loading...",      "hi": "लोड हो रहा है...", "ml": "ലോഡ് ചെയ്യുന്നു...","ta": "ஏற்றுகிறது...",  "te": "లోడవుతోంది..."},
    "msg_no_data":          {"en": "No data available","hi": "डेटा उपलब्ध नहीं","ml": "ഡാറ്റ ലഭ്യമല്ല","ta": "தரவு இல்லை",     "te": "డేటా అందుబాటులో లేదు"},
    "msg_success":          {"en": "Success!",        "hi": "सफलता!",          "ml": "വിജയം!",          "ta": "வெற்றி!",         "te": "విజయం!"},
    "msg_error":            {"en": "Error occurred",  "hi": "त्रुटि हुई",      "ml": "പിഴവ് സംഭവിച്ചു","ta": "பிழை ஏற்பட்டது", "te": "లోపం సంభవించింది"},
    "msg_points_earned":    {"en": "Points earned",   "hi": "अंक अर्जित किए", "ml": "പോയിന്റ് നേടി",  "ta": "புள்ளிகள் பெறப்பட்டன","te": "పాయింట్లు సంపాదించారు"},
}

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "हिन्दी",
    "ml": "മലയാളം",
    "ta": "தமிழ்",
    "te": "తెలుగు",
}

def t(key: str) -> str:
    """Translate a key to the active language. Falls back to English."""
    lang = st.session_state.get("language", "en")
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key   # Key not found — return key itself
    return entry.get(lang) or entry.get("en") or key

def set_language(lang: str) -> None:
    """Set the active language in session state."""
    if lang in LANGUAGE_NAMES:
        st.session_state["language"] = lang
