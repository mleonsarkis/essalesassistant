# ES Sales Support Bot

The Sales Support Bot is a smart, multi-channel assistant designed to automate and streamline sales agents’ daily tasks. It integrates with Microsoft Teams and Telegram to help prepare materials for potential projects, collect vital information, submit opportunities to a CRM via API, and even draft project proposals by generating PowerPoint presentations—all using GenAI models.

## Overview

Sales agents face a variety of repetitive tasks when preparing proposals and managing client data. This bot addresses those challenges by:
- *Automating Information Collection:* Gathers details about potential projects from user inputs.
- *CRM Integration:* Submits opportunities directly into your CRM system through its API.
- *Proposal Generation:* Uses natural language processing to draft proposals and outline presentations.
- *PowerPoint Creation:* Automatically generates PowerPoint files based on the proposal outline.

The bot is built for scalability, so additional use cases can be added as needed.

## Features

- *Multi-Channel Deployment:*  
  Works on Microsoft Teams and Telegram, letting agents use their preferred communication platform.

- *Automated Proposal Preparation:*  
  - Collects user input to draft a proposal outline.
  - Generates a professional PowerPoint presentation from the outline.

- *CRM Opportunity Submission:*  
  Integrates with your CRM’s API to submit new sales opportunities.

- *Scalability:*  
  Modular design to support future enhancements and additional use cases.

## Technical Stack

- *Programming Language:* Python 3.9
- *Frameworks & Libraries:*
  - *FastAPI:* For building the RESTful API.
  - *Microsoft Bot Builder:* To manage bot interactions.
  - *Langchain & OpenAI:* For leveraging GPT-4 to generate proposals and presentation outlines.
- *Infrastructure:*
  - *Azure Services:*
    - *Azure Bot Service:* Hosts and manages the bot.
    - *Azure Web App:* Runs the FastAPI application.
  - *Data Storage:*  
    - *Redis:* Stores chat history and session data (using free tier limits).

## Architecture

The bot follows a modular architecture:
- *Bot Framework Adapter:*  
  Integrates with Teams and Telegram, routing incoming messages to the bot logic.
- *FastAPI Service:*  
  Acts as the central API endpoint for all interactions.
- *LLM Integration:*  
  Uses Langchain and OpenAI to process user inputs and generate proposal content.
- *CRM Connector:*  
  Interfaces with the CRM API to submit sales opportunities.
- *Redis Storage:*  
  Caches chat history and session data to ensure efficient processing and state management.