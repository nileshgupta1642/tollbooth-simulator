from fastapi import FastAPI

app = FastAPI()


@app.post("/toll-passages")
async def receive_toll_passage(event: dict):
    print("Received toll passage:", event)
    return {"status": "ok"}