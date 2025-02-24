from main import app
from mangum import Mangum

handler = Mangum(app)  # Required for Vercel
