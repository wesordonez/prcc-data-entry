"""
CRM Integration Module
Handles integration with Twenty CRM via n8n workflow
"""

import requests
import logging
from typing import Dict, Any, Optional
import json
from datetime import datetime

class CRMIntegration:
    def __init__(self, n8n_webhook_url: Optional[str] = None, twenty_api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize CRM integration
        
        Args:
            n8n_webhook_url: URL of your n8n webhook endpoint
            twenty_api_url: Direct API URL for Twenty CRM (if not using n8n)
            api_key: API key for direct Twenty CRM access
        """
        self.logger = logging.getLogger(__name__)
        self.n8n_webhook_url = n8n_webhook_url
        self.twenty_api_url = twenty_api_url
        self.api_key = api_key
        
        # Set up session for requests
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

    def format_data_for_crm(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format Smartsheet form data for CRM
        
        Args:
            form_data: Structured form data
            
        Returns:
            Dictionary formatted for CRM ingestion
        """
        # Extract name parts
        first_name = form_data.get('business_owner_first_name', '')
        last_name = form_data.get('business_owner_last_name', '')
        full_name = f"{first_name} {last_name}".strip()
        
        # Format consultation date
        consultation_date = form_data.get('consultation_date', '')
        if consultation_date:
            try:
                # Parse and format date for CRM
                date_obj = datetime.strptime(consultation_date, '%m/%d/%Y')
                formatted_date = date_obj.isoformat()
            except ValueError:
                formatted_date = consultation_date
        else:
            formatted_date = datetime.now().isoformat()
        
        # Create CRM payload
        crm_data = {
            # Company/Business information
            'company': {
                'name': form_data.get('business_name', ''),
                'address': {
                    'street': form_data.get('business_street_address', ''),
                    'city': form_data.get('city', ''),
                    'state': form_data.get('state', ''),
                    'zipCode': form_data.get('zip_code', '')
                },
                'industry': self._map_business_type(form_data.get('business_presence', '')),
                'stage': form_data.get('business_stage', ''),
                'structure': form_data.get('business_structure', ''),
                'yearsInBusiness': form_data.get('years_in_business', ''),
                'employeeCount': form_data.get('employee_count', ''),
                'customFields': {
                    'businessPresence': form_data.get('business_presence', ''),
                    'serviceAreas': form_data.get('service_areas', []),
                    'referralSource': form_data.get('referral_source', ''),
                    'consultationLanguage': form_data.get('consultation_language', ''),
                    'smartsheetSubmitted': True
                }
            },
            
            # Contact/Person information
            'contact': {
                'firstName': first_name,
                'lastName': last_name,
                'fullName': full_name,
                'email': form_data.get('business_owner_email', ''),
                'phone': form_data.get('phone', ''),  # If available from OCR
                'demographics': {
                    'race': form_data.get('race', ''),
                    'ethnicity': form_data.get('ethnicity', ''),
                    'gender': form_data.get('gender', ''),
                    'isVeteran': form_data.get('is_veteran', '') == 'Yes',
                    'isDisabled': form_data.get('is_disabled', '') == 'Yes'
                }
            },
            
            # Consultation/Activity information
            'consultation': {
                'date': formatted_date,
                'duration': form_data.get('consultation_length', '1'),
                'summary': form_data.get('business_summary', ''),
                'advisor': form_data.get('submitted_by', ''),
                'program': form_data.get('program', ''),
                'type': 'Business Consultation',
                'status': 'Completed'
            },
            
            # Metadata
            'metadata': {
                'source': 'Smartsheet Automation',
                'submittedBy': form_data.get('submitted_by', ''),
                'reportingMonth': form_data.get('reporting_month', ''),
                'delegateAgency': form_data.get('delegate_agency', ''),
                'vendorId': form_data.get('vendor_id', ''),
                'processedAt': datetime.now().isoformat()
            }
        }
        
        return crm_data

    def _map_business_type(self, business_presence: str) -> str:
        """Map business presence to industry category"""
        mapping = {
            'Home based': 'Service',
            'Brick and Mortar': 'Retail',
            'E-commerce': 'Technology',
            'Brick & Mortar': 'Retail'
        }
        return mapping.get(business_presence, 'Other')

    def send_to_n8n_workflow(self, crm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send data to n8n workflow
        
        Args:
            crm_data: Formatted CRM data
            
        Returns:
            Response dictionary
        """
        if not self.n8n_webhook_url:
            return {
                'success': False,
                'error': 'n8n webhook URL not configured'
            }
        
        try:
            self.logger.info(f"Sending data to n8n workflow: {self.n8n_webhook_url}")
            
            response = self.session.post(
                self.n8n_webhook_url,
                json=crm_data,
                timeout=30
            )
            
            response.raise_for_status()
            
            response_data = response.json() if response.content else {}
            
            self.logger.info("✅ Successfully sent to n8n workflow")
            return {
                'success': True,
                'response': response_data,
                'status_code': response.status_code
            }
            
        except requests.exceptions.Timeout:
            error_msg = "Request timeout - n8n workflow may still be processing"
            self.logger.warning(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to send to n8n workflow: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def send_to_twenty_crm_direct(self, crm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send data directly to Twenty CRM API
        
        Args:
            crm_data: Formatted CRM data
            
        Returns:
            Response dictionary
        """
        if not self.twenty_api_url:
            return {
                'success': False,
                'error': 'Twenty CRM API URL not configured'
            }
        
        try:
            self.logger.info(f"Sending data directly to Twenty CRM: {self.twenty_api_url}")
            
            # Create company
            company_response = self.session.post(
                f"{self.twenty_api_url}/companies",
                json=crm_data['company'],
                timeout=30
            )
            company_response.raise_for_status()
            company_data = company_response.json()
            company_id = company_data.get('id')
            
            # Create contact
            contact_data = crm_data['contact'].copy()
            contact_data['companyId'] = company_id
            
            contact_response = self.session.post(
                f"{self.twenty_api_url}/contacts",
                json=contact_data,
                timeout=30
            )
            contact_response.raise_for_status()
            contact_data = contact_response.json()
            
            # Create consultation activity
            activity_data = crm_data['consultation'].copy()
            activity_data['companyId'] = company_id
            activity_data['contactId'] = contact_data.get('id')
            
            activity_response = self.session.post(
                f"{self.twenty_api_url}/activities",
                json=activity_data,
                timeout=30
            )
            activity_response.raise_for_status()
            
            self.logger.info("✅ Successfully created records in Twenty CRM")
            return {
                'success': True,
                'company_id': company_id,
                'contact_id': contact_data.get('id'),
                'activity_id': activity_response.json().get('id')
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to send to Twenty CRM: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def sync_consultation_data(self, form_data: Dict[str, Any], use_n8n: bool = True) -> Dict[str, Any]:
        """
        Sync consultation data to CRM
        
        Args:
            form_data: Structured form data from Smartsheet
            use_n8n: Whether to use n8n workflow or direct API
            
        Returns:
            Sync result dictionary
        """
        business_name = form_data.get('business_name', 'Unknown Business')
        self.logger.info(f"Syncing consultation data to CRM for: {business_name}")
        
        try:
            # Format data for CRM
            crm_data = self.format_data_for_crm(form_data)
            
            # Send to CRM
            if use_n8n:
                result = self.send_to_n8n_workflow(crm_data)
            else:
                result = self.send_to_twenty_crm_direct(crm_data)
            
            if result['success']:
                self.logger.info(f"✅ CRM sync successful for: {business_name}")
            else:
                self.logger.error(f"❌ CRM sync failed for {business_name}: {result.get('error')}")
            
            return {
                'business_name': business_name,
                'crm_sync_success': result['success'],
                'crm_response': result,
                'formatted_data': crm_data
            }
            
        except Exception as e:
            error_msg = f"Error syncing {business_name} to CRM: {str(e)}"
            self.logger.error(error_msg)
            return {
                'business_name': business_name,
                'crm_sync_success': False,
                'crm_response': {'error': error_msg},
                'formatted_data': None
            }

    def batch_sync(self, consultations: list[Dict[str, Any]], use_n8n: bool = True) -> list[Dict[str, Any]]:
        """
        Sync multiple consultations to CRM
        
        Args:
            consultations: List of consultation form data
            use_n8n: Whether to use n8n workflow or direct API
            
        Returns:
            List of sync results
        """
        results = []
        
        self.logger.info(f"Starting batch CRM sync for {len(consultations)} consultations")
        
        for i, consultation in enumerate(consultations):
            self.logger.info(f"Syncing consultation {i+1}/{len(consultations)}")
            
            result = self.sync_consultation_data(consultation, use_n8n)
            results.append(result)
            
            # Small delay between requests to avoid overwhelming the API
            if i < len(consultations) - 1:
                import time
                time.sleep(1)
        
        # Summary
        successful = sum(1 for r in results if r['crm_sync_success'])
        failed = len(results) - successful
        
        self.logger.info(f"📊 CRM batch sync complete: {successful} successful, {failed} failed")
        
        return results

    def test_connection(self, use_n8n: bool = True) -> Dict[str, Any]:
        """
        Test connection to CRM system
        
        Args:
            use_n8n: Whether to test n8n or direct API
            
        Returns:
            Test result dictionary
        """
        self.logger.info("Testing CRM connection...")
        
        if use_n8n:
            if not self.n8n_webhook_url:
                return {
                    'success': False,
                    'error': 'n8n webhook URL not configured'
                }
            
            try:
                # Send a test payload
                test_payload = {
                    'test': True,
                    'timestamp': datetime.now().isoformat(),
                    'message': 'Connection test from consultation automation'
                }
                
                response = self.session.post(
                    self.n8n_webhook_url,
                    json=test_payload,
                    timeout=10
                )
                
                return {
                    'success': response.status_code < 400,
                    'status_code': response.status_code,
                    'response': response.text[:200]  # First 200 chars
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
        else:
            if not self.twenty_api_url:
                return {
                    'success': False,
                    'error': 'Twenty CRM API URL not configured'
                }
            
            try:
                # Test API connection
                response = self.session.get(
                    f"{self.twenty_api_url}/health",
                    timeout=10
                )
                
                return {
                    'success': response.status_code < 400,
                    'status_code': response.status_code,
                    'response': response.text[:200]
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize CRM integration
    crm = CRMIntegration(
        n8n_webhook_url="https://your-n8n-instance.com/webhook/consultation-data"
        # Or for direct API:
        # twenty_api_url="https://your-twenty-crm.com/api/v1",
        # api_key="your-api-key"
    )
    
    # Test connection
    test_result = crm.test_connection()
    print(f"Connection test: {test_result}")
    
    # Sample consultation data
    sample_data = {
        'business_name': 'Plena Mercancia',
        'business_owner_first_name': 'Daphne',
        'business_owner_last_name': '',
        'business_owner_email': '',
        'business_street_address': '',
        'city': 'Chicago',
        'state': 'IL',
        'zip_code': '60622',
        'consultation_date': '07/08/2025',
        'consultation_length': '2',
        'consultation_language': 'Spanish',
        'business_stage': 'Growth Phase',
        'business_structure': 'LLC',
        'business_presence': 'Brick and Mortar',
        'years_in_business': '6-1',
        'employee_count': '2',
        'race': 'White',
        'ethnicity': 'Hispanic / Latino',
        'is_veteran': 'No',
        'is_disabled': 'No',
        'service_areas': ['Business Planning & Strategy'],
        'business_summary': 'Met with client to discuss upcoming events and their plans.',
        'referral_source': 'Economic Development Nonprofit',
        'submitted_by': 'wesleyo@prcc-chgo.org',
        'program': 'Place-based Business Specialist',
        'reporting_month': 'August',
        'delegate_agency': 'Puerto Rican Cultural Center (PRCC)',
        'vendor_id': '1055031'
    }
    
    # Test sync
    # sync_result = crm.sync_consultation_data(sample_data, use_n8n=True)
    # print(f"Sync result: {sync_result}")
    
    print("CRM Integration module loaded successfully!")
    print("Install required packages with:")
    print("pip install requests")