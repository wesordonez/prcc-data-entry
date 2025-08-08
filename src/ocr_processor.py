"""
OCR Processor Module
Handles PDF to text conversion using Tesseract OCR
"""

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
import logging
from pathlib import Path
from typing import List, Dict, Optional
import json

class OCRProcessor:
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize OCR processor
        
        Args:
            tesseract_path: Path to tesseract executable (if not in PATH)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        self.logger = logging.getLogger(__name__)
        
        # OCR configuration for forms
        self.ocr_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,/()- '

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image
        """
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply denoising
        img_array = cv2.fastNlMeansDenoising(img_array)
        
        # Apply adaptive threshold
        img_array = cv2.adaptiveThreshold(
            img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Convert back to PIL Image
        processed_image = Image.fromarray(img_array)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(processed_image)
        processed_image = enhancer.enhance(2.0)
        
        # Apply slight blur to smooth text
        processed_image = processed_image.filter(ImageFilter.MedianFilter(size=1))
        
        return processed_image

    def extract_text_from_image(self, image: Image.Image) -> Dict[str, any]:
        """
        Extract text from image using OCR
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary containing extracted text and confidence scores
        """
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Extract text with confidence scores
            data = pytesseract.image_to_data(
                processed_image, 
                config=self.ocr_config, 
                output_type=pytesseract.Output.DICT
            )
            
            # Get raw text
            raw_text = pytesseract.image_to_string(processed_image, config=self.ocr_config)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'raw_text': raw_text.strip(),
                'word_data': data,
                'confidence': avg_confidence,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"OCR extraction failed: {str(e)}")
            return {
                'raw_text': '',
                'word_data': None,
                'confidence': 0,
                'success': False,
                'error': str(e)
            }

    def pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[Image.Image]:
        """
        Convert PDF pages to images
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for conversion
            
        Returns:
            List of PIL Images
        """
        try:
            self.logger.info(f"Converting PDF to images: {pdf_path}")
            images = convert_from_path(pdf_path, dpi=dpi)
            self.logger.info(f"Successfully converted {len(images)} pages")
            return images
        
        except Exception as e:
            self.logger.error(f"PDF conversion failed: {str(e)}")
            return []

    def process_consultation_form(self, image: Image.Image) -> Dict[str, any]:
        """
        Process a single consultation form image
        
        Args:
            image: PIL Image of the consultation form
            
        Returns:
            Dictionary with extracted form data
        """
        ocr_result = self.extract_text_from_image(image)
        
        if not ocr_result['success']:
            return {
                'success': False,
                'error': ocr_result.get('error', 'OCR failed'),
                'form_data': {}
            }
        
        # Basic text extraction successful
        return {
            'success': True,
            'raw_text': ocr_result['raw_text'],
            'confidence': ocr_result['confidence'],
            'word_data': ocr_result['word_data'],
            'form_data': {}  # Will be populated by form_parser
        }

    def process_pdf(self, pdf_path: str) -> List[Dict[str, any]]:
        """
        Process entire PDF file with consultation forms
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of processed form data dictionaries
        """
        self.logger.info(f"Starting PDF processing: {pdf_path}")
        
        # Convert PDF to images
        images = self.pdf_to_images(pdf_path)
        if not images:
            return []
        
        results = []
        for i, image in enumerate(images):
            self.logger.info(f"Processing page {i+1}/{len(images)}")
            
            # Process each page as a consultation form
            result = self.process_consultation_form(image)
            result['page_number'] = i + 1
            result['pdf_path'] = pdf_path
            
            results.append(result)
            
            # Log progress
            if result['success']:
                confidence = result.get('confidence', 0)
                self.logger.info(f"Page {i+1} processed successfully (confidence: {confidence:.1f}%)")
            else:
                self.logger.error(f"Page {i+1} failed: {result.get('error', 'Unknown error')}")
        
        self.logger.info(f"PDF processing complete. Processed {len(results)} pages")
        return results

    def save_debug_images(self, pdf_path: str, output_dir: str = "debug_images"):
        """
        Save preprocessed images for debugging OCR issues
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save debug images
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        images = self.pdf_to_images(pdf_path)
        
        for i, image in enumerate(images):
            # Save original
            original_path = output_path / f"page_{i+1}_original.png"
            image.save(original_path)
            
            # Save preprocessed
            processed = self.preprocess_image(image)
            processed_path = output_path / f"page_{i+1}_processed.png"
            processed.save(processed_path)
            
        self.logger.info(f"Debug images saved to {output_path}")


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize processor
    processor = OCRProcessor()
    
    # Test with a PDF file
    # processor.process_pdf("sample_consultation.pdf")
    
    print("OCR Processor module loaded successfully!")
    print("Install required packages with:")
    print("pip install pytesseract opencv-python pdf2image pillow numpy")