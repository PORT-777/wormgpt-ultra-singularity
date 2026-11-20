# OCR Text Extractor

import os
import sys
import cv2
import pytesseract
from PIL import Image
import argparse

def extract_text_from_image(image_path):
    """
    Extract text from an image using Tesseract OCR.
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        str: Extracted text from the image
    """
    try:
        # Check if the image file exists
        if not os.path.exists(image_path):
            return f"Error: Image file not found at {image_path}"
            
        # Load image using OpenCV
        img = cv2.imread(image_path)
        
        if img is None:
            return f"Error: Could not read image file {image_path}"
            
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Use pytesseract to extract text with Arabic support
        text = pytesseract.image_to_string(img_rgb, lang='ara+eng')
        
        return text.strip()
        
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='Extract text from images using OCR')
    parser.add_argument('image_path', help='Path to the image file')
    args = parser.parse_args()
    
    extracted_text = extract_text_from_image(args.image_path)
    
    if "Error" in extracted_text:
        print(extracted_text)
        sys.exit(1)
        
    print("Extracted text:")
    print("-" * 50)
    print(extracted_text)
    print("-" * 50)

if __name__ == "__main__":
    main()