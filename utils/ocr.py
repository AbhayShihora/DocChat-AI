import pytesseract
from pdf2image import convert_from_path

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Users\Abhay\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
)

# Poppler path
POPPLER_PATH = r"D:\SOFTWARE\poppler-26.02.0\Library\bin"


def extract_text_from_scanned_pdf(pdf_path):
    """
    Extract text from a scanned PDF using OCR.
    """

    images = convert_from_path(
        pdf_path,
        poppler_path=POPPLER_PATH
    )

    extracted_text = ""

    for page_number, image in enumerate(images, start=1):

        print(f"Reading Page {page_number}...")

        page_text = pytesseract.image_to_string(image)

        extracted_text += f"\n\n----- Page {page_number} -----\n"
        extracted_text += page_text

    return extracted_text