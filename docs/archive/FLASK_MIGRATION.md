# Flask Migration Guide

## 🎉 Your app has been refactored from Streamlit to Flask + Jinja2!

### 📁 New Structure

```
credit_disputer/
├── app.py                    # Main Flask application
├── templates/                # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── add_dispute.html
│   ├── send_batch.html
│   └── settings.html
├── static/
│   ├── css/
│   │   └── style.css        # Custom CSS
│   └── js/                   # (for future JS)
├── run_flask.sh             # Easy launcher script
├── requirements-flask.txt   # Flask dependencies
│
├── db.py                    # ✅ Unchanged
├── generator.py             # ✅ Unchanged
├── mailer.py               # ✅ Unchanged
├── tracker.py              # ✅ Unchanged
├── main.py                 # ✅ Unchanged
│
└── OLD (can archive):
    ├── dashboard.py         # Old Streamlit version
    ├── dashboard_improved.py
    └── utils/auth.py        # Now handled by Flask sessions
```

### 🚀 Quick Start

1. **Install Flask dependencies:**
   ```bash
   pip install -r requirements-flask.txt
   ```

2. **Update your .env file:**
   ```bash
   # Add this line to your .env
   FLASK_SECRET_KEY=your-secret-key-here-change-this
   ```

3. **Run the app:**
   ```bash
   ./run_flask.sh
   ```
   
   Or manually:
   ```bash
   python3 app.py
   ```

4. **Open in browser:**
   ```
   http://localhost:5000
   ```

5. **Login:**
   - Username: `admin`
   - Password: `admin123`

### ✨ What's New

#### Benefits Over Streamlit:
- ✅ **Faster**: No reloading on every interaction
- ✅ **More Control**: Traditional web app with proper routing
- ✅ **Better UX**: Smoother navigation, no widget resets
- ✅ **Production Ready**: Standard Flask deployment options
- ✅ **Mobile Friendly**: Responsive Bootstrap design
- ✅ **Charts**: Interactive Chart.js visualizations
- ✅ **Session Management**: Proper login/logout with Flask sessions

#### Features Preserved:
- ✅ Dashboard with analytics
- ✅ Add disputes
- ✅ Send batch processing
- ✅ Check status updates
- ✅ PDF downloads
- ✅ Settings page
- ✅ All backend logic unchanged

### 🔧 Configuration

Update your `.env` file:

```bash
# Lob API
LOB_API_KEY=live_ec506538504f8bd4e07a0da4edf21d61840

# Flask
FLASK_SECRET_KEY=change-this-to-a-random-secret-key

# Personal Info (optional - can be hardcoded or in DB)
FULL_NAME=Your Full Name
ADDRESS=Your Full Address
DOB=01/01/1990
SSN_LAST4=1234
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 🎨 Customization

**Styling:** Edit `static/css/style.css`

**Templates:** Edit files in `templates/` directory

**Colors:** Change CSS variables in `style.css`:
```css
:root {
    --primary-color: #2196F3;
    --success-color: #4CAF50;
    ...
}
```

### 🌐 Deployment Options

#### Local Development:
```bash
python3 app.py
```

#### Production with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### With Docker:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements-flask.txt
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

#### Systemd Service:
```ini
[Unit]
Description=Next Credit Flask App
After=network.target

[Service]
User=adamn
WorkingDirectory=/home/adamn/credit_disputer
Environment="PATH=/home/adamn/credit_disputer/.venv/bin"
ExecStart=/home/adamn/credit_disputer/.venv/bin/python3 app.py

[Install]
WantedBy=multi-user.target
```

### 📊 Features Comparison

| Feature | Streamlit | Flask |
|---------|-----------|-------|
| Speed | Slower (reruns) | ✅ Fast |
| Navigation | Limited | ✅ Full control |
| Deployment | Specialized | ✅ Standard |
| Customization | Limited | ✅ Full |
| Mobile | Basic | ✅ Responsive |
| Sessions | State-based | ✅ Proper |

### 🔄 Migration from Streamlit

Your old Streamlit files are safe. To switch back:
```bash
streamlit run dashboard.py
```

To use Flask (recommended):
```bash
./run_flask.sh
```

### 🐛 Troubleshooting

**Port already in use:**
```bash
# Change port in app.py:
app.run(debug=True, host='0.0.0.0', port=8080)
```

**Import errors:**
```bash
pip install -r requirements-flask.txt
```

**Database errors:**
```bash
python3 -c "from db import init_db; init_db()"
```

**Static files not loading:**
- Clear browser cache
- Check file paths in templates

### 📝 Next Steps

1. ✅ Test all features
2. ✅ Update personal info in settings
3. ✅ Change default password
4. ✅ Add FLASK_SECRET_KEY to .env
5. ✅ Archive old Streamlit files
6. ✅ Deploy to production (optional)

### 💡 Tips

- Use `debug=False` in production
- Set strong FLASK_SECRET_KEY
- Consider using PostgreSQL instead of SQLite for production
- Add HTTPS with nginx reverse proxy
- Set up automatic backups of disputes.db

### 🎯 Future Enhancements

Easy to add with Flask:
- REST API endpoints
- Webhook listeners for Lob callbacks
- Email notifications (SMTP)
- Multi-user support with roles
- OAuth login (Google, GitHub)
- Real-time updates with WebSockets
- File upload for bulk CSV
- Export to PDF/Excel reports

### ❓ Questions?

The backend logic is unchanged - only the frontend is different. All your existing dispute generation, mailing, and tracking code works exactly the same!

Enjoy your new Flask app! 🎉
