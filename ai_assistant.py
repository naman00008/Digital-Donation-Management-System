import os
import sqlite3
import re
from datetime import datetime

# Try importing google.genai
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def get_ngo_context(db_path='rayoftrust.db'):
    """Fetch real-time context from database to ground AI responses."""
    context_lines = []
    
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Active Campaigns
        cursor.execute("SELECT title, category, target_amount, raised_amount, description FROM campaigns WHERE status = 'Active' LIMIT 5")
        campaigns = cursor.fetchall()
        if campaigns:
            context_lines.append("Active Campaigns:")
            for c in campaigns:
                pct = (c['raised_amount'] / c['target_amount'] * 100) if c['target_amount'] > 0 else 0
                context_lines.append(f"- {c['title']} ({c['category']}): Target ₹{c['target_amount']:,.0f}, Raised ₹{c['raised_amount']:,.0f} ({pct:.1f}% funded). {c['description']}")
        
        # 2. Shelter Kids for Celebrations
        cursor.execute("SELECT name, age, dream_aspiration, favorite_treat FROM shelter_kids LIMIT 6")
        kids = cursor.fetchall()
        if kids:
            context_lines.append("\nShelter Children Available for Birthday/Occasion Celebration Sponsoring:")
            for k in kids:
                context_lines.append(f"- {k['name']} (Age {k['age']}): Dream: {k['dream_aspiration']}. Favorite Treat: {k['favorite_treat']}")
        
        # 3. Overall Stats
        cursor.execute("SELECT COUNT(*) as total_donations, SUM(amount) as total_raised FROM donations WHERE status = 'Received'")
        stats = cursor.fetchone()
        if stats:
            total_donations = stats['total_donations'] or 0
            total_raised = stats['total_raised'] or 0.0
            context_lines.append(f"\nOverall NGO Impact: {total_donations} total verified donations raised over ₹{total_raised:,.0f} supporting 60+ shelter children.")
            
        conn.close()
    except Exception as e:
        context_lines.append(f"Context fetch note: Using default NGO parameters ({e}).")
        
    return "\n".join(context_lines)

def generate_smart_fallback(user_query, channel='web', context="", language='English'):
    res = _raw_smart_fallback(user_query, channel, context, language)
    if channel == 'voice':
        res = re.sub(r'[*#_`~]', '', res)
    return res

