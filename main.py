from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from PIL import Image
import numpy as np 
from numpy import ndarray
import uvicorn
from camopy import camo_request
import io
import zipfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your specific frontend URL if known
    allow_credentials=True,
    allow_methods=["*"],  # Or list specific methods like ["GET", "POST"]
    allow_headers=["*"],  # Or list specific headers
)

def create_zip(sat_buff, graph_buff):
    zip_buff = io.BytesIO()
    with zipfile.ZipFile(zip_buff, mode="x") as zf:
        zf.writestr("satellite_image.png", sat_buff.getvalue())
        zf.writestr("graph_image.png", graph_buff.getvalue())
    zip_buff.seek(0)
    return zip_buff

def xarray_to_PIL(tif):
    data = tif.values #has shape of (3, y, x)    
    combined = np.stack(data, axis=-1) #shape (x, y, 3)
    combined = combined.astype(np.uint8)
    image = Image.fromarray(combined, mode="RGB")
    return image

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/image/{latitude}_{longitude}_{box_size}_{month}")
def serve_images(latitude: float, longitude: float, box_size: float, month: int):
    try:
        # Request satellite image from camo_request
        sat_data, graph_data = camo_request(latitude, longitude, box_size, month)
        
        # Check if sat_data is a PI L Image or needs conversion
        if isinstance(sat_data, Image.Image):
            sat_image = sat_data
        else:
            sat_image = xarray_to_PIL(sat_data)

        if isinstance(graph_data, Image.Image):
            graph_image = graph_data
        else:
            graph_image = Image.new("RGB", (200, 200), color=(255, 0, 0))


        sat_buffer = io.BytesIO()
        sat_image.save(sat_buffer, format="PNG")
        sat_buffer.seek(0)

        graph_buffer = io.BytesIO()
        graph_image.save(graph_buffer, format="PNG")
        graph_buffer.seek(0)

        zip_buff = create_zip(sat_buffer,  graph_buffer) #returns another buffer containing a zip     file
    
        # Return the image as a response
        return Response(content=zip_buff.getvalue(), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=images.zip"})
    
    except Exception as e:
        print(f"Exception raised: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

#Url_Test : http://127.0.0.1:8000/image/32.715736_-117.161087_5000_5