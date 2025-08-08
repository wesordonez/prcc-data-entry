# PRCC Automated Business Consultation Data Entry

# Requirements.txt
flask==2.3.3
selenium==4.15.2
webdriver-manager==4.0.1
pytesseract==0.3.10
opencv-python==4.8.1.78
pdf2image==1.16.3
pillow==10.0.1
numpy==1.25.2
requests==2.31.0

---

# Setup Instructions

## 📋 Prerequisites

### 1. Install Python 3.8+
Download from https://python.org

### 2. Configure CRM Integration (Optional)

**Option A: Using n8n Workflow (Recommended)**
1. Set up your n8n workflow for Twenty CRM integration
2. Get the webhook URL from n8n
3. Update configuration in `main_app.py`:
```python
'n8n_webhook_url': 'https://your-n8n-instance.com/webhook/consultation-data'
```

**Option B: Direct Twenty CRM API**
Update configuration in `main_app.py`:
```python
'twenty_api_url': 'https://your-twenty-crm.com/api/v1',
'twenty_api_key': 'your-api-key-here'
```

### 3. Update Static Configuration
Edit the configuration in `main_app.py`:
```python
def _load_default_config(self) -> Dict[str, Any]:
    return {
        'delegate_agency': 'Your Organization Name',
        'vendor_id': 'YOUR_VENDOR_ID',
        'program': 'Your Program Name',
        'submitted_by': 'your-email@organization.com',
        'reporting_month': 'Current Month',
        # ... other settings
    }
```

## 🏃‍♂️ Running the Application

### 1. Start the Web Interface
```bash
python main_app.py
```

### 2. Access the Application
Open your browser and go to: http://localhost:8000

### 3. Upload PDF Files
- Drag and drop PDF files with consultation forms
- Or click "Select PDF File" to choose files
- Configure settings (reporting month, CRM integration)
- Click process and wait for automation

## 📁 Project Structure
```
consultation_automation/
├── src/
│   ├── ocr_processor.py          # OCR processing logic
│   ├── form_parser.py            # Form data parsing
│   ├── smartsheet_bot.py         # Smartsheet automation
│   ├── crm_integration.py        # CRM integration
│   └── main_app.py               # Web interface & orchestrator
├── uploads/                      # Uploaded PDF files
├── outputs/                      # Processed results (JSON)
├── debug_images/                 # OCR debug images (optional)
├── requirements.txt              # Python dependencies
├── consultation_automation.log   # Application logs
└── README.md                     # This file
```

## 🔄 Workflow Process

1. **Upload PDF**: User uploads scanned consultation forms
2. **OCR Processing**: Extract text from each page using Tesseract
3. **Form Parsing**: Parse OCR text into structured data
4. **Data Validation**: Check for required fields, show warnings
5. **Manual Review**: User reviews parsed data in browser
6. **Smartsheet Automation**: Fill and submit Smartsheet forms
7. **CRM Integration**: Sync data to Twenty CRM via n8n or API
8. **Results**: Show success/failure summary

## 🐛 Troubleshooting

### Common Issues

**1. Tesseract not found**
```
Error: TesseractNotFoundError
```
- Ensure Tesseract is installed and in PATH
- Windows users: Add C:\Program Files\Tesseract-OCR to PATH

**2. PDF conversion fails**
```
Error: pdf2image conversion failed
```
- Install Poppler utilities
- Check PDF file is not corrupted

**3. ChromeDriver issues**
```
Error: WebDriver executable not found
```
- Install Chrome browser
- webdriver-manager should auto-download driver
- Manually download ChromeDriver if needed

**4. OCR accuracy issues**
- Check debug images in debug_images/ folder
- Ensure forms are scanned at 300 DPI or higher
- Forms should be straight and well-lit
- Consider image preprocessing adjustments

**5. Smartsheet form filling fails**
- Update field selectors in smartsheet_bot.py
- Check form URL is correct
- Verify form structure hasn't changed

### Debug Mode

**Enable debug logging:**
```python
logging.basicConfig(level=logging.DEBUG)
```

**Save debug images:**
```python
processor.save_debug_images("path/to/pdf", "debug_images")
```

**Test individual components:**
```bash
# Test OCR only
python ocr_processor.py

# Test form parsing only
python form_parser.py

# Test Smartsheet bot only
python smartsheet_bot.py
```

## 📊 Performance Tips

### OCR Optimization
- Scan forms at 300 DPI
- Use high contrast (black text on white)
- Ensure forms are straight and clear
- Consider scanning in grayscale

### Batch Processing
- Process multiple forms in single PDF
- Use batch size limits for large files
- Monitor memory usage for large documents

### Form Accuracy
- Review parsed data before Smartsheet submission
- Use validation warnings to catch missing fields
- Keep form templates consistent

## 🔐 Security Considerations

- Store API keys in environment variables
- Don't commit sensitive configuration
- Regularly rotate API keys
- Monitor access logs
- Use HTTPS in production

## 🚀 Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    chromium \
    chromium-driver

# Copy application
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

# Run application
CMD ["python", "main_app.py"]
```

### Environment Variables
```bash
export SMARTSHEET_FORM_URL="your-form-url"
export N8N_WEBHOOK_URL="your-webhook-url"
export TWENTY_API_KEY="your-api-key"
```

## 📞 Support

### Logs
Check `consultation_automation.log` for detailed error messages

### Debug Images
Review preprocessed images in `debug_images/` folder to troubleshoot OCR issues

### Output Files
- Parsed data: `outputs/parsed_consultations_*.json`
- Complete results: `outputs/workflow_results_*.json`

## 🔄 Updates and Maintenance

### Updating Form Parsers
When consultation forms change:
1. Update field patterns in `form_parser.py`
2. Update Smartsheet field mappings in `smartsheet_bot.py`
3. Test with sample forms

### Monitoring
- Check logs regularly for errors
- Monitor OCR accuracy rates
- Verify Smartsheet submissions
- Test CRM integration periodically

## 📈 Future Enhancements

- **AI-powered parsing**: Add LangChain/LLM integration
- **Mobile app**: Create mobile interface for scanning
- **Batch validation**: Bulk data validation interface
- **Analytics dashboard**: Processing statistics and trends
- **Form templates**: Support for different form types
- **Cloud deployment**: AWS/Azure deployment options

---

## 📝 License

This project is for internal use by Puerto Rican Cultural Center (PRCC).

---

*Last updated: August 2025* Install Tesseract OCR

**Windows:**
1. Download installer from https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location (C:\Program Files\Tesseract-OCR)
3. Add to PATH environment variable

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr
sudo apt install libtesseract-dev
```

### 3. Install Chrome Browser
Download from https://chrome.google.com

### 4. Install Poppler (for PDF processing)

**Windows:**
1. Download from https://github.com/oschwartz10612/poppler-windows/releases
2. Extract and add bin folder to PATH

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt install poppler-utils
```

## 🚀 Installation Steps

### 1. Clone/Download the Project
```bash
git clone <repository-url>
cd consultation_automation
```

### 2. Create Virtual Environment
```bash
python -m venv consultation_env
# Windows:
consultation_env\Scripts\activate
# macOS/Linux:
source consultation_env/bin/activate
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download ChromeDriver (automatic)
The webdriver-manager package will automatically download ChromeDriver on first run.

### 5. Create Directory Structure
```bash
mkdir uploads
mkdir outputs
mkdir debug_images
```

## ⚙️ Configuration

### 1. Update Smartsheet Form URL
Edit the `smartsheet_bot.py` file and update the form URL:
```python
self.form_url = 'YOUR_ACTUAL_SMARTSHEET_FORM_URL'
```

### 2.