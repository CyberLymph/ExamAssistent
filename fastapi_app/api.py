from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from deepseek import DeepSeekWrapper

wrapper = DeepSeekWrapper()

# Create FastAPI app
app = FastAPI(title="My API Base", version="1.0.0")

# Example request body
class Item(BaseModel):
    name: str
    description: str
    price: float
    tax: float

class OpenApiMessage(BaseModel):
    content: str

class Attachement(BaseModel):
    file_name: str
    content_base64: str
    file_type: str = "pdf"

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to my FastAPI base project!"}

@app.get("/home")
def read_root():
    return {"message": "Welcome to the homepage!"}

# Example GET
@app.get("/ping")
def ping():
    return {"ping": "pong"}

@app.post("/sendApiMessage")
def sendApiMessage(message: OpenApiMessage):
    #Note: If input is file: 

    response = wrapper.send_request(message=message.content)
    print(response)

@app.post("/send-attachement")
def sendAttachementToOpenAi(attachement: Attachement):
    if attachement.file_type != "pdf":
        raise HTTPException(
            status_code=400,
            detail="Filetype can only be pdf."
        )
    else:
        pass



# Example POST
@app.post("/items/")
def create_item(item: Item):
    total_price = item.price + (item.tax if item.tax else 0)
    return {"name": item.name, "total_price": total_price}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
