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
    
    def convert_pdf_to_images(self, page_num, highlight_text=None):
        """
        Convert PDF pages to images using PyMuPDF directly and highlight the specified text.
        Also highlight the subheading to the RIGHT of the main code or BELOW it.
        
        Args:
            page_num: Page number to convert
            highlight_text: Text to highlight (defaults to the HTS code if None)
        
        Returns:
            List containing the PIL Image with highlighted text
        """
        import io
        from PIL import Image, ImageDraw
        
        # Use the search code by default if no highlight text is provided
        if highlight_text is None:
            code_parts = self.code_parts
            if len(code_parts) == 4:
                highlight_text = f"{code_parts[0]}.{code_parts[1]}.{code_parts[2]}"
            elif len(code_parts) == 3:
                highlight_text = self.hts_code
            else:
                highlight_text = self.hts_code

        search_path = f"{self.pdf_path}/Chapter {self.code_parts[0][:2]}.pdf"
        doc = fitz.open(search_path)
        page = doc.load_page(page_num - 1)  # 0-based index
        
        # Higher zoom = higher resolution
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        
        # Search for text and get rectangles for main HTS code
        text_instances = page.search_for(highlight_text)
        
        # Look for the subheading code_parts[3] if it exists and has length > 0
        subheading_instances = []
        if len(self.code_parts) == 4 and self.code_parts[3]:
            subheading = self.code_parts[3]
            
            if text_instances:
                # Get the main code instance coordinates
                main_instance = text_instances[0]  # Use the first instance found
                right_x = main_instance[2]  # Right x-coordinate
                top_y = main_instance[1]    # Top y-coordinate
                bottom_y = main_instance[3] # Bottom y-coordinate
                
                # Search for the subheading in the whole document
                all_subheadings = page.search_for(subheading)
                
                # Filter to find only instances that are:
                # 1. To the right of the main code
                # 2. Either on the same row OR below the main code on the page
                vertical_tolerance = (bottom_y - top_y) * 2  # For determining "same row"
                
                subheading_instances = [
                    inst for inst in all_subheadings 
                    if inst[0] > right_x and  # To the right of the main code
                       (
                           # Same row (approximately)
                           abs((inst[1] + inst[3])/2 - (top_y + bottom_y)/2) < vertical_tolerance or
                           # OR below the main code
                           inst[1] >= bottom_y
                       )
                ]
                
                # Sort by vertical position to prioritize instances on the same row
                if subheading_instances:
                    subheading_instances.sort(key=lambda inst: abs((inst[1] + inst[3])/2 - (top_y + bottom_y)/2))
    
        # Create pixmap (image)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Create a transparent overlay for highlighting
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # If text instances found, highlight them
        if text_instances:
            # Draw yellow semi-transparent highlight around each main code instance
            for inst in text_instances:
                # Scale the coordinates according to zoom factor
                rect = [coord * zoom for coord in inst]
                
                # Draw rectangle with yellow highlight (semi-transparent)
                draw.rectangle(
                    [(rect[0], rect[1]), (rect[2], rect[3])],
                    fill=(255, 255, 0, 80),  # Yellow with alpha
                    outline=(255, 165, 0),   # Orange outline
                    width=2
                )
    
        # If subheading instances found, highlight them differently
        if subheading_instances:
            # Draw light blue semi-transparent highlight around each subheading instance
            # for inst in subheading_instances:
            # Scale the coordinates according to zoom factor
            rect = [coord * zoom for coord in subheading_instances[0]]
            
            # Draw rectangle with blue highlight (semi-transparent)
            draw.rectangle(
                [(rect[0], rect[1]), (rect[2], rect[3])],
                fill=(135, 206, 250, 80),  # Light blue with alpha
                outline=(0, 0, 255),       # Blue outline
                width=2
            )
    
        # Combine the overlay with the original image
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        
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