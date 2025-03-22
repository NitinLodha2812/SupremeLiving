from flask import Flask, request, render_template, redirect, url_for, send_file, jsonify, redirect
from werkzeug.utils import secure_filename
import os
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Gmail configuration instead of Mailgun
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") # Use App Password, not regular password

def read_excel(file_path):
    df = pd.read_excel(file_path)
    return df.to_dict(orient = 'records')

products = read_excel('products.xlsx')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_message(name):
    return f'Hello {name}, \nWelcome to our store! Please find our product catalog attached.'

def generate_message_quotation(name):
    return f'Hello {name}, \nHere is your quotation.'

def send_email(email, message, subject, media_url = None):
    try:
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = subject
        
        # Attach the message text
        msg.attach(MIMEText(message))
        
        # Attach file if provided
        if media_url is not None:
            with open(media_url, 'rb') as file:
                attachment = MIMEApplication(file.read(), _subtype="pdf")
                attachment.add_header('Content-Disposition', 
                                     'attachment', 
                                     filename=os.path.basename(media_url))
                msg.attach(attachment)
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', files = files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('index'))
    return 'Invalid file type'

@app.route('/send', methods=['POST'])
def send_message():
    name = request.form['name']
    email = request.form['email']
    catalogs = request.form.getlist('catalogs[]')
    
    if not catalogs:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        return render_template('index.html', error_message="Please select at least one catalog", files=files)
    
    message = generate_message(name)
    subject = "SupremeLiving Product Catalog"
    
    # Create a single email with multiple attachments
    try:
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = subject
        
        # Attach the message text
        msg.attach(MIMEText(message))
        
        # Attach all selected files
        for catalog in catalogs:
            pdf_url = os.path.join(app.config['UPLOAD_FOLDER'], catalog)
            with open(pdf_url, 'rb') as file:
                attachment = MIMEApplication(file.read(), _subtype="pdf")
                attachment.add_header('Content-Disposition', 
                                     'attachment', 
                                     filename=os.path.basename(pdf_url))
                msg.attach(attachment)
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        success_message = "Message sent with all selected catalogs!"
    except Exception as e:
        print(f"Error sending email: {e}")
        success_message = f"Error sending email: {str(e)}"
    
    return render_template('index.html', success_message=success_message, files=os.listdir('uploads'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/quotation')
def quotation():
    return render_template('quotation.html', products = products)

def generate_pdf(data, items):
    today = datetime.today().strftime('%d-%m-%Y')
    pdf = FPDF()
    
    # Set UTF-8 encoding for the PDF
    pdf.add_page()
    
    # Header section
    pdf.set_font("Helvetica", "B", size=14)
    pdf.cell(190, 10, txt="Quotation", ln=True, border=True, align="C")
    pdf.set_font("Helvetica", "B", size=10)
    pdf.cell(95, 8, txt=f"No. {data['number']}", ln=0, align="L", border=True)
    pdf.cell(95, 8, txt=f"Date: {today}", ln=True, align="R", border=True)
    pdf.set_font("Helvetica", "B", size=9)
    pdf.cell(190, 15, txt="To", ln=True)
    pdf.cell(190, -5, txt=f"{data['name']}", ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(190, 8, txt="", ln=True)
    pdf.cell(190, 7, txt="Dear Sir/Madam,", ln=True)
    pdf.cell(190, 1, txt="", ln=True)
    pdf.cell(190, 10, txt="We thank you for your enquiry of Bosch Products.", ln=True)
    pdf.cell(190, 1, txt="In continuation to our discussion please find below our special offer for the same.", ln=True)
    pdf.line(10, 68, 200, 68)
    pdf.cell(190, 5, txt="", ln=True)
    
    # Define column widths
    col_width_product = 45
    col_width_price = 30
    col_width_desc = 75
    col_width_special = 40
    
    # Set table headers
    pdf.set_font("Helvetica", "B", size=9)
    pdf.cell(col_width_product, 10, "Product", 1, 0, "L")
    pdf.cell(col_width_price, 10, "Price", 1, 0, "R")
    pdf.cell(col_width_desc, 10, "Description", 1, 0, "L")
    pdf.cell(col_width_special, 10, "Special Price", 1, 1, "R")
    
    # Calculate total of special prices
    total_special_price = 0
    for price in items['special_prices']:
        # Strip any currency symbols and commas, then convert to float
        try:
            # Handle price format like "₹1,234" or "1,234.56"
            # Replace Rupee symbol with "Rs." to avoid encoding issues
            clean_price = price.replace('₹', '').replace(',', '')
            total_special_price += float(clean_price)
        except ValueError:
            # If conversion fails, just skip this item
            continue
    
    # Set table data
    pdf.set_font("Helvetica", size=8)
    
    for i in range(len(items['products'])):
        # Create a fixed height row
        row_height = 10  # Fixed height - adjust if needed
        
        # Product
        current_x = pdf.get_x()
        current_y = pdf.get_y()
        pdf.multi_cell(col_width_product, row_height, items['products'][i], 1, 'L')
        pdf.set_xy(current_x + col_width_product, current_y)
        
        # Price (right-aligned) - Replace Rupee symbol if present
        price_text = items['prices'][i].replace('₹', 'Rs.')
        pdf.cell(col_width_price, row_height, price_text, 1, 0, 'R')
        
        # Description  
        current_x = pdf.get_x()
        current_y = pdf.get_y()
        pdf.multi_cell(col_width_desc, row_height, items['descriptions'][i], 1, 'L')
        pdf.set_xy(current_x + col_width_desc, current_y)
        
        # Special Price (right-aligned) - Replace Rupee symbol if present
        special_price_text = items['special_prices'][i].replace('₹', 'Rs.')
        pdf.cell(col_width_special, row_height, special_price_text, 1, 1, 'R')
    
    # Add Total row at the bottom of the table
    pdf.set_font("Helvetica", "B", size=9)
    pdf.cell(col_width_product + col_width_price + col_width_desc, 10, "Total", 1, 0, "R")
    pdf.cell(col_width_special, 10, f"Rs.{total_special_price:,.2f}", 1, 1, "R")
    
    # Footer content
    pdf.cell(190, 5, txt="", ln=True)
    pdf.set_font("Helvetica", "U", size=9)
    pdf.cell(190, 5, txt="Note", ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(190, 5, txt="Price              : The Above Prices are all inclusive of GST", ln=True)
    pdf.set_font("Helvetica", "B", size=9)
    pdf.cell(190, 5, txt="Payment       : 100% Advance in favour of Shiron Atelier Pvt. Ltd", ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(190, 5, txt="Bank Details  : ICICI Bank A/c No.000905034876, IFSC : ICIC0000009, Nungambakkam Branch", ln=True)
    pdf.cell(190, 5, txt="Delivery         : Subject to availability of Stock", ln=True)
    pdf.set_text_color(255, 0, 0)
    pdf.cell(190, 5, txt="Quotation      : Valid for 2 days from the date of quote.", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", size=9)
    pdf.cell(190, 5, txt="GSTIN No.    : 33ABJCS4952Q1ZM", ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(190, 5, txt="", ln=True)
    pdf.cell(190, 5, txt="Please Call the Undersigned person for any clarification.", ln=True)
    pdf.cell(190, 5, txt="", ln=True)
    pdf.cell(190, 5, txt="Regards,", ln=True)
    pdf.set_font("Helvetica", "B", size=9)
    pdf.cell(190, 5, txt="For Shiron Atelier Pvt. Ltd.,", ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(190, 8, txt="", ln=True)
    pdf.cell(190, 5, txt="Authorized Signatory", ln=True)
    pdf.cell(190, 5, txt="Manager", ln=True)
    
    return pdf

@app.route('/generate_quotation', methods=['POST'])
def generate_quotation():
    name = request.form['name']
    email = request.form['email']
    message = generate_message_quotation(name)
    subject = "SupremeLiving Quotation"
    data = request.form.to_dict()
    items = {
        'products': request.form.getlist('products[]'),
        'prices': request.form.getlist('prices[]'),
        'descriptions': request.form.getlist('descriptions[]'),
        'special_prices': request.form.getlist('special_prices[]')
    }
    
    pdf = generate_pdf(data, items)
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quotation.pdf')
    pdf.output(pdf_path)
    
    if 'send_email' in request.form:
        send_email(email, message, subject, pdf_path)
        success_message = "Quotation sent!"
        return render_template('quotation.html', success_message=success_message, products=products)
    
    if 'download_pdf' in request.form:
        return redirect(url_for('download_quotation'))

@app.route('/download-quotation')
def download_quotation():
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quotation.pdf')
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True)
    else:
        return "File not found", 404
    
@app.route('/follow')
def customer_database():
    return render_template('follow.html')

@app.route('/submit-customer', methods=['POST'])
def submit_customer():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    subject = request.form.get('subject', "Reg: Follow Up from SupremeLiving")
    
    # Replace any remaining placeholder if exists
    message = message.replace('[Customer Name]', name)
    
    # Send the email
    if send_email(email, message, subject):
        success_message = "Follow-Up email has been sent successfully!"
    else:
        success_message = "There was an error sending the email. Please try again."
    
    return render_template('follow.html', success_message=success_message)

@app.route('/review')
def review_link():
    return render_template('review.html', products = products)

@app.route('/submit-review', methods=['POST'])
def submit_review():
    name = request.form['name']
    dob = request.form['dob']
    anniversary = request.form['anniversary']
    review = request.form['review']
    new_review = {'Name': name, 'DOB': dob, 'Anniversary Date': anniversary, 'Review': review}

    csv_file_path = 'reviews.csv'
    if os.path.exists(csv_file_path):
        df = pd.read_csv(csv_file_path)
        df.loc[len(df), df.columns] = new_review
    else:
        df = pd.DataFrame([new_review], columns=['Name', 'DOB', 'Anniversary Date', 'Review'])

    df.to_csv(csv_file_path, index=False)
    return jsonify({"status": "success"})

@app.route('/get-reviews', methods=['GET'])
def get_reviews():
    reviews = []
    if os.path.exists('reviews.csv'):
        with open('reviews.csv', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                reviews.append({'name': row['Name'], 'dob': row['DOB'],
                    'anniversary': row['Anniversary Date'],'review': row['Review']})
    return jsonify(reviews)

if __name__ == '__main__':
    app.run(debug = True)