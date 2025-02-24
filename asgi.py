from main import app
from mangum import Mangum

# Convert FastAPI app for Vercel's serverless environment
handler = Mangum(app, lifespan="auto")
