"""
Smartsheet Form Automation Bot
Python equivalent of your Puppeteer script using Selenium
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import logging
from typing import Dict, Any, List, Optional

class SmartsheetBot:
    def __init__(self, headless: bool = False, wait_timeout: int = 10):
        """
        Initialize Smartsheet automation bot
        
        Args:
            headless: Run browser in headless mode
            wait_timeout: Timeout for element waiting
        """
        self.logger = logging.getLogger(__name__)
        self.wait_timeout = wait_timeout
        self.driver = None
        self.wait = None
        
        # Smartsheet form URL (you'll need to update this)
        self.form_url = 'https://app.smartsheet.com/b/form/c2909a51b80e4d75a8b277f96befb11d'
        
        # Set up Chrome options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')

    def start_browser(self):
        """Initialize browser session"""
        try:
            self.logger.info("Starting browser session...")
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.wait = WebDriverWait(self.driver, self.wait_timeout)
            self.logger.info("Browser session started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start browser: {str(e)}")
            raise

    def stop_browser(self):
        """Close browser session"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Browser session closed")

    def navigate_to_form(self):
        """Navigate to Smartsheet form"""
        try:
            self.logger.info(f"Navigating to form: {self.form_url}")
            self.driver.get(self.form_url)
            
            # Wait for form to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            time.sleep(2)  # Additional wait for dynamic content
            
            self.logger.info("Form loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to navigate to form: {str(e)}")
            raise

    def find_element_by_label(self, label_text: str, input_type: str = "input") -> Optional[Any]:
        """
        Find form element by associated label text
        
        Args:
            label_text: Text content of the label
            input_type: Type of input element to find
            
        Returns:
            WebElement or None
        """
        try:
            # Method 1: Find label and get associated input via 'for' attribute
            label_xpath = f"//label[contains(text(), '{label_text}')]"
            label_elements = self.driver.find_elements(By.XPATH, label_xpath)
            
            for label in label_elements:
                for_attr = label.get_attribute('for')
                if for_attr:
                    try:
                        element = self.driver.find_element(By.ID, for_attr)
                        return element
                    except:
                        continue
            
            # Method 2: Look for input near the label
            nearby_xpath = f"//label[contains(text(), '{label_text}')]/following-sibling::{input_type}[1]"
            try:
                element = self.driver.find_element(By.XPATH, nearby_xpath)
                return element
            except:
                pass
            
            # Method 3: Look for input in parent/sibling containers
            container_xpath = f"//label[contains(text(), '{label_text}')]/parent::*//{input_type}[1]"
            try:
                element = self.driver.find_element(By.XPATH, container_xpath)
                return element
            except:
                pass
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Could not find element for label '{label_text}': {str(e)}")
            return None

    def fill_text_field(self, label_text: str, value: str) -> bool:
        """
        Fill text input field by label
        
        Args:
            label_text: Label text to search for
            value: Value to enter
            
        Returns:
            True if successful, False otherwise
        """
        if not value or not value.strip():
            return True  # Skip empty values
        
        try:
            element = self.find_element_by_label(label_text, "input")
            if not element:
                element = self.find_element_by_label(label_text, "textarea")
            
            if element:
                # Clear and fill
                element.clear()
                element.send_keys(str(value).strip())
                self.logger.debug(f"Filled '{label_text}' with '{value}'")
                return True
            else:
                self.logger.warning(f"Could not find text field for: {label_text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error filling text field '{label_text}': {str(e)}")
            return False

    def select_radio_button(self, group_label: str, option_text: str) -> bool:
        """
        Select radio button option
        
        Args:
            group_label: Label text for the radio group
            option_text: Text of the option to select
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find radio button by option text
            radio_xpath = f"//label[contains(text(), '{option_text}')]/input[@type='radio']"
            radio_elements = self.driver.find_elements(By.XPATH, radio_xpath)
            
            if radio_elements:
                radio_elements[0].click()
                self.logger.debug(f"Selected radio option '{option_text}' for '{group_label}'")
                return True
            
            # Alternative: look for radio button near group label
            alt_xpath = f"//label[contains(text(), '{group_label}')]/following::label[contains(text(), '{option_text}')]/input[@type='radio']"
            alt_elements = self.driver.find_elements(By.XPATH, alt_xpath)
            
            if alt_elements:
                alt_elements[0].click()
                self.logger.debug(f"Selected radio option '{option_text}' for '{group_label}' (alternative method)")
                return True
            
            self.logger.warning(f"Could not find radio option '{option_text}' for '{group_label}'")
            return False
            
        except Exception as e:
            self.logger.error(f"Error selecting radio button '{group_label}' = '{option_text}': {str(e)}")
            return False

    def select_checkbox(self, group_label: str, option_text: str) -> bool:
        """
        Check checkbox option
        
        Args:
            group_label: Label text for the checkbox group
            option_text: Text of the option to check
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find checkbox by option text
            checkbox_xpath = f"//label[contains(text(), '{option_text}')]/input[@type='checkbox']"
            checkbox_elements = self.driver.find_elements(By.XPATH, checkbox_xpath)
            
            if checkbox_elements:
                checkbox = checkbox_elements[0]
                if not checkbox.is_selected():
                    checkbox.click()
                self.logger.debug(f"Checked checkbox '{option_text}' for '{group_label}'")
                return True
            
            self.logger.warning(f"Could not find checkbox '{option_text}' for '{group_label}'")
            return False
            
        except Exception as e:
            self.logger.error(f"Error selecting checkbox '{group_label}' = '{option_text}': {str(e)}")
            return False

    def fill_form_data(self, form_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Fill entire form with provided data
        
        Args:
            form_data: Dictionary containing form field values
            
        Returns:
            Dictionary showing success/failure for each field
        """
        results = {}
        
        self.logger.info("Starting form filling process...")
        
        # Text fields mapping
        text_field_mappings = {
            'delegate_agency': 'Delegate Agency Name',
            'vendor_id': 'City of Chicago Vendor ID',
            'program': 'Program',
            'submitted_by': 'Submitted By',
            'reporting_month': 'Reporting Month',
            'business_name': 'Business Name',
            'business_owner_first_name': 'Business Owner First Name',
            'business_owner_last_name': 'Business Owner Last Name',
            'business_owner_email': 'Business Owner Email',
            'business_street_address': 'Business Street Address',
            'city': 'City',
            'state': 'State',
            'zip_code': 'Zip Code',
            'consultation_date': 'Consultation Date',
            'consultation_length': 'Please specify the length of the business consultation in hours',
            'consultation_language': 'Consultation Language',
            'business_summary': 'Business Consultation Summary'
        }
        
        # Fill text fields
        for field_key, label in text_field_mappings.items():
            value = form_data.get(field_key, '')
            success = self.fill_text_field(label, value)
            results[field_key] = success
            time.sleep(0.5)  # Small delay between fields
        
        # Radio button mappings
        radio_mappings = {
            'business_stage': 'Business Stage',
            'business_structure': 'Business Structure',
            'business_presence': 'Business Presence',
            'years_in_business': 'Years in Business',
            'employee_count': 'Full-time Employees',
            'race': 'Race',
            'ethnicity': 'Ethnicity',
            'gender': 'Gender',
            'is_veteran': 'Veteran',
            'is_disabled': 'Disabled',
            'referral_source': 'Business Referred To'
        }
        
        # Select radio buttons
        for field_key, label in radio_mappings.items():
            value = form_data.get(field_key, '')
            if value:
                success = self.select_radio_button(label, value)
                results[field_key] = success
                time.sleep(0.5)
        
        # Handle service areas (checkboxes)
        service_areas = form_data.get('service_areas', [])
        if service_areas:
            for service in service_areas:
                success = self.select_checkbox('Type of Business Consultation', service)
                results[f'service_area_{service}'] = success
                time.sleep(0.5)
        
        # Check "Send me a copy" if available
        try:
            copy_checkbox = self.driver.find_element(
                By.XPATH, "//label[contains(text(), 'Send me a copy')]/input[@type='checkbox']"
            )
            if not copy_checkbox.is_selected():
                copy_checkbox.click()
            results['send_copy'] = True
        except:
            results['send_copy'] = False
        
        self.logger.info("Form filling completed")
        return results

    def wait_for_manual_review(self, timeout_minutes: int = 10) -> bool:
        """
        Wait for user to manually review and submit the form
        
        Args:
            timeout_minutes: Maximum time to wait
            
        Returns:
            True if form was submitted, False if timeout
        """
        self.logger.info("Waiting for manual review and submission...")
        self.logger.info("Please review the form data and click Submit when ready")
        
        timeout_seconds = timeout_minutes * 60
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                # Check for success message
                success_indicators = [
                    "Thank you",
                    "submitted",
                    "success",
                    "received"
                ]
                
                page_text = self.driver.page_source.lower()
                if any(indicator in page_text for indicator in success_indicators):
                    self.logger.info("✅ Form submission detected!")
                    return True
                
                # Check if URL changed (navigated away from form)
                current_url = self.driver.current_url
                if 'smartsheet.com/b/form' not in current_url:
                    self.logger.info("✅ Form submission detected (URL changed)!")
                    return True
                
                time.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                self.logger.debug(f"Error during manual review wait: {str(e)}")
        
        self.logger.warning("⏰ Manual review timeout reached")
        return False

    def process_consultation(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single consultation form
        
        Args:
            form_data: Structured form data from parser
            
        Returns:
            Dictionary with processing results
        """
        business_name = form_data.get('business_name', 'Unknown Business')
        self.logger.info(f"Processing consultation for: {business_name}")
        
        try:
            # Navigate to form
            self.navigate_to_form()
            
            # Fill form data
            fill_results = self.fill_form_data(form_data)
            
            # Count successful fills
            successful_fields = sum(1 for success in fill_results.values() if success)
            total_fields = len(fill_results)
            
            self.logger.info(f"Form filled: {successful_fields}/{total_fields} fields successful")
            
            # Wait for manual review and submission
            submitted = self.wait_for_manual_review()
            
            return {
                'success': submitted,
                'business_name': business_name,
                'fields_filled': successful_fields,
                'total_fields': total_fields,
                'fill_results': fill_results,
                'submitted': submitted
            }
            
        except Exception as e:
            self.logger.error(f"Error processing consultation for {business_name}: {str(e)}")
            return {
                'success': False,
                'business_name': business_name,
                'error': str(e),
                'submitted': False
            }

    def process_batch(self, consultations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple consultations
        
        Args:
            consultations: List of consultation form data
            
        Returns:
            List of processing results
        """
        results = []
        
        self.logger.info(f"Starting batch processing of {len(consultations)} consultations")
        
        for i, consultation in enumerate(consultations):
            self.logger.info(f"\n--- Processing consultation {i+1}/{len(consultations)} ---")
            
            result = self.process_consultation(consultation)
            results.append(result)
            
            # Wait between consultations (except for the last one)
            if i < len(consultations) - 1:
                self.logger.info("⏱️ Waiting 10 seconds before next consultation...")
                time.sleep(10)
        
        # Print summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        self.logger.info(f"\n📊 === BATCH PROCESSING COMPLETE ===")
        self.logger.info(f"✅ Successful: {successful}")
        self.logger.info(f"❌ Failed: {failed}")
        
        if failed > 0:
            self.logger.info("💥 Failed consultations:")
            for result in results:
                if not result['success']:
                    business = result.get('business_name', 'Unknown')
                    error = result.get('error', 'Unknown error')
                    self.logger.info(f"   - {business}: {error}")
        
        return results


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Sample form data (matching your form structure)
    sample_data = {
        'delegate_agency': 'Puerto Rican Cultural Center (PRCC)',
        'vendor_id': '1055031',
        'program': 'Place-based Business Specialist',
        'submitted_by': 'wesleyo@prcc-chgo.org',
        'reporting_month': 'August',
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
        'business_summary': 'Met with client to discuss upcoming events and their plans. Discussed some marketing ideas and ways to drive more clients to his shop. Needed some help researching import taxes for coffee products. Connected client to another business owner looking for collaboration.',
        'referral_source': 'Economic Development Nonprofit'
    }
    
    # Initialize bot
    bot = SmartsheetBot(headless=False)  # Set to True for headless mode
    
    try:
        # Start browser
        bot.start_browser()
        
        # Process single consultation
        result = bot.process_consultation(sample_data)
        
        print(f"Processing result: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Always close browser
        bot.stop_browser()
    
    print("Smartsheet bot module loaded successfully!")
    print("Install required packages with:")
    print("pip install selenium webdriver-manager")