"""
Form Parser Module
Extracts structured data from OCR text using pattern matching
"""

import re
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import json

class FormParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define field patterns based on your form template
        self.field_patterns = {
            'business_name': [
                r'Business\s+Name[:\s]+([^\n\r]+)',
                r'Business\s*Name[:\s]*([^\n\r]+)'
            ],
            'dba': [
                r'DBA[:\s]+([^\n\r]+)',
                r'D\.?B\.?A\.?[:\s]*([^\n\r]+)'
            ],
            'contact_name': [
                r'Contact\s+Name[:\s]+([^\n\r]+)',
                r'Contact\s*Name[:\s]*([^\n\r]+)'
            ],
            'address': [
                r'Address[:\s]+([^\n\r]+)',
                r'Address[:\s]*([^\n\r]+)'
            ],
            'city': [
                r'City[:\s]+([^\n\r]+)',
                r'City[:\s]*([^\n\r]+)'
            ],
            'zip': [
                r'Zip[:\s]+(\d{5})',
                r'ZIP[:\s]+(\d{5})',
                r'Zip\s*Code[:\s]*(\d{5})'
            ],
            'phone': [
                r'Phone[:\s]+([^\n\r]+)',
                r'Phone[:\s]*([^\n\r]+)'
            ],
            'email': [
                r'Email[:\s]+([^\n\r]+)',
                r'E[\-\s]*mail[:\s]*([^\n\r]+)'
            ],
            'business_structure': [
                r'Business\s+Structure[:\s]+([^\n\r]+)',
                r'LLC|S[\-\s]*CORP|Corporation|Partnership|Sole\s+Proprietorship'
            ],
            'years_in_business': [
                r'Years\s+in\s+business[:\s]+([^\n\r]+)',
                r'(\d+\s*[-]\s*\d+|\d+)'
            ],
            'full_time_employees': [
                r'Full\s+time\s+employees[:\s]+([^\n\r]+)',
                r'Full[\s\-]*time\s+employees[:\s]*(\d+)'
            ],
            'session_date': [
                r'Session\s+Date[:\s]+([^\n\r]+)',
                r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})'
            ],
            'advisor': [
                r'Advisor[:\s]+([^\n\r]+)',
                r'Advisor[:\s]*([^\n\r]+)'
            ],
            'contact_time': [
                r'Contact\s+Time[:\s]+([^\n\r]+)',
                r'Contact\s*Time[:\s]*(\d+)'
            ],
            'type_of_consultation': [
                r'Type\s+of\s+Consultation[:\s]+([^\n\r]+)',
                r'operations|marketing|financing|legal|accounting'
            ]
        }
        
        # Define radio button/checkbox patterns
        self.choice_patterns = {
            'business_stage': {
                'patterns': [r'Business\s+Stage', r'(Seed|Start\s*up|Growth|Expansion|Maturity)'],
                'options': ['Seed/Idea Phase', 'Start up Phase', 'Growth Phase', 'Expansion Phase', 'Maturity/Exit Phase']
            },
            'business_presence': {
                'patterns': [r'Business\s+Presence', r'(Home\s*based|Brick\s*and\s*Mortar|E[\-\s]*commerce)'],
                'options': ['Home based', 'Brick and Mortar', 'E-commerce']
            },
            'race': {
                'patterns': [r'Race', r'(American\s*Indian|Black|Native\s*Hawaiian|Asian|White)'],
                'options': ['American Indian / Alaska Native', 'Black / African American', 'Native Hawaiian / Pacific Islander', 'Asian', 'White']
            },
            'ethnicity': {
                'patterns': [r'Ethnicity', r'(Hispanic|Latino|Other)'],
                'options': ['Hispanic / Latino', 'Other']
            },
            'language': {
                'patterns': [r'Language\s+of\s+Consultation', r'(English|Spanish)'],
                'options': ['English', 'Spanish']
            },
            'veteran': {
                'patterns': [r'Veteran', r'(Yes|No)'],
                'options': ['Yes', 'No']
            },
            'disabled': {
                'patterns': [r'Disabled', r'(Yes|No)'],
                'options': ['Yes', 'No']
            }
        }

    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Fix common OCR errors
        text = text.replace('|', 'I')  # Common OCR mistake
        text = text.replace('0', 'O')  # In names/words
        
        return text

    def extract_field_value(self, text: str, field_name: str) -> Optional[str]:
        """Extract value for a specific field using pattern matching"""
        patterns = self.field_patterns.get(field_name, [])
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                return self.clean_text(value)
        
        return None

    def extract_checkbox_selections(self, text: str, field_name: str) -> List[str]:
        """Extract checkbox/radio button selections"""
        if field_name not in self.choice_patterns:
            return []
        
        config = self.choice_patterns[field_name]
        patterns = config['patterns']
        options = config['options']
        
        selections = []
        
        # Look for X marks or checkmarks near options
        for option in options:
            # Create pattern to find option with possible selection indicator
            option_pattern = rf'[X✓✗⌧]\s*{re.escape(option)}|{re.escape(option)}\s*[X✓✗⌧]'
            if re.search(option_pattern, text, re.IGNORECASE):
                selections.append(option)
        
        return selections

    def extract_consultation_notes(self, text: str) -> str:
        """Extract the consultation notes section"""
        # Look for the notes section - usually at the bottom
        notes_patterns = [
            r'Consultation\s+Notes[:\s]+(.*?)(?=\n\s*$|\Z)',
            r'Notes[:\s]+(.*?)(?=\n\s*$|\Z)',
            r'(?:Met|Discussed|Client).*?(?=\n\s*$|\Z)'  # Fallback - look for narrative text
        ]
        
        for pattern in notes_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                notes = match.group(1).strip()
                if len(notes) > 20:  # Ensure it's substantial text
                    return self.clean_text(notes)
        
        return ""

    def parse_date(self, date_str: str) -> str:
        """Parse and normalize date string"""
        if not date_str:
            return ""
        
        # Try different date formats
        date_formats = [
            '%m/%d/%Y', '%m/%d/%y',
            '%m-%d-%Y', '%m-%d-%y',
            '%d/%m/%Y', '%d/%m/%y'
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                return parsed_date.strftime('%m/%d/%Y')
            except ValueError:
                continue
        
        # Return original if parsing fails
        return date_str.strip()

    def map_to_smartsheet_format(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map parsed data to Smartsheet form format"""
        
        # Split contact name into first/last
        contact_name = parsed_data.get('contact_name', '')
        name_parts = contact_name.split() if contact_name else []
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Map business stage
        business_stage_mapping = {
            'Seed/Idea Phase': 'Seed/Idea Phase',
            'Start up Phase': 'Start-up Phase', 
            'Growth Phase': 'Growth Phase',
            'Expansion Phase': 'Expansion Phase',
            'Maturity/Exit Phase': 'Maturity / Exit Phase'
        }
        
        business_stage = parsed_data.get('business_stage', [])
        mapped_stage = business_stage_mapping.get(business_stage[0] if business_stage else '', 'Growth Phase')
        
        return {
            # Static configuration (you'll need to set these)
            'delegate_agency': 'Puerto Rican Cultural Center (PRCC)',
            'vendor_id': '1055031',
            'program': 'Place-based Business Specialist',
            'submitted_by': 'wesleyo@prcc-chgo.org',
            'reporting_month': 'August',  # Update as needed
            
            # Business information
            'business_name': parsed_data.get('business_name', ''),
            'business_owner_first_name': first_name,
            'business_owner_last_name': last_name,
            'business_owner_email': parsed_data.get('email', ''),
            'business_street_address': parsed_data.get('address', ''),
            'city': parsed_data.get('city', 'Chicago'),
            'state': 'IL',
            'zip_code': parsed_data.get('zip', ''),
            
            # Consultation details
            'consultation_date': self.parse_date(parsed_data.get('session_date', '')),
            'consultation_length': parsed_data.get('contact_time', '1'),
            'consultation_language': parsed_data.get('language', ['English'])[0] if parsed_data.get('language') else 'English',
            
            # Business characteristics
            'business_stage': mapped_stage,
            'business_structure': parsed_data.get('business_structure', 'Limited Liability Company'),
            'business_presence': parsed_data.get('business_presence', ['Brick and Mortar'])[0] if parsed_data.get('business_presence') else 'Brick & Mortar',
            'years_in_business': parsed_data.get('years_in_business', '2 to 5 years'),
            'employee_count': f"{parsed_data.get('full_time_employees', '2')} employees",
            
            # Demographics
            'race': parsed_data.get('race', ['Prefer not to answer'])[0] if parsed_data.get('race') else 'Prefer not to answer',
            'ethnicity': parsed_data.get('ethnicity', ['Prefer not to answer'])[0] if parsed_data.get('ethnicity') else 'Prefer not to answer',
            'gender': 'Prefer not to answer',  # Not on current form
            'is_veteran': parsed_data.get('veteran', ['No'])[0] if parsed_data.get('veteran') else 'No',
            'is_disabled': parsed_data.get('disabled', ['No'])[0] if parsed_data.get('disabled') else 'No',
            
            # Service areas and summary
            'service_areas': ['Business Planning & Strategy'],  # Default based on form
            'business_summary': parsed_data.get('consultation_notes', ''),
            'referral_source': 'Economic Development Nonprofit'
        }

    def parse_form(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse OCR result into structured form data
        
        Args:
            ocr_result: Result from OCR processor
            
        Returns:
            Dictionary with parsed form data
        """
        if not ocr_result.get('success', False):
            return {
                'success': False,
                'error': 'OCR processing failed',
                'parsed_data': {}
            }
        
        raw_text = ocr_result.get('raw_text', '')
        
        try:
            # Extract basic field values
            parsed_data = {}
            
            for field_name in self.field_patterns.keys():
                value = self.extract_field_value(raw_text, field_name)
                if value:
                    parsed_data[field_name] = value
            
            # Extract checkbox/radio selections
            for field_name in self.choice_patterns.keys():
                selections = self.extract_checkbox_selections(raw_text, field_name)
                if selections:
                    parsed_data[field_name] = selections
            
            # Extract consultation notes
            notes = self.extract_consultation_notes(raw_text)
            if notes:
                parsed_data['consultation_notes'] = notes
            
            # Map to Smartsheet format
            smartsheet_data = self.map_to_smartsheet_format(parsed_data)
            
            return {
                'success': True,
                'raw_parsed_data': parsed_data,
                'smartsheet_data': smartsheet_data,
                'confidence': ocr_result.get('confidence', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Form parsing failed: {str(e)}")
            return {
                'success': False,
                'error': f"Parsing failed: {str(e)}",
                'parsed_data': {}
            }

    def validate_required_fields(self, smartsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that required fields are present"""
        required_fields = [
            'business_name',
            'business_owner_first_name',
            'consultation_date'
        ]
        
        missing_fields = []
        warnings = []
        
        for field in required_fields:
            if not smartsheet_data.get(field, '').strip():
                missing_fields.append(field)
        
        # Check for reasonable values
        if not smartsheet_data.get('consultation_length', '').strip():
            smartsheet_data['consultation_length'] = '1'  # Default
            warnings.append('Used default consultation length: 1 hour')
        
        return {
            'is_valid': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'warnings': warnings,
            'data': smartsheet_data
        }


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Test with sample OCR text
    sample_text = """
    Client Consultation Form
    
    Business Name: Plena Mercancia
    Contact Name: Daphne
    City: Chicago
    Zip: 60622
    Business Structure: LLC
    Business Stage: X Growth Phase
    Business Presence: X Brick and Mortar
    Years in business: 6-1
    Full time employees: 2
    Race: X White
    Ethnicity: X Hispanic / Latino
    Language of Consultation: X Spanish
    Session Date: 07/08/2025
    Advisor: Wesley O.
    Contact Time: 2
    
    Consultation Notes:
    Met with client to discuss upcoming events and their plans. Discussed
    some marketing ideas and ways to drive more clients to his shop.
    Needed some help researching import taxes for coffee products. Connected
    client to another business owner looking for collaboration.
    """
    
    parser = FormParser()
    
    # Simulate OCR result
    ocr_result = {
        'success': True,
        'raw_text': sample_text,
        'confidence': 85.0
    }
    
    # Parse the form
    result = parser.parse_form(ocr_result)
    
    if result['success']:
        print("✅ Parsing successful!")
        print(f"Confidence: {result['confidence']}%")
        print("\nSmartsheet Data:")
        for key, value in result['smartsheet_data'].items():
            print(f"  {key}: {value}")
    else:
        print(f"❌ Parsing failed: {result['error']}")