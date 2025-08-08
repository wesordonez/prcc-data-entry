"""
Main Application & Web Interface
Complete consultation automation workflow orchestrator
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

# Web framework
from flask import Flask, request, render_template_string, jsonify, send_file
from werkzeug.utils import secure_filename

# Our modules
from ocr_processor import OCRProcessor
from form_parser import FormParser
from smartsheet_bot import SmartsheetBot
from crm_integration import CRMIntegration

class ConsultationAutomation:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize consultation automation system
        
        Args:
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or self._load_default_config()
        
        # Initialize components
        self.ocr_processor = OCRProcessor()
        self.form_parser = FormParser()
        self.smartsheet_bot = None
        self.crm_integration = CRMIntegration(
            n8n_webhook_url=self.config.get('n8n_webhook_url'),
            twenty_api_url=self.config.get('twenty_api_url'),
            api_key=self.config.get('twenty_api_key')
        )
        
        # Create directories
        self.upload_dir = Path("uploads")
        self.output_dir = Path("outputs")
        self.upload_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            'smartsheet_form_url': 'https://app.smartsheet.com/b/form/c2909a51b80e4d75a8b277f96befb11d',
            'delegate_agency': 'Puerto Rican Cultural Center (PRCC)',
            'vendor_id': '1055031',
            'program': 'Place-based Business Specialist',
            'submitted_by': 'wesleyo@prcc-chgo.org',
            'reporting_month': 'August',
            'n8n_webhook_url': None,  # Set your n8n webhook URL here
            'twenty_api_url': None,   # Set your Twenty CRM API URL here
            'twenty_api_key': None,   # Set your API key here
            'use_crm': True,
            'use_n8n': True
        }

    def process_pdf_file(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a single PDF file through the complete workflow
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Processing results dictionary
        """
        self.logger.info(f"Starting complete workflow for: {pdf_path}")
        
        try:
            # Step 1: OCR Processing
            self.logger.info("Step 1: OCR Processing...")
            ocr_results = self.ocr_processor.process_pdf(pdf_path)
            
            if not ocr_results:
                return {
                    'success': False,
                    'error': 'OCR processing failed - no pages processed',
                    'stage': 'ocr'
                }
            
            # Step 2: Form Parsing
            self.logger.info("Step 2: Form Parsing...")
            parsed_consultations = []
            
            for ocr_result in ocr_results:
                if ocr_result['success']:
                    parsed_result = self.form_parser.parse_form(ocr_result)
                    if parsed_result['success']:
                        # Validate required fields
                        validated = self.form_parser.validate_required_fields(
                            parsed_result['smartsheet_data']
                        )
                        parsed_result['validation'] = validated
                        parsed_consultations.append(parsed_result)
                    else:
                        self.logger.warning(f"Form parsing failed for page {ocr_result.get('page_number')}")
                else:
                    self.logger.warning(f"OCR failed for page {ocr_result.get('page_number')}")
            
            if not parsed_consultations:
                return {
                    'success': False,
                    'error': 'No consultations could be parsed successfully',
                    'stage': 'parsing'
                }
            
            # Save parsed data for review
            output_file = self.output_dir / f"parsed_consultations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(parsed_consultations, f, indent=2, default=str)
            
            self.logger.info(f"Parsed data saved to: {output_file}")
            
            return {
                'success': True,
                'consultations': parsed_consultations,
                'total_consultations': len(parsed_consultations),
                'output_file': str(output_file),
                'stage': 'parsing_complete'
            }
            
        except Exception as e:
            self.logger.error(f"Error in PDF processing: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stage': 'error'
            }

    def process_smartsheet_submissions(self, consultations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process consultations through Smartsheet automation
        
        Args:
            consultations: List of parsed consultation data
            
        Returns:
            List of Smartsheet submission results
        """
        self.logger.info(f"Step 3: Smartsheet Automation for {len(consultations)} consultations...")
        
        # Initialize Smartsheet bot
        self.smartsheet_bot = SmartsheetBot(
            headless=False  # Keep visible for manual review
        )
        
        try:
            self.smartsheet_bot.start_browser()
            
            # Process each consultation
            smartsheet_results = []
            
            for consultation in consultations:
                smartsheet_data = consultation['smartsheet_data']
                validation = consultation.get('validation', {})
                
                # Check if validation passed
                if not validation.get('is_valid', True):
                    self.logger.warning(
                        f"Skipping consultation with missing required fields: "
                        f"{validation.get('missing_fields', [])}"
                    )
                    smartsheet_results.append({
                        'success': False,
                        'business_name': smartsheet_data.get('business_name', 'Unknown'),
                        'error': f"Missing required fields: {validation.get('missing_fields', [])}",
                        'skipped': True
                    })
                    continue
                
                # Process with Smartsheet bot
                result = self.smartsheet_bot.process_consultation(smartsheet_data)
                smartsheet_results.append(result)
            
            return smartsheet_results
            
        finally:
            if self.smartsheet_bot:
                self.smartsheet_bot.stop_browser()

    def process_crm_integration(self, consultations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process CRM integration for successful Smartsheet submissions
        
        Args:
            consultations: List of parsed consultation data
            
        Returns:
            List of CRM integration results
        """
        if not self.config.get('use_crm', False):
            self.logger.info("CRM integration disabled in configuration")
            return []
        
        self.logger.info("Step 4: CRM Integration...")
        
        # Extract smartsheet data for CRM
        crm_data_list = []
        for consultation in consultations:
            if consultation.get('smartsheet_data'):
                crm_data_list.append(consultation['smartsheet_data'])
        
        if not crm_data_list:
            self.logger.warning("No consultation data available for CRM integration")
            return []
        
        # Process CRM integration
        crm_results = self.crm_integration.batch_sync(
            crm_data_list, 
            use_n8n=self.config.get('use_n8n', True)
        )
        
        return crm_results

    def run_complete_workflow(self, pdf_path: str) -> Dict[str, Any]:
        """
        Run the complete automation workflow
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Complete workflow results
        """
        self.logger.info(f"🚀 Starting complete automation workflow for: {pdf_path}")
        
        # Step 1 & 2: OCR + Parsing
        parsing_result = self.process_pdf_file(pdf_path)
        
        if not parsing_result['success']:
            return parsing_result
        
        consultations = parsing_result['consultations']
        
        # Step 3: Smartsheet automation
        smartsheet_results = self.process_smartsheet_submissions(consultations)
        
        # Step 4: CRM integration (only for successful Smartsheet submissions)
        crm_results = []
        if self.config.get('use_crm', False):
            successful_consultations = [
                consultation for consultation, result in zip(consultations, smartsheet_results)
                if result.get('success', False)
            ]
            
            if successful_consultations:
                crm_results = self.process_crm_integration(successful_consultations)
        
        # Compile final results
        final_result = {
            'success': True,
            'pdf_file': pdf_path,
            'total_pages': len(consultations),
            'parsing_results': parsing_result,
            'smartsheet_results': smartsheet_results,
            'crm_results': crm_results,
            'summary': self._generate_summary(smartsheet_results, crm_results)
        }
        
        # Save complete results
        results_file = self.output_dir / f"workflow_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(final_result, f, indent=2, default=str)
        
        self.logger.info(f"Complete workflow results saved to: {results_file}")
        
        return final_result

    def _generate_summary(self, smartsheet_results: List[Dict], crm_results: List[Dict]) -> Dict[str, Any]:
        """Generate workflow summary"""
        smartsheet_success = sum(1 for r in smartsheet_results if r.get('success', False))
        smartsheet_total = len(smartsheet_results)
        
        crm_success = sum(1 for r in crm_results if r.get('crm_sync_success', False))
        crm_total = len(crm_results)
        
        return {
            'smartsheet': {
                'successful': smartsheet_success,
                'total': smartsheet_total,
                'success_rate': f"{(smartsheet_success/smartsheet_total*100):.1f}%" if smartsheet_total > 0 else "0%"
            },
            'crm': {
                'successful': crm_success,
                'total': crm_total,
                'success_rate': f"{(crm_success/crm_total*100):.1f}%" if crm_total > 0 else "0%"
            }
        }


# Flask Web Interface
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Global automation instance
automation = None

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consultation Form Automation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .upload-area { border: 2px dashed #ddd; padding: 40px; text-align: center; border-radius: 10px; margin: 20px 0; }
        .upload-area.dragover { border-color: #007bff; background-color: #f8f9fa; }
        .btn { background-color: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .btn:hover { background-color: #0056b3; }
        .btn:disabled { background-color: #ccc; cursor: not-allowed; }
        .progress { margin: 20px 0; }
        .progress-bar { width: 100%; height: 20px; background-color: #e9ecef; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background-color: #007bff; width: 0%; transition: width 0.3s; }
        .results { margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 5px; }
        .log { background-color: #000; color: #0f0; padding: 15px; border-radius: 5px; height: 200px; overflow-y: scroll; font-family: monospace; font-size: 12px; }
        .hidden { display: none; }
        .status-success { color: #28a745; }
        .status-error { color: #dc3545; }
        .status-warning { color: #ffc107; }
        .config-section { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .config-input { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Consultation Form Automation</h1>
            <p>Upload scanned consultation forms (PDF) for automated processing</p>
        </div>

        <!-- Configuration Section -->
        <div class="config-section">
            <h3>Configuration</h3>
            <label>Reporting Month:</label>
            <input type="text" id="reportingMonth" class="config-input" value="August" />
            
            <label>CRM Integration:</label>
            <select id="useCrm" class="config-input">
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
            </select>
            
            <label>n8n Webhook URL (optional):</label>
            <input type="url" id="n8nWebhook" class="config-input" placeholder="https://your-n8n.com/webhook/consultation" />
        </div>

        <!-- Upload Section -->
        <div class="upload-area" id="uploadArea">
            <p>📄 Drop your PDF file here or click to select</p>
            <input type="file" id="fileInput" accept=".pdf" style="display: none;" />
            <button class="btn" onclick="document.getElementById('fileInput').click()">Select PDF File</button>
        </div>

        <!-- Progress Section -->
        <div class="progress hidden" id="progressSection">
            <h3>Processing Progress</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <p id="progressText">Initializing...</p>
        </div>

        <!-- Log Section -->
        <div class="hidden" id="logSection">
            <h3>Processing Log</h3>
            <div class="log" id="logContainer"></div>
        </div>

        <!-- Results Section -->
        <div class="results hidden" id="resultsSection">
            <h3>Results</h3>
            <div id="resultsContent"></div>
        </div>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        const progressSection = document.getElementById('progressSection');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const logSection = document.getElementById('logSection');
        const logContainer = document.getElementById('logContainer');
        const resultsSection = document.getElementById('resultsSection');
        const resultsContent = document.getElementById('resultsContent');

        // Drag and drop functionality
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'application/pdf') {
                processFile(files[0]);
            } else {
                alert('Please select a PDF file');
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                processFile(e.target.files[0]);
            }
        });

        function updateProgress(percent, text) {
            progressFill.style.width = percent + '%';
            progressText.textContent = text;
        }

        function addLog(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.innerHTML = `[${timestamp}] ${message}`;
            if (type === 'error') logEntry.style.color = '#ff6b6b';
            if (type === 'success') logEntry.style.color = '#51cf66';
            if (type === 'warning') logEntry.style.color = '#ffd43b';
            
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        function processFile(file) {
            // Show progress and log sections
            progressSection.classList.remove('hidden');
            logSection.classList.remove('hidden');
            resultsSection.classList.add('hidden');
            
            // Get configuration
            const config = {
                reporting_month: document.getElementById('reportingMonth').value,
                use_crm: document.getElementById('useCrm').value === 'true',
                n8n_webhook_url: document.getElementById('n8nWebhook').value
            };

            // Create form data
            const formData = new FormData();
            formData.append('file', file);
            formData.append('config', JSON.stringify(config));

            updateProgress(10, 'Uploading file...');
            addLog('Starting consultation form processing...', 'info');

            // Upload and process
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateProgress(100, 'Processing complete!');
                    addLog('✅ Processing completed successfully', 'success');
                    displayResults(data);
                } else {
                    updateProgress(0, 'Processing failed');
                    addLog('❌ Processing failed: ' + data.error, 'error');
                }
            })
            .catch(error => {
                updateProgress(0, 'Error occurred');
                addLog('❌ Error: ' + error.message, 'error');
            });

            // Simulate progress updates (replace with actual progress tracking)
            setTimeout(() => updateProgress(30, 'OCR processing...'), 1000);
            setTimeout(() => updateProgress(50, 'Parsing forms...'), 3000);
            setTimeout(() => updateProgress(70, 'Filling Smartsheet forms...'), 5000);
            setTimeout(() => updateProgress(90, 'CRM integration...'), 8000);
        }

        function displayResults(data) {
            const summary = data.summary;
            
            let html = `
                <h4>Processing Summary</h4>
                <p><strong>Total Consultations:</strong> ${data.total_pages}</p>
                
                <h5>Smartsheet Automation:</h5>
                <p class="${summary.smartsheet.successful === summary.smartsheet.total ? 'status-success' : 'status-warning'}">
                    ✓ ${summary.smartsheet.successful}/${summary.smartsheet.total} successful (${summary.smartsheet.success_rate})
                </p>
            `;
            
            if (summary.crm && summary.crm.total > 0) {
                html += `
                    <h5>CRM Integration:</h5>
                    <p class="${summary.crm.successful === summary.crm.total ? 'status-success' : 'status-warning'}">
                        ✓ ${summary.crm.successful}/${summary.crm.total} successful (${summary.crm.success_rate})
                    </p>
                `;
            }
            
            html += `
                <h5>Output Files:</h5>
                <p>📁 Parsed data: <code>${data.parsing_results.output_file}</code></p>
                <p>📁 Complete results: Available in outputs/ directory</p>
            `;
            
            resultsContent.innerHTML = html;
            resultsSection.classList.remove('hidden');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    global automation
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Only PDF files are allowed'})
    
    try:
        # Get configuration from request
        config_data = json.loads(request.form.get('config', '{}'))
        
        # Initialize automation with updated config
        config = automation.config.copy()
        config.update(config_data)
        automation.config = config
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        file_path = automation.upload_dir / safe_filename
        file.save(file_path)
        
        # Process the file
        result = automation.run_complete_workflow(str(file_path))
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Upload processing error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

def main():
    """Main entry point"""
    global automation
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('consultation_automation.log')
        ]
    )
    
    # Initialize automation system
    automation = ConsultationAutomation()
    
    # Test components
    automation.logger.info("Testing system components...")
    
    # Test CRM connection if configured
    if automation.config.get('n8n_webhook_url') or automation.config.get('twenty_api_url'):
        crm_test = automation.crm_integration.test_connection(
            use_n8n=automation.config.get('use_n8n', True)
        )
        if crm_test['success']:
            automation.logger.info("✅ CRM connection test successful")
        else:
            automation.logger.warning(f"⚠️ CRM connection test failed: {crm_test.get('error')}")
    
    automation.logger.info("🚀 Consultation automation system ready!")
    automation.logger.info("📂 Upload directory: uploads/")
    automation.logger.info("📂 Output directory: outputs/")
    
    # Start web interface
    print("\n🌐 Starting web interface...")
    print("📡 Access the application at: http://localhost:5000")
    print("📋 Upload PDF files with consultation forms for automated processing")
    print("\n⚠️ Make sure to:")
    print("   - Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
    print("   - Install Chrome browser for Selenium")
    print("   - Configure your n8n webhook URL if using CRM integration")
    print("\n🛑 Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=8000)

if __name__ == "__main__":
    main()