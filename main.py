import google.generativeai as genai
import PIL.Image
import json
from io import BytesIO
import fitz  # PyMuPDF for PDF processing
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

# Configure the API key
GOOGLE_API_KEY = "AIzaSyBkMFn58k0KdGPZGSOqP4UXtYu2qYMLKmk"  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize FastAPI app
app = FastAPI()

def validate_pdf(filename: str, content: bytes) -> bool:
    """Validate if the file is a PDF"""
    if not filename.lower().endswith(".pdf"):
        return False
    try:
        fitz.open(stream=content, filetype="pdf").close()
        return True
    except:
        return False

def convert_pdf_to_image(pdf_bytes: bytes) -> BytesIO:
    """Convert first page of PDF to image in memory"""
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = pdf_document.load_page(0)  # Load first page
        pix = page.get_pixmap()
        img_data = BytesIO(pix.tobytes("png"))
        pdf_document.close()
        return img_data
    except Exception as e:
        print(f"Error converting PDF to image: {str(e)}")
        return None

def extract_aadhaar_data(image_source: BytesIO) -> dict:
    """Extract Aadhaar data using Google's Generative AI"""
    model = genai.GenerativeModel("gemini-1.5-flash")

    try:
        img = PIL.Image.open(image_source)

        # Define AI prompt
        prompt = """
        Analyze this Aadhaar card image and extract the following details:
        - Full name
        - Date of birth
        - Gender
        - Aadhaar number
        - Address
        - S/O, D/O (Parent Name)
        
        Return the information in this JSON format:
        {
            "name": "",
            "date_of_birth": "",
            "date_of_birth_year": "",
            "gender": "",
            "aadhaar_number": "",
            "address": "",
            "parent": "",
            "confidence": 0-100
        }

        Guidelines:
        - Extract data exactly as printed on the card
        - Ensure Aadhaar number is 12 digits without spaces
        - Date of birth should be null if day/month/year is missing
        - Address should include all components (house, street, city, state, PIN)
        - Set confidence based on image clarity

        Return only the JSON object, no extra text.
        """

        response = model.generate_content([prompt, img])
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
    
    except Exception as e:
        print(f"Error extracting Aadhaar data: {str(e)}")
        return None

@app.post("/extract-aadhaar-data/")
async def extract_aadhaar(aadhaar: UploadFile = File(...)):
    """Extract Aadhaar data and return JSON response"""
    try:
        # Read Aadhaar PDF content
        aadhaar_content = await aadhaar.read()

        # Validate PDF
        if not validate_pdf(aadhaar.filename, aadhaar_content):
            raise HTTPException(status_code=400, detail="Invalid PDF file")

        # Convert PDF to image
        img_data = convert_pdf_to_image(aadhaar_content)
        if not img_data:
            raise HTTPException(status_code=400, detail="Failed to process Aadhaar PDF")

        # Extract Aadhaar data
        aadhaar_data = extract_aadhaar_data(img_data)
        if not aadhaar_data:
            raise HTTPException(status_code=400, detail="Failed to extract Aadhaar data")

        return JSONResponse(status_code=200, content=aadhaar_data)
    
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"error": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/")
async def home():
    """Root endpoint"""
    return {"message": "Aadhaar Extraction API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
