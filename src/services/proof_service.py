"""
Service to provide validation of HTS codes with pdf-proof
"""
import fitz  # PyMuPDF
from pdf2image import convert_from_path

class ProofService:
    def __init__(self, hts_code: str):
        """Initialize the ProofService."""
        self.pdf_path = "Data/pdfs"
        self.images = None
        self.hts_code = hts_code
        self.code_parts = hts_code.split('.')
        self.page = 0


    def find_hts_code_page(self, desc_snippet=None):
        """
        Preconditon: hts_code is a valid HTS code in the format specified
        """
        found_pages = []

        # Normalize code format for search
        hts_code = self.hts_code.strip()
        code_parts = self.code_parts
        if len(code_parts) == 4:
            # e.g., '8539.22.80.00' => '8539.22.80'
            # since the last part is often a subheading, we can search without it
            search_code = f"{code_parts[0]}.{code_parts[1]}.{code_parts[2]}"
        elif len(code_parts) == 3:
            search_code = hts_code
        else:
            search_code = hts_code  # fallback

        search_path = f"{self.pdf_path}/Chapter {code_parts[0][:2]}.pdf"
        doc = fitz.open(search_path)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            # Search by exact HTS code
            if search_code in text:
                self.page = page_num + 1
                return self.page
        # Return most likely page (fallback if description not found)
        if found_pages:
            return found_pages[0][0]

        # Code not found
        return None

    # def convert_pdf_to_images(self, page_num):
    #     """
    #     Convert PDF pages to images.
    #     """
    #     images = convert_from_path(self.pdf_path, first_page=page_num, last_page=page_num)
    #     self.images = images
    #     return images
    
    def convert_pdf_to_images(self, page_num):
        """
        Convert PDF pages to images using PyMuPDF directly.
        """
        import io
        from PIL import Image
        
        search_path = f"{self.pdf_path}/Chapter {self.code_parts[0][:2]}.pdf"
        doc = fitz.open(search_path)
        page = doc.load_page(page_num - 1)  # 0-based index
        
        # Higher zoom = higher resolution
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.images = [img]
        return self.images

if __name__ == "__main__":
    hts_code = "1211.90.89"
    proof_handler = ProofService(hts_code)
    page = proof_handler.find_hts_code_page(hts_code)
    images = proof_handler.convert_pdf_to_images(page)
    if images:
        print(f"Converted page {page} to image successfully.")
    else:
        print("No images found for the specified page.")

    print(proof_handler.images[0].size)  # Print size of the first image
    print(f"Found on page: {page}")