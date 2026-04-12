import subprocess
import time
import os
import random
import sys

# ضمان ظهور اللغة العربية بشكل صحيح في Terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# قائمة الدول المستهدفة
TARGET_COUNTRIES = [
    "US", "GB", "CA", "AU", "DE", "FR", "IT", "ES", "NL", "SE", 
    "SA", "AE", "ZA", "JP", "KR"
]

# قاموس لتخزين الإحصائيات لجميع الشبكات
stats = {
    "REVCONTENT": {"new": 0, "updates": 0},
    "TABOOLA": {"new": 0, "updates": 0},
    "MGID": {"new": 0, "updates": 0},
    "OUTBRAIN": {"new": 0, "updates": 0}
}

def run_script(script_name, country):
    start_time = time.time()
    print(f"📡 جاري إطلاق: {script_name} باستهداف ({country})...")
    try:
        env = os.environ.copy()
        env["TARGET_COUNTRY"] = country
        
        process = subprocess.Popen(
            ['python', script_name], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            env=env,
            encoding='utf-8' 
        )
        
        for line in process.stdout:
            print(line, end='') 
            
            # تحليل السطور لتحديث الإحصائيات لجميع الشبكات
            for network in stats:
                if f"[{network}]" in line.upper():
                    if "صيد جديد" in line or "تم الحفظ" in line:
                        stats[network]["new"] += 1
                    elif "تحديث" in line:
                        stats[network]["updates"] += 1

        process.wait()
        duration = (time.time() - start_time) / 60
        print(f"✅ اكتملت مهمة {script_name} في {duration:.2f} دقيقة.\n")
        return duration
    except Exception as e:
        print(f"❌ خطأ في تشغيل {script_name}: {e}")
        return 0

def show_dashboard(total_time):
    print("\n" + "*"*60)
    print("📊 ملخص جولة التجسس الشاملة (All Networks Active) 📊")
    print("*"*60)
    
    table_header = f"{'الشبكة':<15} | {'صيد جديد ✨':<12} | {'تحديثات 📈':<10}"
    print(table_header)
    print("-" * len(table_header))
    
    total_new = 0
    total_updates = 0
    for network, data in stats.items():
        print(f"{network:<15} | {data['new']:<12} | {data['updates']:<10}")
        total_new += data['new']
        total_updates += data['updates']
    
    print("-" * len(table_header))
    print(f"🚀 إجمالي الصيد الجديد: {total_new} إعلان")
    print(f"📈 إجمالي التحديثات: {total_updates}")
    print(f"⏱️ الوقت الإجمالي للجولة: {total_time:.2f} دقيقة")
    print("*"*60 + "\n")

if __name__ == "__main__":
    start_all = time.time()
    
    print("🚀 بدء جولة البحث الشاملة (Full Power Mode)...")
    
    scripts = [
        "revcontent_crawler.py",
        "taboola_crawler.py",
        "mgid_crawler.py",
        "outbrain_crawler.py"
    ]
    
    # اختيار 5 دول عشوائياً
    selected_countries = random.sample(TARGET_COUNTRIES, 5)
    print(f"🌐 الدول المستهدفة في هذه الدورة: {', '.join(selected_countries)}\n")
    
    for country in selected_countries:
        print(f"\n{'='*40}\n🌍 جاري المسح الشامل في: {country}\n{'='*40}")
        for script in scripts:
            # تم إزالة شرط "continue" لتفعيل جميع السكريبتات
            if os.path.exists(script):
                run_script(script, country)
            else:
                print(f"⚠️ الملف {script} غير موجود، تخطي...")

    total_duration = (time.time() - start_all) / 60
    show_dashboard(total_duration)
    
    print("🏁 انتهت العملية الشاملة بنجاح! تفقد الـ Dashboard بالأعلى.")
