"""
Roman Urdu to Urdu Text Converter
"""
import re

# Roman Urdu to Urdu mapping
ROMAN_TO_URDU = {
    # Single letters
    'a': 'ا', 'b': 'ب', 'p': 'پ', 't': 'ت', 'ṭ': 'ٹ',
    's': 'س', 'j': 'ج', 'ch': 'چ', 'h': 'ح', 'kh': 'خ',
    'd': 'د', 'ḍ': 'ڈ', 'r': 'ر', 'ṛ': 'ڑ', 'z': 'ز',
    'zh': 'ژ', 'sh': 'ش', 'gh': 'غ', 'f': 'ف', 'q': 'ق',
    'k': 'ک', 'g': 'گ', 'l': 'ل', 'm': 'م', 'n': 'ن',
    'v': 'و', 'y': 'ی', 'e': 'ے', 'o': 'و', 'i': 'ی',
    
    # Common words and phrases
    'salam': 'سلام',
    'assalamualaikum': 'السلام علیکم',
    'aap': 'آپ',
    'tum': 'تم',
    'main': 'میں',
    'wo': 'وہ',
    'ye': 'یہ',
    'ka': 'کا',
    'ki': 'کی',
    'ke': 'کے',
    'ko': 'کو',
    'se': 'سے',
    'mein': 'میں',
    'par': 'پر',
    'hai': 'ہے',
    'hain': 'ہیں',
    'ho': 'ہو',
    'hun': 'ہوں',
    'tha': 'تھا',
    'thi': 'تھی',
    'the': 'تھے',
    'na': 'نہ',
    'bhi': 'بھی',
    'to': 'تو',
    'agar': 'اگر',
    'kyun': 'کیوں',
    'kya': 'کیا',
    'kaise': 'کیسے',
    'kitna': 'کتنا',
    'kahan': 'کہاں',
    'kab': 'کب',
    'mera': 'میرا',
    'meri': 'میری',
    'hamara': 'ہمارا',
    'tera': 'تیرا',
    'teri': 'تیری',
    'allah': 'اللہ',
    'khuda': 'خدا',
    'shukriya': 'شکریہ',
    'meherbani': 'مہربانی',
    'maaf': 'معاف',
    'ji': 'جی',
    'han': 'ہاں',
    'nahi': 'نہیں',
    'acha': 'اچھا',
    'theek': 'ٹھیک',
    'insaan': 'انسان',
    'duniya': 'دنیا',
    'pyar': 'پیار',
    'mohabbat': 'محبت',
    'dost': 'دوست',
    'yaar': 'یار',
    
    # Numbers
    '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
    '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹',
}

def roman_urdu_to_urdu_text(text):
    """
    Convert Roman Urdu text to Urdu script
    
    Example:
    >>> roman_urdu_to_urdu_text("aap kaise hain?")
    'آپ کیسے ہیں؟'
    """
    if not text:
        return text
    
    # Convert to lowercase for processing
    text_lower = text.lower()
    
    # Replace common phrases first
    urdu_text = text
    
    # Sort keys by length (longest first) to prevent partial matches
    sorted_keys = sorted(ROMAN_TO_URDU.keys(), key=len, reverse=True)
    
    for roman in sorted_keys:
        if roman in text_lower:
            # Replace with Urdu, preserving original case context
            pattern = re.compile(re.escape(roman), re.IGNORECASE)
            urdu_text = pattern.sub(ROMAN_TO_URDU[roman], urdu_text)
    
    # Add Urdu punctuation
    urdu_text = urdu_text.replace('?', '؟')
    
    return urdu_text

# Test function
if __name__ == "__main__":
    test_cases = [
        ("salam", "سلام"),
        ("aap kaise hain?", "آپ کیسے ہیں؟"),
        ("mera naam ahmed hai", "میرا نام احمد ہے"),
        ("shukriya", "شکریہ"),
        ("allah hafiz", "اللہ حافظ"),
        ("ye kitne ka hai?", "یہ کتنے کا ہے؟"),
    ]
    
    print("🧪 Testing Roman Urdu Converter:")
    print("-" * 40)
    
    for roman, expected in test_cases:
        result = roman_urdu_to_urdu_text(roman)
        status = "✅" if result == expected else "❌"
        print(f"{status} {roman:30} → {result:20} (Expected: {expected})")
