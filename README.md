# Cruise Employee English Assessment Platform

## Quick Start

1. **Read CLAUDE.md first** - Contains essential rules for Claude Code
2. Follow the pre-task compliance checklist before starting any work
3. Use proper module structure under `src/main/python/`
4. Commit after every completed task

## Project Overview

A comprehensive web-based English assessment platform designed specifically for cruise ship employees. The platform features division-based testing across three operational areas:

- **Hotel Operations** (8 departments)
- **Marine Operations** (3 departments)
- **Casino Operations** (3 departments)

## Features

- **6 Assessment Modules**: Listening, Time & Numbers, Grammar, Vocabulary, Reading, Speaking
- **AI-Powered**: AI-generated audio, automated scoring, intelligent feedback
- **Division-Specific Content**: Tailored questions for each operational area
- **Comprehensive Analytics**: Performance tracking and trend analysis
- **Anti-Cheating Measures**: IP restrictions, time limits, randomized questions

## AI/ML Project Structure

**Data Management:**
- `data/raw/` - Original question banks and audio files
- `data/processed/` - Cleaned and structured assessment data
- `notebooks/` - Analysis and model development

**ML Components:**
- `models/` - AI models for speech analysis and scoring
- `experiments/` - ML experiment tracking and results
- `src/main/python/inference/` - Real-time assessment scoring

## Development Guidelines

- **Always search first** before creating new files
- **Extend existing** functionality rather than duplicating
- **Use Task agents** for operations >30 seconds
- **Single source of truth** for all functionality
- **Language-agnostic structure** - works with Python, JS, Java, etc.
- **Scalable** - start simple, grow as needed
- **AI/ML Ready** - includes MLOps-focused directories for datasets, experiments, and models

## Technology Stack

- **Backend**: Python (Flask/FastAPI)
- **AI/ML**: OpenAI API/Claude API for speech analysis
- **Database**: MySQL/PostgreSQL
- **Frontend**: Web-based responsive design
- **Audio**: MP3/WAV support with AI voice generation