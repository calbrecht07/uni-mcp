from dotenv import load_dotenv
import os
load_dotenv(override=True)
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.orchestrator import router
from providers.slack import slack_oauth
from providers.jira import jira_oauth

# Initialize FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)
app.include_router(slack_oauth.router)
app.include_router(jira_oauth.router)

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)

