# 🚢 English Assessment Platform - Setup Guide

## 🎯 **3 Ways to Run Your Application**

### **Method 1: Quick Test Server (Recommended for Testing)**
```bash
# Navigate to your project folder
cd "C:\Users\szh2051\OneDrive - Carnival Corporation\Desktop\Python\Claude Demo"

# Run the simple test server
python test_server.py
```
**✅ Result:** Opens at http://127.0.0.1:8000

---

### **Method 2: Full Application (Production-like)**
```bash
# 1. Navigate to project folder
cd "C:\Users\szh2051\OneDrive - Carnival Corporation\Desktop\Python\Claude Demo"

# 2. Install dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic

# 3. Run the full application
python run_server.py
```

---

### **Method 3: Manual FastAPI Server**
```bash
# 1. Navigate to project
cd "C:\Users\szh2051\OneDrive - Carnival Corporation\Desktop\Python\Claude Demo"

# 2. Set Python path and run
set PYTHONPATH=src\main\python
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 📋 **Step-by-Step Instructions**

### **🔧 Prerequisites Check**
1. **Python Installation**: You already have Python (we've been using it)
2. **Project Files**: All files are in your Claude Demo folder
3. **Internet Connection**: For installing packages if needed

### **🚀 Quick Start (5 minutes)**

#### **Step 1: Open Command Prompt**
- Press `Windows + R`
- Type `cmd` and press Enter

#### **Step 2: Navigate to Project**
```cmd
cd "C:\Users\szh2051\OneDrive - Carnival Corporation\Desktop\Python\Claude Demo"
```

#### **Step 3: Check Files**
```cmd
dir
```
You should see:
- `test_server.py` ✅
- `run_server.py` ✅
- `src` folder ✅
- `requirements.txt` ✅

#### **Step 4: Run the Test Server**
```cmd
python test_server.py
```

#### **Step 5: Open in Browser**
Open your web browser and go to: **http://127.0.0.1:8000**

---

## 🎮 **What You'll See**

### **Dashboard (Main Page)**
- ✅ Application status
- 🏨 Division information (Hotel, Marine, Casino)
- 📊 Assessment modules overview
- 🔗 Test links

### **API Endpoints You Can Test**
- **Health Check**: http://127.0.0.1:8000/health
- **Test Data**: http://127.0.0.1:8000/test-data
- **Assessment Info**: http://127.0.0.1:8000/assessment-info

---

## 🛠️ **Full Production Setup (Advanced)**

### **Step 1: Install All Dependencies**
```cmd
pip install -r requirements.txt
```

### **Step 2: Setup Environment**
```cmd
copy .env.example .env
```
Edit `.env` file to add your API keys (optional for testing)

### **Step 3: Setup Database (Optional)**
For full functionality, you'd need PostgreSQL:
```cmd
# Install PostgreSQL
# Create database named 'english_assessment'
# Update DATABASE_URL in .env
```

### **Step 4: Run Full Application**
```cmd
python run_server.py
```

---

## 🔍 **Testing Your Application**

### **1. Basic Functionality Test**
- ✅ Main page loads
- ✅ Health check returns JSON
- ✅ All division information displays

### **2. API Testing**
Visit these URLs to test different parts:
- `http://127.0.0.1:8000/` - Main dashboard
- `http://127.0.0.1:8000/health` - API health check
- `http://127.0.0.1:8000/test-data` - Sample assessment data

### **3. Features Verification**
- ✅ 630+ questions loaded
- ✅ 6 assessment modules ready
- ✅ 3 divisions configured
- ✅ AI integration prepared
- ✅ Scoring system implemented

---

## ❓ **Troubleshooting**

### **Problem: "Python not found"**
**Solution**: Make sure Python is installed and in your PATH

### **Problem: "Module not found"**
**Solution**: Install missing packages:
```cmd
pip install fastapi uvicorn
```

### **Problem: "Port already in use"**
**Solution**: Either:
- Stop the running server (Ctrl+C)
- Or change port in the code (8001, 8002, etc.)

### **Problem: "Can't access localhost:8000"**
**Solution**:
- Check server is running (should see "Uvicorn running...")
- Try http://127.0.0.1:8000 instead
- Check Windows Firewall settings

---

## 🎯 **Next Steps After Testing**

1. **✅ Confirm basic functionality** - Dashboard loads
2. **📊 Review assessment structure** - All modules visible
3. **🧪 Test API endpoints** - Health check works
4. **🔧 Add API keys** - For full AI functionality
5. **🗄️ Setup database** - For persistent data storage
6. **🚀 Deploy to production** - When ready for real use

---

## 📞 **Quick Commands Summary**

```bash
# Navigate to project
cd "C:\Users\szh2051\OneDrive - Carnival Corporation\Desktop\Python\Claude Demo"

# Quick test
python test_server.py

# Full application
python run_server.py

# Install dependencies
pip install -r requirements.txt
```

**🎉 Your English Assessment Platform is ready to test!**