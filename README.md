### Borderless.so parser

This is a collection of functions related to parsing and processing stories from Borderless.so -- a website that tells stories of international students abroad.

Originally, I wanted to make a Telegram bot out of it, but as it stands, the dataset generated from the Borderless stories is too small to do any meaningful analysis. But hey, maybe someone will find its use!

## Installation

Prerequisite: Python 3.11.0 +

```bash
pip install -r requirements.txt
```

## Usage

```bash
python parser.py
```

## Misc folder

You can find some additional files in the `misc` folder that I used for testing and some rudimentary data analysis using OpenAI LLM. These are not necessary for the parser to work.
