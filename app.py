
from flask import Flask, render_template, request
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def form():
    return render_template('form.html')

@app.route('/generate', methods=['POST'])
def generate():
    full_name = request.form['fullName']
    job_title = request.form['jobTitle']
    experience = request.form['experience']
    skills = request.form['skills']
    job_description = request.form['jobDescription']

    prompt = f"""
    Generate a professional CV and cover letter based on the following details:

    Full Name: {full_name}
    Job Title: {job_title}
    Experience Summary: {experience}
    Key Skills: {skills}
    Job Description: {job_description}
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a CV and cover letter writing assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    content = response['choices'][0]['message']['content']
    return render_template('result.html', output=content)

if __name__ == '__main__':
    app.run(debug=True)
