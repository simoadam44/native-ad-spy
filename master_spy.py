import subprocess
import time
import os

# قاموس لتخزين الإحصائيات (يمكنك تطويره ليرتبط بقاعدة البيانات لاحقاً)
stats = {
    "REVCONTENT": {"new": 0, "updates": 0},
    "TABOOLA": {"new": 0, "updates": 0},
    "MGID": {"new": 0, "updates": 0},
    "OUTBRAIN": {"new": 0, "updates": 0}
}

def run_script(script_name):
    start_time = time.time()
    print(f"📡 جاري إطلاق: {script_name}...")
    try:
        # تشغيل السكربت والتقاط المخرجات لتحليل الإحصائيات
        process = subprocess.Popen(['python', script_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        for line in process.stdout:
            print(line, end='') # عرض المخرجات في الوقت الحقيقي
            
            # تحليل السطور لتحديث الإحصائيات
            if "صيد جديد" in line:
                for network in stats:
                    if f"[{network}]" in line: stats[network]["new"] += 1
            elif "تحديث" in line:
                for network in stats:
                    if f"[{network}]" in line: stats[network]["updates"] += 1

        process.wait()
        duration = (time.time() - start_time) / 60
        print(f"✅ اكتملت مهمة {script_name} في {duration:.2f} دقيقة.\n")
        return duration
    except Exception as e:
        print(f"❌ خطأ في تشغيل {script_name}: {e}")
        return 0

def show_dashboard(total_time):
    print("\n" + "*"*50)
    print("📊 ملخص جولة التجسس الاحترافية 📊")
    print("*"*50)
    
    table_header = f"{'الشبكة':<15} | {'صيد جديد ✨':<12} | {'تحديثات 📈':<10}"
    print(table_header)
    print("-" * len(table_header))
    
    total_new = 0
    for network, data in stats.items():
        print(f"{network:<15} | {data['new']:<12} | {data['updates']:<10}")
        total_new += data['new']
    
    print("-" * len(table_header))
    print(f"🚀 إجمالي الصيد الجديد: {total_new} إعلان")
    print(f"⏱️ الوقت الإجمالي: {total_time:.2f} دقيقة")
    print("*"*50 + "\n")

if __name__ == "__main__":
    start_all = time.time()
    
    print("🚀 بدء جولة البحث عن أهداف جديدة (Stealth Mode Enabled)...")
    
    # ترتيب التشغيل (يمكنك تغيير الترتيب حسب الأهمية)
    scripts = [
        "revcontent_crawler.py",
        "taboola_crawler.py",
        "mgid_crawler.py",
        "outbrain_crawler.py"
    ]
    
    for script in scripts:
        if os.path.exists(script):
            run_script(script)
        else:
            print(f"⚠️ الملف {script} غير موجود، تخطي...")

    total_duration = (time.time() - start_all) / 60
    
    # عرض اللوحة النهائية
    show_dashboard(total_duration)
    
    print("🏁 انتهت العملية الشاملة بنجاح!")
