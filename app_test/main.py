import uvicorn
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict
import pandas as pd


app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

locations_data: List[Dict[str, float]] = []

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request":request})


@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    try:
        df = pd.read_csv(file.file)
        global locations_data
        locations_data = df.to_dict(orient='records')
        print(locations_data)

        """ return templates.TemplateResponse("index.html", {"request": request}) """
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return {"error": str(e)}

@app.get("/locations", response_model=List[Dict[str, float]])
async def get_locations():
    return locations_data


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)