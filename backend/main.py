from fastapi import FastAPI

app = FastAPI(title="ListPilot")


@app.get("/health")
def health():
    return {"status": "ok"}