def _raw_smart_fallback(user_query, channel='web', context="", language='English'):
    query = user_query.lower().strip()
    lang = language.lower().strip()
    
    # 1. Hindi (हिंदी)
    if 'hi' in lang or 'hindi' in lang or 'हिंदी' in query:
        if any(k in query for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', 'help', 'give', 'दान', 'पेमेंट']):
            return ("🙏 **रे ऑफ ट्रस्ट एनजीओ (Ray of Trust NGO) में आपका स्वागत है**\n\n"
                    "आश्रय बच्चों की सहायता के लिए आप निम्नलिखित माध्यमों से दान कर सकते हैं:\n\n"
                    "• **ऑनलाइन कार्ड / स्ट्राइप भुगतान**: हमारे [दान पोर्टल](/donate) पर जाकर क्रेडिट/डेबिट कार्ड से दान करें।\n"
                    "• **तत्काल यूपीआई (UPI) भुगतान**: सीधे एनजीओ यूपीआई आईडी `namanmtj2005-2@okicici` पर ट्रांसफर करें।\n\n"
                    "📜 **80G आयकर छूट**: प्रत्येक दान पर आपको तुरंत धारा 80G के तहत कर छूट की रसीद प्रदान की जाती है।")
        elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'occasion', 'जन्मदिन', 'बर्थडे']):
            return ("🎉 **आश्रय के बच्चों के साथ जन्मदिन व विशेष अवसर मनाएं**\n\n"
                    "अपने या अपने परिवार के जन्मदिन या वर्षगांठ पर 60 बच्चों के चेहरे पर मुस्कान लाएं!\n\n"
                    "🎂 **पैकेज विवरण**:\n"
                    "1. ताज़ा केक काटने का समारोह\n"
                    "2. 60 बच्चों के लिए स्वादिष्ट भोजन व आइसक्रीम\n"
                    "3. फोटो के साथ आधिकारिक सेलिब्रेशन पास\n\n"
                    "👉 अपनी तिथि आरक्षित करने के लिए [सेलिब्रेशन पेज](/celebrate) पर जाएं।")
        elif any(k in query for k in ['campaign', 'drive', 'project', 'active', 'अभियान']):
            return ("🌟 **हमारे सक्रिय अभियान (Active Campaigns)**\n\n"
                    "• **वाकड शेल्टर पोषण अभियान**: 60 बच्चों के लिए दैनिक भोजन व दूध (लक्ष्य: ₹75,000 | प्राप्त: ₹54,200)\n"
                    "• **बैक-टू-स्कूल शिक्षा किट**: स्कूल बैग व विज्ञान किट (लक्ष्य: ₹50,000 | प्राप्त: ₹39,500)\n"
                    "• **दिवाली स्माइल्स वस्त्र अभियान**: नए त्योहारी कपड़े व मिठाइयां (लक्ष्य: ₹1,00,000 | प्राप्त: ₹15,000)\n\n"
                    "👉 विवरण देखने के लिए [अभियान पेज](/campaigns) पर जाएं।")
        elif any(k in query for k in ['tax', '80g', 'receipt', 'कर']):
            return ("📜 **धारा 80G के तहत 100% कर छूट**\n\n"
                    "रे ऑफ ट्रस्ट एनजीओ आयकर अधिनियम की धारा 80G के तहत पंजीकृत है। दान पूरा होते ही आपको आधिकारिक कर रसीद प्राप्त होती है।\n\n"
                    "👉 रसीद डाउनलोड करने के लिए हमारे [डोनर पोर्टल](/donor_login) या [दान पोर्टल](/donate) पर जाएं।")
        else:
            return ("👋 **नमस्ते! मैं आशा (Aasha) हूँ - रे ऑफ ट्रस्ट एनजीओ एआई सहायक।**\n\n"
                    "मैं आपकी सहायता के लिए यहाँ हूँ। आप मुझसे दान, 80G कर छूट रसीद, सक्रिय अभियानों और बच्चों के साथ जन्मदिन मनाने के बारे में पूछ सकते हैं!")

    # 2. Marathi (मराठी)
    elif 'mr' in lang or 'marathi' in lang or 'मराठी' in query:
        if any(k in query for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', 'help', 'give', 'देणगी']):
            return ("🙏 **रे ऑफ ट्रस्ट एनजीओ (Ray of Trust NGO) मध्ये आपले स्वागत आहे**\n\n"
                    "आपण खालील प्रकारे देणगी देऊन अनाथ मुलांना मदत करू शकता:\n\n"
                    "• **ऑनलाइन कार्ड / पेमेंट**: आमच्या [देणगी पोर्टलवर](/donate) जाऊन देणगी द्या.\n"
                    "• **थेट यूपीआई (UPI) पेमेंट**: यूपीआय आयडी `namanmtj2005-2@okicici` वर ट्रान्सफर करा.\n\n"
                    "📜 **80G कर सवलत**: प्रत्येक देणगीवर आपल्याला कलम 80G अंतर्गत करात सवलत मिळणारी अधिकृत पावती त्वरित मिळते.")
        elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'occasion', 'वाढदिवस']):
            return ("🎉 **अनाथ मुलांसोबत वाढदिवस व विशेष प्रसंग साजरा करा**\n\n"
                    "आपला वाढदिवस किंवा लग्नसोहळा 60 मुलांसोबत साजरा करून त्यांच्या आयुष्यात आनंद निर्माण करा!\n\n"
                    "🎂 **समाविष्ट गोष्टी**:\n"
                    "1. ताजी केक कापण्याचा सोहळा\n"
                    "2. 60 मुलांसाठी विशेष मिष्टान्न व जेवण\n"
                    "3. फोटोसह अधिकृत सेलिब्रेशन पास\n\n"
                    "👉 तुमची तारीख आरक्षित करण्यासाठी [सेलिब्रेशन पेजवर](/celebrate) जा.")
        elif any(k in query for k in ['campaign', 'drive', 'project', 'active', 'उपक्रम']):
            return ("🌟 **आमचे सक्रिय उपक्रम (Active Campaigns)**\n\n"
                    "• **वाकड शेल्टर पोषण अभियान**: 60 मुलांसाठी दररोजचे जेवण (लक्ष्य: ₹75,000 | प्राप्त: ₹54,200)\n"
                    "• **शालेय साहित्य किट**: दप्तर व विज्ञान किट (लक्ष्य: ₹50,000 | प्राप्त: ₹39,500)\n"
                    "• **दिवाळी स्माईल कपडे अभियान**: नवीन कपडे व फराळ (लक्ष्य: ₹1,00,000 | प्राप्त: ₹15,000)\n\n"
                    "👉 अधिक माहितीसाठी [उपक्रम पेजवर](/campaigns) जा.")
        else:
            return ("👋 **नमस्कार! मी आशा (Aasha) - रे ऑफ ट्रस्ट एनजीओ एआई साहाय्यक.**\n\n"
                    "मी आपल्याला मदत करण्यासाठी येथे आहे. आपण मला देणगी, 80G कर सवलत पावती, सक्रिय उपक्रम आणि मुलांसोबत वाढदिवस साजरा करण्याबाबत विचारू शकता!")

    # 3. Gujarati (ગુજરાતી)
    elif 'gu' in lang or 'gujarati' in lang or 'ગુજરાતી' in query:
        if any(k in query for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', 'help', 'give', 'દાન']):
            return ("🙏 **રે ઓફ ટ્રસ્ટ એનજીઓ (Ray of Trust NGO) માં તમારું સ્વાગત છે**\n\n"
                    "અનાથ બાળકોની મદદ માટે તમે નીચેના માધ્યમોથી દાન કરી શકો છો:\n\n"
                    "• **ઓનલાઈન કાર્ડ / પેમેન્ટ**: અમારા [દાન પોર્ટલ](/donate) પર જઈને દાન કરો.\n"
                    "• **ઈન્સ્ટન્ટ UPI પેમેન્ટ**: સીધા UPI ID `namanmtj2005-2@okicici` પર ટ્રાન્સફર કરો.\n\n"
                    "📜 **80G ટેક્સ છૂટ**: દરેક દાન પર તમને કલમ 80G હેઠળ ટેક્સ છૂટની રસીદ તાત્કાલિક મળે છે.")
        elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'occasion', 'જન્મદિવસ']):
            return ("🎉 **બાળકો સાથે જન્મદિવસ અને ખાસ પ્રસંગો ઉજવો**\n\n"
                    "તમારા અથવા પરિવારના જન્મદિવસ પર 60 અનાથ બાળકો સાથે કેક કાપીને ખુશીઓ વહેંચો!\n\n"
                    "🎂 **પેકેજ વિગતો**:\n"
                    "1. તાજી કેક કાપવાનો સમારોહ\n"
                    "2. 60 બાળકો માટે સ્વાદિષ્ટ ભોજન અને આઈસ્ક્રીમ\n"
                    "3. ફોટો સાથેનો ઑફિશિયલ સેલિબ્રેશન પાસ\n\n"
                    "👉 તમારી તારીખ બુક કરવા માટે [સેલિબ્રેશન પેજ](/celebrate) પર જાઓ.")
        else:
            return ("👋 **નમસ્તે! હું આશા (Aasha) છું - રે ઓફ ટ્રસ્ટ એનજીઓ AI સહાયક.**\n\n"
                    "હું તમને દાન, 80G ટેક્સ રસીદ, સક્રિય ઝુંબેશ અને બાળકો સાથે જન્મદિવસ ઉજવવા અંગે મદદ કરી શકું છું!")

    # 4. Tamil (தமிழ்)
    elif 'ta' in lang or 'tamil' in lang or 'தமிழ்' in query:
        if any(k in query for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', 'help', 'give', 'நன்கொடை']):
            return ("🙏 **ரே ஆஃப் டிரஸ்ட் தொண்டு நிறுவனத்திற்கு வரவேற்கிறோம் (Ray of Trust NGO)**\n\n"
                    "குழந்தைகளுக்கு உதவ நீங்கள் பின்வரும் வழிகளில் நன்கொடை அளிக்கலாம்:\n\n"
                    "• **ஆன்லைன் கார்டு செலுத்துதல்**: எங்களின் [நன்கொடை போர்டல்](/donate) மூலம் செலுத்தலாம்.\n"
                    "• **UPI கட்டணம்**: நேரடியாக `namanmtj2005-2@okicici` என்ற UPI முகவரிக்கு அனுப்பலாம்.\n\n"
                    "📜 **80G வரி விலக்கு**: ஒவ்வொரு நன்கொடைக்கும் 80G பிரிவின் கீழ் உடனடியாக வரி விலக்கு ரசீது வழங்கப்படும்.")
        elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'occasion', 'பிறந்தநாள்']):
            return ("🎉 **குழந்தைகளுடன் பிறந்தநாளைக் கொண்டாடுங்கள்**\n\n"
                    "60 ஆதரவற்ற குழந்தைகளுடன் கேக் வெட்டி உங்கள் பிறந்தநாளைக் கொண்டாடுங்கள்!\n\n"
                    "👉 பதிவு செய்ய [கொண்டாட்டப் பக்கத்தைப்](/celebrate) பார்வையிடவும்.")
        else:
            return ("👋 **வணக்கம்! நான் ஆஷா (Aasha) - ரே ஆஃப் டிரஸ்ட் AI உதவியாளர்.**\n\n"
                    "நன்கொடை, 80G வரி ரசீது மற்றும் ஆதரவற்ற குழந்தைகளின் கொண்டாட்டங்கள் பற்றி என்னிடம் கேட்கலாம்!")

    # 5. Telugu (తెలుగు)
    elif 'te' in lang or 'telugu' in lang or 'తెలుగు' in query:
        if any(k in query for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', 'help', 'give', 'విరాళం']):
            return ("🙏 **రే ఆఫ్ ట్రస్ట్ NGO కి స్వాగతం (Ray of Trust NGO)**\n\n"
                    "పిల్లలకు సహాయం చేయడానికి మీరు క్రింది మార్గాల ద్వారా విరాళం ఇవ్వవచ్చు:\n\n"
                    "• **ఆన్‌లైన్ కార్డ్ పేమెంట్**: మా [విరాళాల పోర్టల్](/donate) ద్వారా చెల్లించండి.\n"
                    "• **తక్షణ UPI చెల్లింపు**: నేరుగా UPI ID `namanmtj2005-2@okicici` కి పంపండి.\n\n"
                    "📜 **80G పన్ను మినహాయింపు**: ప్రతి విరాళానికి సెక్షన్ 80G కింద రసీదు తక్షణమే లభిస్తుంది.")
        elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'occasion', 'పుట్టినరోజు']):
            return ("🎉 **అనాథ పిల్లలతో పుట్టినరోజు జరుపుకోండి**\n\n"
                    "60 మంది పిల్లలకు రుచికరమైన భోజనం మరియు కేక్ అందించి మీ ప్రత్యేక రోజును జరుపుకోండి!\n\n"
                    "👉 స్లాట్ బుక్ చేయడానికి [వేడుకల పేజీని](/celebrate) సందర్శించండి.")
        else:
            return ("👋 **నమస్కారం! నేను ఆశా (Aasha) - రే ఆఫ్ ట్రస్ట్ AI అసిస్టెంట్.**\n\n"
                    "విరాళాలు, 80G పన్ను రసీదులు మరియు పిల్లల పుట్టినరోజు వేడుకల గురించి నన్ను అడగవచ్చు!")

    # 6. Bengali (বাংলা)
    elif 'bn' in lang or 'bengali' in lang or 'বাংলা' in query:
        if any(k in query for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', 'help', 'give', 'দান']):
            return ("🙏 **রে অফ ট্রাস্ট এনজিও (Ray of Trust NGO)-তে আপনাকে স্বাগতম**\n\n"
                    "আপনি নিম্নলিখিত উপায়ে দান করে শিশুদের সাহায্য করতে পারেন:\n\n"
                    "• **অনলাইন কার্ড পেমেন্ট**: আমাদের [দান পোর্টালে](/donate) গিয়ে দান করুন।\n"
                    "• **ইনস্ট্যান্ট UPI পেমেন্ট**: সরাসরি UPI ID `namanmtj2005-2@okicici`-তে পাঠান।\n\n"
                    "📜 **80G কর ছাড়**: প্রতিটি দানের জন্য 80G ধারায় তাৎক্ষণিক কর ছাড়ের রশিদ প্রদান করা হয়।")
        elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'occasion', 'জন্মদিন']):
            return ("🎉 **শিশুদের সাথে জন্মদিন ও বিশেষ দিন উদযাপন করুন**\n\n"
                    "৬০ জন শিশুর সাথে কেক কেটে আপনার জন্মদিন স্মরণীয় করে তুলুন!\n\n"
                    "👉 বুক করতে [উদযাপন পেজে](/celebrate) যান।")
        else:
            return ("👋 **নমস্কার! আমি আশা (Aasha) - রে অফ ট্রাস্ট এনজিও এআই সহায়ক।**\n\n"
                    "দান, 80G ট্যাক্স রসিদ এবং শিশুদের সাথে উৎসব উদযাপন সম্পর্কে আপনার প্রশ্নের উত্তর দিতে আমি প্রস্তুত!")

    # 7. Spanish (Español)
    elif 'es' in lang or 'spanish' in lang or 'español' in query:
        if any(k in query for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', 'help', 'give', 'donar', 'donación']):
            return ("🙏 **Bienvenido a Ray of Trust NGO**\n\n"
                    "Puedes apoyar a nuestros niños a través de los siguientes métodos:\n\n"
                    "• **Pago en línea con Tarjeta**: Visita nuestro [Portal de Donaciones](/donate).\n"
                    "• **Pago por UPI Directo**: Envía a la ID de UPI `namanmtj2005-2@okicici`.\n\n"
                    "📜 **Beneficio Fiscal 80G**: Cada donación incluye un recibo oficial deducible de impuestos bajo la Sección 80G.")
        elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'cumpleaños']):
            return ("🎉 **Celebra tu Cumpleaños con los Niños del Refugio**\n\n"
                    "¡Haz sonreír a 60 niños compartiendo un pastel y comida especial en tu día especial!\n\n"
                    "👉 Reserva tu fecha en la [Página de Celebraciones](/celebrate).")
        else:
            return ("👋 **¡Hola! Soy Aasha, tu asistente de Inteligencia Artificial para Ray of Trust NGO.**\n\n"
                    "Puedo ayudarte con información sobre donaciones, recibos de impuestos 80G, campañas activas y eventos con los niños.")

    # 8. French (Français)
    elif 'fr' in lang or 'french' in lang or 'français' in query:
        if any(k in query for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', 'help', 'give', 'don', 'donner']):
            return ("🙏 **Bienvenue à Ray of Trust NGO**\n\n"
                    "Vous pouvez soutenir nos 60 enfants par les moyens suivants :\n\n"
                    "• **Paiement en ligne par carte** : Visitez notre [Portail de Don](/donate).\n"
                    "• **Paiement UPI direct** : Envoyez vers l'ID UPI `namanmtj2005-2@okicici`.\n\n"
                    "📜 **Déduction Fiscale 80G** : Un reçu fiscal officiel est généré instantanément après chaque don.")
        elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'anniversaire']):
            return ("🎉 **Célébrez votre Anniversaire avec les Enfants**\n\n"
                    "Offrez un gâteau frais et un repas festif à 60 enfants pour votre anniversaire !\n\n"
                    "👉 Réservez votre créneau sur la [Page des Célébrations](/celebrate).")
        else:
            return ("👋 **Bonjour ! Je suis Aasha, l'assistante IA de Ray of Trust NGO.**\n\n"
                    "Je peux vous aider à faire un don, obtenir un reçu fiscal 80G ou organiser un anniversaire avec les enfants !")

    # 9. German (Deutsch)
    elif 'de' in lang or 'german' in lang or 'deutsch' in query:
        if any(k in query for k in ['donate', 'donation', 'payment', 'upi', 'stripe', 'money', 'help', 'give', 'spenden', 'spende']):
            return ("🙏 **Willkommen bei Ray of Trust NGO**\n\n"
                    "Sie können unsere Kinder wie folgt unterstützen:\n\n"
                    "• **Online-Kartenzahlung**: Besuchen Sie unser [Spendenportal](/donate).\n"
                    "• **Direkte UPI-Überweisung**: An die UPI-ID `namanmtj2005-2@okicici`.\n\n"
                    "📜 **80G Steuerbescheinigung**: Jede Spende erhält sofort eine offizielle Quittung für den Steuerabzug.")
        elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'geburtstag']):
            return ("🎉 **Feiern Sie Ihren Geburtstag mit unseren Heimkindern**\n\n"
                    "Schenken Sie 60 Kindern ein Lächeln mit Kuchen und einem Festmahl an Ihrem besonderen Tag!\n\n"
                    "👉 Buchen Sie auf der [Feier-Seite](/celebrate).")
        else:
            return ("👋 **Hallo! Ich bin Aasha, Ihre KI-Assistentin für Ray of Trust NGO.**\n\n"
                    "Ich helfe Ihnen gerne bei Fragen zu Spenden, Steuerbescheinigungen (80G) und Geburtstagsfeiern für Kinder!")

    # 10. English (Default)
    # Direct Payment Request
    if any(k in query for k in ['direct me', 'payment page', 'online payment', 'make payment', 'pay online', 'donate link', 'payment link', 'donate']):
        if channel == 'voice':
            return ("To make an online donation, please visit our secure donation portal at 127.0.0.1:5000/donate. "
                    "You can pay using credit card, debit card, or instant UPI using ID namanmtj2005-2@okicici. "
                    "All donations generate an instant 80G tax receipt.")
        elif channel == 'whatsapp':
            return ("💳 *Ray of Trust NGO - Online Donation Gateway*\n\n"
                    "We offer fast and secure ways to make your contribution:\n\n"
                    "1️⃣ *Online Card / Stripe Payment*:\n"
                    "👉 Visit our donation portal: http://127.0.0.1:5000/donate\n\n"
                    "2️⃣ *Instant UPI Payment*:\n"
                    "• *UPI ID*: `namanmtj2005-2@okicici`\n"
                    "• *Payee*: Ray of Trust Foundation\n\n"
                    "📜 *80G Tax Benefit*: Instant tax exemption receipt generated upon payment.")
        else:
            return ("💳 **Ray of Trust NGO - Online Donation Portal**\n\n"
                    "Thank you for supporting our shelter children! Here is how you can contribute:\n\n"
                    "• **Online Card / Stripe Payment**: Click here to open the [Secure Donation Page](/donate) to contribute via Card or Netbanking.\n"
                    "• **Instant UPI Payment**: Transfer directly to our official NGO UPI ID `namanmtj2005-2@okicici`.\n\n"
                    "Every donation is 100% tax-deductible under **Section 80G** with instant PDF receipts!")

    # General Support / How Can I Help
    elif any(k in query for k in ['how can i help', 'volunteer', 'ways to contribute', 'support ngo', 'how to help']):
        if channel == 'voice':
            return ("There are several ways you can support Ray of Trust NGO. "
                    "You can make a direct donation, sponsor a birthday celebration meal for shelter children, or donate educational supplies. "
                    "Please visit our website at 127.0.0.1:5000 to choose how you would like to help.")
        elif channel == 'whatsapp':
            return ("🤝 *How You Can Empower Children at Ray of Trust NGO*\n\n"
                    "1️⃣ *Financial Donation*: Support nutrition, healthcare, and education.\n"
                    "👉 Donate online: http://127.0.0.1:5000/donate\n\n"
                    "2️⃣ *Sponsor a Birthday Celebration*: Host a cake ceremony & meal for 60 children.\n"
                    "👉 Book a slot: http://127.0.0.1:5000/celebrate\n\n"
                    "3️⃣ *Support Active Campaigns*: School backpacks, science kits, or festive clothing.\n"
                    "👉 View campaigns: http://127.0.0.1:5000/campaigns")
        else:
            return ("🤝 **Ways You Can Make a Meaningful Difference**\n\n"
                    "Thank you for offering your support! Ray of Trust NGO provides multiple ways to contribute:\n\n"
                    "1. **Direct Financial Contribution**: Fund hot meals, healthcare, and education on our [Donate Portal](/donate).\n"
                    "2. **Sponsor a Celebration with Children**: Gift meals and cakes to shelter kids on your birthday or anniversary at our [Celebration Page](/celebrate).\n"
                    "3. **Contribute to Active Drives**: Help us fulfill specific targets on our [Campaigns Hub](/campaigns).\n"
                    "4. **On-Site Volunteering**: Contact our Wakad shelter team to volunteer or donate physical supplies.")

    # Active Campaigns Inquiry
    elif any(k in query for k in ['campaign', 'drive', 'project', 'active']):
        if channel == 'voice':
            return ("Our active campaigns include the Wakad Shelter Nutrition Drive, Back to School Science Kits, and Diwali Smiles Drive. "
                    "You can read details and contribute at 127.0.0.1:5000/campaigns.")
        elif channel == 'whatsapp':
            return ("🌟 *Active Community Campaigns at Ray of Trust NGO*\n\n"
                    "🍲 *Wakad Shelter Nutrition Drive* (Target: ₹75,000 | Raised: ₹54,200)\n"
                    "🎒 *Back-to-School Science Kits* (Target: ₹50,000 | Raised: ₹39,500)\n"
                    "🪔 *Diwali Smiles Festive Drive* (Target: ₹1,00,000 | Raised: ₹15,000)\n\n"
                    "👉 Support a campaign now: http://127.0.0.1:5000/campaigns")
        else:
            return ("🌟 **Active Community Campaigns**\n\n"
                    "Our active campaigns allow you to direct your donation to specific impact areas:\n\n"
                    "• **Wakad Shelter Nutrition & Hot Meals Drive** (Target: ₹75,000 | Raised: ₹54,200)\n"
                    "• **Back-to-School Science & Educational Kits** (Target: ₹50,000 | Raised: ₹39,500)\n"
                    "• **Diwali Smiles & New Clothes Festive Drive** (Target: ₹1,00,000 | Raised: ₹15,000)\n\n"
                    "👉 Explore full progress on the [Campaigns Hub](/campaigns).")

    # Birthday & Occasion Celebration Inquiry
    elif any(k in query for k in ['celebrate', 'birthday', 'kid', 'child', 'children', 'party', 'occasion']):
        if channel == 'voice':
            return ("You can celebrate your birthday, anniversary, or special milestone with our shelter children! "
                    "We organize cake cutting, special meal treats, and celebration passes. Visit 127.0.0.1:5000/celebrate to choose a slot.")
        elif channel == 'whatsapp':
            return ("🎉 *Celebrate Special Milestones with Shelter Children*\n\n"
                    "Transform your birthday into joy for 60 shelter kids!\n"
                    "Includes fresh cake cutting, special meals, and custom celebration pass.\n\n"
                    "👉 Reserve your date: http://127.0.0.1:5000/celebrate")
        else:
            return ("🎉 **Celebrate Special Milestones with Shelter Children**\n\n"
                    "Turn your birthday or anniversary into unforgettable memories for 60 shelter children!\n\n"
                    "**What We Arrange**:\n"
                    "1. **Cake Cutting Ceremony**: Fresh bakery cake customized for your occasion.\n"
                    "2. **Wholesome Meal Treat**: Full festive lunch/dinner for all shelter kids.\n"
                    "3. **Celebration Pass**: Official commemorative pass with photo details.\n\n"
                    "👉 Check calendar availability at the [Celebrate Page](/celebrate).")

    # Tax Benefits & 80G Receipts
    elif any(k in query for k in ['tax', '80g', 'receipt', 'deduction', 'certificate', 'pan']):
        if channel == 'voice':
            return ("Ray of Trust NGO is registered under Section 80G of the Indian Income Tax Act. "
                    "Every donation made through our portal generates an instant downloadable receipt with our PAN and tax registration details.")
        elif channel == 'whatsapp':
            return ("📜 *Section 80G Tax Exemption Guarantee*\n\n"
                    "All donations made to Ray of Trust NGO are eligible for tax deduction under Section 80G.\n"
                    "Includes official NGO PAN & instant downloadable PDF receipts.\n\n"
                    "👉 Donate & get receipt: http://127.0.0.1:5000/donate")
        else:
            return ("📜 **100% Tax Exemption Under Section 80G**\n\n"
                    "Ray of Trust NGO is a government-recognized charitable institution registered under **Section 80G**.\n\n"
                    "**Features**:\n"
                    "1. **Instant PDF Receipt**: Automatically generated immediately after payment.\n"
                    "2. **Official Credentials**: Contains our NGO PAN and 80G registration number.\n"
                    "3. **Donor Portal Access**: Download past receipts anytime in your [Donor Portal](/donor_login).\n\n"
                    "👉 Make a tax-deductible donation today at our [Donate Page](/donate).")

    # Default Fallback
    else:
        if channel == 'voice':
            return ("Welcome to Ray of Trust NGO. "
                    "I am Aasha, your AI guide. You can ask me about making a donation, 80G tax exemption receipts, active shelter campaigns, or booking birthday celebrations with shelter kids. "
                    "How may I assist you?")
        elif channel == 'whatsapp':
            return ("👋 *Welcome to Ray of Trust NGO Assistant (Aasha)*\n\n"
                    "• 💳 *Donations & 80G Tax Receipts*: http://127.0.0.1:5000/donate\n"
                    "• 🎂 *Birthday Celebrations*: http://127.0.0.1:5000/celebrate\n"
                    "• 🌟 *Active Campaigns*: http://127.0.0.1:5000/campaigns\n\n"
                    "Reply with your question and I will provide full details!")
        else:
            return ("👋 **Welcome to Ray of Trust NGO! I am Aasha, your AI Guide.**\n\n"
                    "How can I assist you today? You can ask me about:\n\n"
                    "1. **Making a Donation**: Step-by-step payment via Stripe or UPI.\n"
                    "2. **80G Tax Exemption**: Automated tax receipts for income tax deduction.\n"
                    "3. **Celebrating with Shelter Children**: Sponsoring birthday cakes and meals for 60 kids.\n"
                    "4. **Active Community Drives**: Nutrition, education kits, and winter clothing.\n\n"
                    "Type any question below or click one of the suggested prompts!")

