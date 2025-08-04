from flask import Flask, request, send_file, jsonify
import requests
from pdfrw import PdfReader, PdfWriter, PdfDict, PdfObject
from datetime import datetime
import io

app = Flask(__name__)

# === Zoho OAuth Credentials ===
CLIENT_ID = "1000.LIG2AUIR72E8FNXRWEYM5U8WB3HU8R"
CLIENT_SECRET = "40869abcac5eb307332c289079ac43aa3585a8bd65"
REFRESH_TOKEN = "1000.079533a7c5c51308e9fc96dc685b0a10.a364615854910f4cf94f6fc0d7fe00da"

# === Field Mapping ===
FIELD_MAP = {
    "Text1": "SSN",
    "Text2": "Date_of_Birth",
    "Text3": "Full_Name",
    "Text4": "Home_Address",
    "Text5": "Home_City",
    "Text6": "Mail_State",
    "Text7": "Home_Zip",
    "Text8": "Phone",
    "Text9": "Mobile",
    "Text10": "Email",
    "Text11": "Full_Name",
    "Text12": "SSN",
    "Text17": "Full_Name",
    "Text18": "SSN"
}

def refresh_access_token():
    print("🔄 Refreshing Zoho access token...")
    url = "https://accounts.zoho.com/oauth/v2/token"
    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, params=params)
    data = response.json()
    if "access_token" in data:
        return data["access_token"]
    raise Exception(f"❌ Failed to refresh access token: {data}")

def fetch_contact_by_id(access_token, contact_id):
    url = f"https://www.zohoapis.com/crm/v2/Contacts/{contact_id}"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["data"][0]

def format_phone(number):
    digits = ''.join(filter(str.isdigit, str(number)))
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return number

def format_dob(dob_raw):
    try:
        return datetime.strptime(dob_raw, "%Y-%m-%d").strftime("%m/%d/%Y")
    except:
        return dob_raw

def fill_pdf(data):
    pdf = PdfReader("form.pdf")
    if pdf.Root.AcroForm:
        pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfObject("true")))

    for page in pdf.pages:
        annotations = page.Annots
        if annotations:
            for annotation in annotations:
                if annotation.Subtype == "/Widget" and annotation.T:
                    key = annotation.T[1:-1]
                    if key in FIELD_MAP:
                        field = FIELD_MAP[key]
                        value = data.get(field, "")
                        if field in ["Phone", "Mobile"]:
                            value = format_phone(value)
                        elif field == "Date_of_Birth":
                            value = format_dob(value)
                        annotation.update(PdfDict(V=PdfObject(f"({value})"), Ff=1, AP=None))
    
    buffer = io.BytesIO()
    PdfWriter().write(buffer, pdf)
    buffer.seek(0)
    return buffer

@app.route("/zoho-generate-pdf", methods=["GET"])
def generate_pdf():
    contact_id = request.args.get("contact_id")
    if not contact_id:
        return jsonify({"error": "Missing contact_id"}), 400
    try:
        token = refresh_access_token()
        contact = fetch_contact_by_id(token, contact_id)
        pdf_file = fill_pdf(contact)
        filename = f"{contact.get('First_Name', 'client')}_{contact.get('Last_Name', 'name')}_filled_form.pdf"
        return send_file(pdf_file, download_name=filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

