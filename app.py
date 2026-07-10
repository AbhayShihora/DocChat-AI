from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
import os
import PyPDF2
import google.generativeai as genai
from dotenv import load_dotenv  
from flask import session
from flask import session, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
from utils.ocr import extract_text_from_scanned_pdf

md="gemini-3.1-flash-lite"
pdf_content = ""
chat_history = []

app = Flask(__name__)

app.secret_key = "AI_PDF_Summarizer_By_Abhay_2026"

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

#Uploaded pdf
@app.route('/upload', methods=['POST'])
def upload_pdf():
    pdf_file = request.files['pdf_file']
    summary_length = request.form["summary_length"]

    if not pdf_file.filename.endswith('.pdf'):
        return """<h3 style='color:red'>  Please upload a PDF file only. </h3>   """
    
    if pdf_file:
        filename = secure_filename(pdf_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        pdf_file.save(file_path)

        extracted_text = extract_text_from_pdf(file_path)
        global pdf_content
        global chat_history

        pdf_content = extracted_text
        chat_history = []
        #print("Text Length:", len(extracted_text))

        summary = summarize_text(extracted_text, summary_length)
        session["summary"] = summary

        return render_template("result.html",summary=summary)

    return "No file selected"

#Ask a Question
@app.route('/ask', methods=['POST'])
def ask():

    global pdf_content
    global chat_history

    question = request.form['question']

    answer = ask_pdf_question(
        pdf_content,
        question
    )

    chat_history.append({
        "question": question,
        "answer": answer
    })

    return render_template(
        "chat.html",
        chat_history=chat_history
    )

#Clear Chat
@app.route('/clear-chat')
def clear_chat():

    global chat_history

    chat_history = []

    return render_template(
        "chat.html",
        chat_history=chat_history
    )

#Read texts from pdf
def extract_text_from_pdf(pdf_path):
    text = ""

    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    # If PyPDF2 couldn't extract any text, use OCR
    if not text.strip():

        #print("No text found. Switching to OCR...")

        text = extract_text_from_scanned_pdf(pdf_path)

    return text
#Summarizer function
def summarize_text(text, length):

    model = genai.GenerativeModel(md)

    prompt = f"""
    Create a {length} summary of the PDF.

    Return professional HTML.
    Do NOT use markdown.
    Do NOT include ```html or ``` tags.
    """

    try:
        response = model.generate_content(prompt + text[:15000] )

        summary = response.text
        summary = summary.replace( "```html", "")
        summary = summary.replace("```","" )

        return summary

    except Exception as e:

        print("Gemini Error:", str(e))

        return f"""
        <div class="alert alert-danger">
            <h4>⚠️ AI Service Unavailable</h4>
            <p>{str(e)}</p>
        </div>
        """


#Download summary
@app.route('/download-summary')
def download_summary():

    summary = session.get("summary", "No summary available")

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer)
    styles = getSampleStyleSheet()

    content = [
    Paragraph("<b>AI PDF Summary</b>", styles['Title']),
    Paragraph("<br/>", styles['BodyText']),
    Paragraph(summary, styles['BodyText'])]

    doc.build(content)
    pdf_buffer.seek(0)

    return send_file(pdf_buffer,as_attachment=True,download_name="summary.pdf",mimetype="application/pdf")

#Ask Question function
def ask_pdf_question(pdf_text, question):

    model = genai.GenerativeModel(md)

    prompt = f"""
        You are an AI PDF Assistant.
        Use ONLY the information from the PDF content below.
        Instructions:
        - Do not use markdown.
        - Do not use ** symbols.
        - Use clean plain text.
        - Use bullet points where needed.
        - Give a direct answer.
        - Keep the answer clear and professional.
        - If the answer is not found in the PDF, say:
        "This information is not available in the uploaded PDF."
        PDF Content:{pdf_text[:15000]}
        Question: {question}
        """

    if not pdf_text.strip():
        return """
        No PDF content found.
        Please upload a PDF first.
        """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception:

        return """
        ⚠️ Unable to process your question right now.
        Possible reasons:
        • No internet connection
        • Gemini API unavailable
        • API quota exceeded
        Please try again later.
        """
if __name__ == '__main__':
    app.run(debug=False)