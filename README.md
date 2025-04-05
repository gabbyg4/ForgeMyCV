
# ForgeMyCV

**ForgeMyCV** is a simple Flask-based web app that uses OpenAI to generate professional resumes and cover letters based on user input.

## Features

- HTML form to collect job details
- GPT-3.5-turbo generates CV and cover letter
- Display result on screen

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ForgeMyCV.git
cd ForgeMyCV
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up environment variables

Create a `.env` file and add your OpenAI API key:

```bash
OPENAI_API_KEY=your-api-key-here
```

### 4. Run the app

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

---

## License

MIT License