def generate_ai_response(user_query, channel='web', user_id=None, db_path='rayoftrust.db', language='English'):
    """
    Generate AI response in the user's demanded language using Gemini API 
    (or intelligent multilingual fallback engine).
    """
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    ngo_context = get_ngo_context(db_path)
    
    if not api_key or not HAS_GENAI:
        return generate_smart_fallback(user_query, channel, ngo_context, language=language)
    
    try:
        client = genai.Client(api_key=api_key)
        
        channel_instructions = ""
        if channel == 'voice':
            channel_instructions = ("This response will be spoken aloud over a phone call. "
                                    "Keep it under 3 natural sentences, warm and professional. Do NOT use markdown symbols or URLs.")
        elif channel == 'whatsapp':
            channel_instructions = ("This response will be sent via WhatsApp. "
                                    "Format cleanly using WhatsApp bold (*text*), clean bullet points, relevant emojis, and complete URLs (e.g. http://127.0.0.1:5000/donate).")
        else:
            channel_instructions = ("This response will be displayed in the web chat widget. "
                                    "Structure with clear Markdown, bullet points, bold headers, and exact page links like [Donate Page](/donate) or [Celebrate Page](/celebrate).")

        system_instruction = f"""
You are Aasha, the highly professional, warm, and articulate AI Assistant for 'Ray of Trust NGO' (Digital Donation Management System).
Your mission is to provide thorough, well-structured, clear, and comprehensive answers to donors, volunteers, and supporters.

NGO Live Context:
{ngo_context}

CRITICAL MULTILINGUAL MANDATE:
- The user has explicitly selected the language: '{language}'.
- You MUST generate the ENTIRE response in the '{language}' language.
- Ensure natural, fluent, respectful, and culturally appropriate vocabulary for '{language}' speakers.
- Even if the user asks in English, answer completely in '{language}'.

Key Guidelines:
- Address the user's EXACT question with specific details.
- Never give generic robotic one-liners. Provide structured, actionable, and empathetic responses.
- {channel_instructions}
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_query,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.6,
                max_output_tokens=600,
            )
        )
        
        if response and response.text:
            text = response.text.strip()
            if channel == 'voice':
                text = re.sub(r'[*#_`~]', '', text)
            return text
        else:
            return generate_smart_fallback(user_query, channel, ngo_context, language=language)
            
    except Exception as e:
        print(f"[AI Assistant] Gemini API error: {e}")
        return generate_smart_fallback(user_query, channel, ngo_context, language=language)
